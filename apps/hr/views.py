from rest_framework import viewsets

from apps.accounts.permissions import ReadAnyWriteRoles

from .models import Department, Employee, Position
from .serializers import DepartmentSerializer, EmployeeSerializer, PositionSerializer

HrWrite = ReadAnyWriteRoles("hr")


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
    queryset = Employee.objects.select_related("department", "position")
    serializer_class = EmployeeSerializer
    permission_classes = [HrWrite]
    filterset_fields = ["department", "position", "status"]
    search_fields = ["last_name", "first_name", "middle_name", "tax_id", "phone"]
    ordering_fields = ["last_name", "hire_date"]
