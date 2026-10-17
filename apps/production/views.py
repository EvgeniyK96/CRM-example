from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, ReadAnyWriteRoles
from apps.purchasing.serializers import PurchaseOrderSerializer
from apps.warehouse.models import Lot
from core.views import CreatedByMixin

from . import services
from .filters import ProductionTaskFilter
from .models import ProductionTask
from .permissions import check_department, own_department_id
from .serializers import FinishSerializer, ProductionTaskSerializer, TaskConsumptionSerializer


class ProductionTaskViewSet(CreatedByMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Производственные задания: запланировано → в работе → выполнено (или отменено).
    Удаления нет — задание отменяют, чтобы не потерять связь с заказами.
    """

    queryset = ProductionTask.objects.select_related(
        "department", "product__unit", "recipe", "output_lot", "created_by", "started_by", "finished_by"
    ).prefetch_related("allocations__order_line__order__client")
    serializer_class = ProductionTaskSerializer
    permission_classes = [ReadAnyWriteRoles("shop_head")]
    filterset_class = ProductionTaskFilter
    search_fields = ["number", "product__name", "comment"]
    ordering_fields = ["planned_date", "created_at", "number"]

    def perform_create(self, serializer):
        check_department(self.request.user, serializer.validated_data["product"].department_id)
        super().perform_create(serializer)

    def get_task(self) -> ProductionTask:
        task = self.get_object()
        if self.request.method not in ("GET", "HEAD", "OPTIONS"):
            check_department(self.request.user, task.department_id)
        return task

    def perform_update(self, serializer):
        self.get_task()
        serializer.save()

    def _respond(self, task):
        return Response(self.get_serializer(self.get_queryset().get(pk=task.pk)).data)

    @action(detail=True, methods=["get"])
    def requirements(self, request, pk=None):
        return Response(services.requirements(self.get_object()))

    @action(detail=True, methods=["get"])
    def consumptions(self, request, pk=None):
        items = self.get_object().consumptions.select_related("move__lot__item__unit", "move__lot__supplier")
        return Response(TaskConsumptionSerializer(items, many=True).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._respond(services.start(self.get_task(), request.user))

    @action(detail=True, methods=["post"], serializer_class=FinishSerializer)
    def finish(self, request, pk=None):
        params = FinishSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        task = services.finish(self.get_task(), user=request.user, **params.validated_data)
        return Response(ProductionTaskSerializer(self.get_queryset().get(pk=task.pk)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._respond(services.cancel(self.get_task()))

    @action(detail=True, methods=["post"])
    def request_purchase(self, request, pk=None):
        """Черновики заявок поставщикам на недостающее сырьё."""
        orders, skipped = services.request_purchase(self.get_task(), request.user)
        return Response(
            {"orders": PurchaseOrderSerializer(orders, many=True).data, "skipped": skipped},
            status=status.HTTP_201_CREATED,
        )


class DemandView(APIView):
    """GET — непокрытая потребность из заказов; POST — сформировать по ней задания."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasRole("shop_head")()]
        return super().get_permissions()

    def get(self, request):
        return Response(services.demand(own_department_id(request.user)))

    def post(self, request):
        tasks = services.plan_from_demand(user=request.user, department_id=own_department_id(request.user))
        return Response(ProductionTaskSerializer(tasks, many=True).data, status=status.HTTP_201_CREATED)


class TraceView(APIView):
    """Прослеживаемость партии: сырьё → продукция."""

    def get(self, request, lot_id):
        return Response(services.trace(get_object_or_404(Lot.objects.select_related("item__unit", "supplier"), pk=lot_id)))
