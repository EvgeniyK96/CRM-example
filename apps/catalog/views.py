from rest_framework import viewsets

from apps.accounts.permissions import ReadAnyWriteRoles

from .models import Category, Item, Supplier, Unit
from .serializers import CategorySerializer, ItemSerializer, SupplierSerializer, UnitSerializer

TechnologistWrite = ReadAnyWriteRoles("technologist")


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [TechnologistWrite]
    search_fields = ["code", "name"]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [TechnologistWrite]
    filterset_fields = ["kind"]
    search_fields = ["name"]


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related("unit", "category", "department")
    serializer_class = ItemSerializer
    permission_classes = [TechnologistWrite]
    filterset_fields = ["kind", "category", "department", "is_active"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "shelf_life_days"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [ReadAnyWriteRoles("storekeeper", "accountant")]
    filterset_fields = ["is_active"]
    search_fields = ["name", "tax_id", "contact_person", "phone"]
