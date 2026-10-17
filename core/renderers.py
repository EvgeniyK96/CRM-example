from decimal import Decimal

from rest_framework.renderers import JSONRenderer as BaseJSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class DecimalAsStringEncoder(JSONEncoder):
    """Decimal → строка, как у DecimalField сериализаторов: без потери точности и единообразно во всём API."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return format(obj, "f")
        return super().default(obj)


class JSONRenderer(BaseJSONRenderer):
    encoder_class = DecimalAsStringEncoder
