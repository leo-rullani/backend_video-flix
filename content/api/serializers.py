# content/api/serializers.py

from typing import Any, Optional

from django.utils.functional import cached_property  # unused but harmless
from rest_framework import serializers

from content.models import Video


class VideoListSerializer(serializers.Serializer):
    """Serializer for public video list endpoint."""

    id = serializers.IntegerField(read_only=True)
    created_at = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    def get_created_at(self, obj: Video) -> Optional[Any]:
        """Return created timestamp under 'created_at' key."""
        created = getattr(obj, "created_at", None) or getattr(obj, "created", None)
        return created

    def get_thumbnail_url(self, obj: Video) -> Optional[str]:
        """Return absolute thumbnail URL if available."""
        request = self.context.get("request")
        thumbnail = getattr(obj, "thumbnail", None) or getattr(
            obj,
            "thumbnail_image",
            None,
        )
        if not thumbnail:
            return None
        try:
            url = thumbnail.url
        except Exception:
            return None
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_category(self, obj: Video) -> Optional[str]:
        """Return category name or string representation."""
        category = getattr(obj, "category", None)
        if category is None:
            return None
        name = getattr(category, "name", None)
        if name is not None:
            return name
        return str(category)
