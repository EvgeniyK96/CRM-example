from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.permissions import ReadAnyWriteRoles

from . import services
from .models import Recipe
from .serializers import CalculateSerializer, RecipeSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    """Рецептуры. Создание и изменение — технолог; черновик → активна → в архиве."""

    queryset = Recipe.objects.select_related("product__unit", "product__department", "created_by").prefetch_related(
        "lines__ingredient__unit"
    )
    serializer_class = RecipeSerializer
    permission_classes = [ReadAnyWriteRoles("technologist")]
    filterset_fields = ["product", "status", "product__department"]
    search_fields = ["product__name", "product__code"]
    ordering_fields = ["version", "created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        if not instance.is_editable:
            raise ValidationError("Удалить можно только черновик.")
        instance.delete()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        try:
            recipe = services.activate(self.get_object())
        except services.RecipeError as e:
            raise ValidationError(str(e))
        return Response(self.get_serializer(recipe).data)

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        recipe = services.copy_as_draft(self.get_object(), request.user)
        return Response(self.get_serializer(recipe).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], serializer_class=CalculateSerializer)
    def calculate(self, request, pk=None):
        params = CalculateSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        qty = params.validated_data["qty"]
        return Response({"qty": qty, "lines": services.calculate(self.get_object(), qty)})
