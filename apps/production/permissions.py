from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role
from apps.hr.models import Employee


def own_department_id(user) -> int | None:
    """Цех начальника цеха (через карточку сотрудника). None — ограничений нет (начальник производства, админ)."""
    if user.role != Role.SHOP_HEAD:
        return None
    return (
        Employee.objects.filter(user=user, department__is_production=True)
        .values_list("department_id", flat=True).first()
    )


def check_department(user, department_id: int) -> None:
    own = own_department_id(user)
    if own is not None and own != department_id:
        raise PermissionDenied("Это задание другого цеха.")
