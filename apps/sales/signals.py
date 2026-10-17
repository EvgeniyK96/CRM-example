from django.dispatch import Signal

# shipment — отгрузка создана, продукция списана (shipment.items)
shipment_created = Signal()
