from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ReadAnyWriteRoles, RoleAccess, has_role
from core.views import CreatedByMixin

from . import services, worktime
from .models import Absence, Department, Employee, Holiday, HROrder, Position, WorkDay
from .serializers import (
    AbsenceSerializer,
    DepartmentSerializer,
    EmployeeSerializer,
    HolidaySerializer,
    HROrderSerializer,
    PositionSerializer,
)

HrWrite = ReadAnyWriteRoles("hr")
# Кадровые документы видят отдел кадров и бухгалтерия (зарплата), начальники цехов — табель
HrDocs = RoleAccess(read=("accountant", "shop_head"), write=("hr",))


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [HrWrite]
    filterset_fields = ["is_production", "is_active"]
    search_fields = ["name"]


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [HrWrite]
    search_fields = ["name"]


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("department", "position", "user")
    serializer_class = EmployeeSerializer
    permission_classes = [HrWrite]
    filterset_fields = ["department", "position", "status"]
    search_fields = ["last_name", "first_name", "middle_name", "tax_id", "phone"]
    ordering_fields = ["last_name", "hire_date"]


class HROrderViewSet(CreatedByMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Кадровые приказы неизменяемы: ошибку исправляют новым приказом."""

    queryset = HROrder.objects.select_related(
        "employee", "from_department", "to_department", "from_position", "to_position", "created_by"
    )
    serializer_class = HROrderSerializer
    permission_classes = [HrDocs]
    filterset_fields = ["employee", "kind"]
    search_fields = ["number", "employee__last_name", "reason"]


class AbsenceViewSet(CreatedByMixin, viewsets.ModelViewSet):
    queryset = Absence.objects.select_related("employee__department")
    serializer_class = AbsenceSerializer
    permission_classes = [HrDocs]
    filterset_fields = {"employee": ["exact"], "kind": ["exact"], "employee__department": ["exact"],
                        "date_from": ["lte"], "date_to": ["gte"]}
    search_fields = ["employee__last_name", "comment"]


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [HrWrite]
    filterset_fields = {"date": ["year"]}


class MonthSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    department = serializers.IntegerField(required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        attrs.setdefault("year", today.year)
        attrs.setdefault("month", today.month)
        return attrs


class TimesheetView(APIView):
    """Табель за месяц: ?year=&month=&department=."""

    permission_classes = [HrDocs]

    def get(self, request):
        params = MonthSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        p = params.validated_data
        return Response(services.timesheet(p["year"], p["month"], p.get("department")))


class WorkDayViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Учёт рабочего дня.

    - `GET current/` — мой сегодняшний день; `POST start/`, `pause/`, `finish/ {report}` — кнопки в шапке;
    - `GET` — отчёт по дням: отдел кадров, бухгалтерия и администратор видят всех, остальные — только себя.
      Фильтры: `date_from`, `date_to`, `user`, `department`.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WorkDay.objects.select_related("user__employee__department").prefetch_related("intervals")
        if not has_role(self.request.user, "hr", "accountant"):
            qs = qs.filter(user=self.request.user)
        p = self.request.query_params
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])
        if p.get("user"):
            qs = qs.filter(user_id=p["user"])
        if p.get("department"):
            qs = qs.filter(user__employee__department_id=p["department"])
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        now = timezone.now()
        return self.get_paginated_response([self._row(day, now) for day in page])

    def retrieve(self, request, *args, **kwargs):
        return Response(self._row(self.get_object(), timezone.now()))

    @staticmethod
    def _row(day, now):
        employee = getattr(day.user, "employee", None)
        return {
            **worktime.summary(day, now),
            "user": day.user_id,
            "user_name": day.user.get_full_name() or day.user.username,
            "department_name": employee.department.name if employee else None,
        }

    def _current(self, request):
        return Response(worktime.summary(worktime.today(request.user)))

    @action(detail=False)
    def current(self, request):
        return self._current(request)

    @action(detail=False, methods=["post"])
    def start(self, request):
        worktime.start(request.user)
        return self._current(request)

    @action(detail=False, methods=["post"])
    def pause(self, request):
        worktime.pause(request.user)
        return self._current(request)

    @action(detail=False, methods=["post"])
    def finish(self, request):
        worktime.finish(request.user, str(request.data.get("report", ""))[:4000])
        return self._current(request)
