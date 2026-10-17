from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.serializers import PeriodSerializer
from apps.accounts.permissions import HasRole

from . import services


def _period(request):
    params = PeriodSerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    return params.validated_data["date_from"], params.validated_data["date_to"]


class DashboardView(APIView):
    """Сводка для главной: состав разделов зависит от роли. ?date_from=&date_to= (по умолчанию — текущий месяц)."""

    def get(self, request):
        return Response(services.dashboard(request.user, *_period(request)))


class SalesReportView(APIView):
    """Продажи за период по продуктам и клиентам: количество, выручка, себестоимость, маржа."""

    permission_classes = [HasRole("sales", "accountant")]

    def get(self, request):
        return Response(services.sales_summary(*_period(request)))


class ProductionReportView(APIView):
    """Загрузка цехов и выпуск с браком за период."""

    permission_classes = [HasRole("shop_head", "technologist", "accountant")]

    def get(self, request):
        return Response(services.production_summary(*_period(request)))


class StockReportView(APIView):
    """Оценка запасов по себестоимости партий, дефицит сырья, сроки годности."""

    permission_classes = [HasRole("storekeeper", "technologist", "shop_head", "accountant")]

    def get(self, request):
        return Response(services.stock_summary())
