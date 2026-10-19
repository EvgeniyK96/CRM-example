from django.contrib import admin

from .models import Activity, Notification


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "content_type", "object_id", "author", "text")
    list_filter = ("kind", "content_type")
    search_fields = ("text",)
    raw_id_fields = ("author",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "reason", "text", "is_read")
    list_filter = ("reason", "is_read")
    raw_id_fields = ("recipient", "activity")
