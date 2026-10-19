from rest_framework import serializers

from .models import Activity
from .registry import describe, key_of


def display_name(user) -> str:
    return user.get_full_name() or user.username


class ActivitySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = (
            "id", "kind", "kind_display", "text", "author", "author_name", "author_role", "old_status", "new_status",
            "created_at", "target", "can_delete",
        )
        read_only_fields = fields

    def get_author_name(self, a):
        return display_name(a.author) if a.author else None

    def get_author_role(self, a):
        return a.author.get_role_display() if a.author else None

    def get_target(self, a):
        """{type, id, title, path}; документ удалён — title «удалён», path нет."""
        if not a.content_type_id:
            return None
        info = {"type": key_of(a.content_type), "id": a.object_id}
        if a.target is None:
            return {**info, "title": f"{a.content_type.name} (удалён)", "path": None}
        return {**info, **describe(a.target)}

    def get_can_delete(self, a):
        user = self.context["request"].user
        return a.kind in (Activity.Kind.COMMENT, Activity.Kind.POST) and (a.author_id == user.pk or user.role == "admin")


class ActivityCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)
    target = serializers.CharField(required=False, allow_blank=True, help_text="Тип документа: sales.salesorder")
    target_id = serializers.IntegerField(required=False, min_value=1)
