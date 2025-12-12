from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Video


class VideoResource(resources.ModelResource):
    class Meta:
        model = Video


@admin.register(Video)
class VideoAdmin(ImportExportModelAdmin):
    resource_class = VideoResource
    list_display = ("id", "title", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description")