from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasRole, RoleAccess
from core.views import CreatedByMixin

from . import services
from .models import PayrollPeriod, PayrollRate, Payslip
from .serializers import PayMethodSerializer, PayrollPeriodSerializer, PayrollRateSerializer, PayslipSerializer

AccountantOnly = HasRole("accountant")


class PayrollRateViewSet(viewsets.ModelViewSet):
    queryset = PayrollRate.objects.all()
    serializer_class = PayrollRateSerializer
    permission_classes = [RoleAccess(read=("hr",), write=("accountant",))]


class PayrollPeriodViewSet(CreatedByMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Ведомости: создать за месяц → рассчитать (можно многократно) → провести → выплатить."""

    queryset = PayrollPeriod.objects.prefetch_related("payslips")
    serializer_class = PayrollPeriodSerializer
    permission_classes = [AccountantOnly]

    def perform_create(self, serializer):
        period = serializer.save(created_by=self.request.user)
        services.calculate(period)

    def _respond(self, period):
        return Response(self.get_serializer(self.get_queryset().get(pk=period.pk)).data)

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        return self._respond(services.calculate(self.get_object()))

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        return self._respond(services.post(self.get_object(), request.user))

    @action(detail=True, methods=["post"])
    def unpost(self, request, pk=None):
        return self._respond(services.unpost(self.get_object()))

    @action(detail=True, methods=["post"], serializer_class=PayMethodSerializer)
    def pay(self, request, pk=None):
        params = PayMethodSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        period = services.pay(self.get_object(), user=request.user, **params.validated_data)
        return Response(PayrollPeriodSerializer(self.get_queryset().get(pk=period.pk)).data)


class PayslipViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Расчётные листки; изменить можно только премию, пока ведомость — черновик."""

    queryset = Payslip.objects.select_related("employee", "department", "position", "period").prefetch_related(
        "lines__rate"
    )
    serializer_class = PayslipSerializer
    permission_classes = [AccountantOnly]
    filterset_fields = ["period", "employee", "department"]
    search_fields = ["employee__last_name", "employee__first_name"]
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        services.set_bonus(serializer.instance, serializer.validated_data.get("bonus", serializer.instance.bonus))

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(self.get_serializer(self.get_queryset().get(pk=kwargs["pk"])).data)


class MyPayslipViewSet(viewsets.ReadOnlyModelViewSet):
    """Свои расчётные листки — любому сотруднику с учётной записью (только проведённые ведомости)."""

    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            Payslip.objects.filter(employee__user=self.request.user)
            .exclude(period__status=PayrollPeriod.Status.DRAFT)
            .select_related("employee", "department", "position", "period").prefetch_related("lines__rate")
            .order_by("-period__year", "-period__month")
        )


