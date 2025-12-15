from django import forms
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Video


class VideoResource(resources.ModelResource):
    class Meta:
        model = Video


class VideoAdminForm(forms.ModelForm):
    """
    Enforces required fields ONLY in Django Admin UI:
    - thumbnail must be provided
    - category must be provided (not empty / not whitespace)
    """

    class Meta:
        model = Video
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make both fields required in the admin form (even if model has blank=True)
        self.fields["thumbnail"].required = True
        self.fields["category"].required = True

        # Ensure whitespace-only input is treated as empty
        self.fields["category"].strip = True

    def clean_category(self):
        value = (self.cleaned_data.get("category") or "").strip()
        if not value:
            raise forms.ValidationError("Category is required.")
        return value

    def clean_thumbnail(self):
        thumb = self.cleaned_data.get("thumbnail")
        if not thumb:
            raise forms.ValidationError("Thumbnail is required.")
        return thumb


@admin.register(Video)
class VideoAdmin(ImportExportModelAdmin):
    resource_class = VideoResource
    form = VideoAdminForm

    list_display = ("id", "title", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description")