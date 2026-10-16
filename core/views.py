from rest_framework.exceptions import ValidationError


class DraftOnlyDestroyMixin:
    """Удалять документ можно только пока он редактируемый (черновик)."""

    def perform_destroy(self, instance):
        if not instance.is_editable:
            raise ValidationError("Удалить можно только черновик.")
        instance.delete()


class CreatedByMixin:
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
