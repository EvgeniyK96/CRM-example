from django.contrib import admin

from .models import Recipe, RecipeLine


class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("product", "version", "status", "output_qty", "activated_at")
    list_filter = ("status", "product__department")
    search_fields = ("product__name",)
    inlines = [RecipeLineInline]
