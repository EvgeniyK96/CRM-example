from django.db import transaction
from rest_framework import serializers


class LinesWriteMixin:
    """
    ModelSerializer документа со вложенными строками (поле ``lines``).
    При сохранении строки заменяются целиком; редактировать можно только документ с is_editable.
    """

    lines_parent_field: str  # имя FK строки на документ
    lines_unique_field: str | None = None  # поле, которое не должно повторяться в строках
    not_editable_message = "Документ нельзя изменить в текущем статусе."

    def validate_lines(self, lines):
        if self.lines_unique_field:
            keys = [line[self.lines_unique_field].pk for line in lines]
            if len(keys) != len(set(keys)):
                raise serializers.ValidationError("Позиции в строках не должны повторяться.")
        return lines

    def validate(self, attrs):
        if self.instance is not None and not self.instance.is_editable:
            raise serializers.ValidationError(self.not_editable_message)
        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        instance = super().create(validated_data)
        self._save_lines(instance, lines)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        instance = super().update(instance, validated_data)
        if lines is not None:
            instance.lines.all().delete()
            self._save_lines(instance, lines)
        return instance

    def _save_lines(self, instance, lines):
        model = self.fields["lines"].child.Meta.model
        model.objects.bulk_create(model(**{self.lines_parent_field: instance}, **line) for line in lines)


def positive(value, message="Значение должно быть больше нуля."):
    if value is not None and value <= 0:
        raise serializers.ValidationError(message)
    return value
