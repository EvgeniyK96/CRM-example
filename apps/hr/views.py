from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ReadAnyWriteRoles, RoleAccess
from core.views import CreatedByMixin

from . import services
from .models import Absence, Department, Employee, Holiday, HROrder, Position
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
