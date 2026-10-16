def assign_number(instance, prefix: str, width: int = 5) -> None:
    """Присваивает документу номер вида «ПР-00012» по первичному ключу (вызывать после сохранения)."""
    if instance.number:
        return
    instance.number = f"{prefix}-{instance.pk:0{width}d}"
    type(instance).objects.filter(pk=instance.pk).update(number=instance.number)
