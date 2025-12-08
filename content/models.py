from django.db import models


class Video(models.Model):
    title = models.CharField("Titel", max_length=255)
    description = models.TextField("Beschreibung", blank=True)
    video_file = models.FileField("Videodatei", upload_to="videos/")
    thumbnail = models.ImageField(
        "Thumbnail", upload_to="thumbnails/", blank=True, null=True
    )
    category = models.CharField("Kategorie", max_length=100, blank=True)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Video"
        verbose_name_plural = "Videos"

    def __str__(self) -> str:
        return self.title

    @property
    def thumbnail_url(self) -> str:
        """
        Passt zu deiner API-Doku:
        {
          "id": 1,
          "created_at": "...",
          "title": "...",
          "description": "...",
          "thumbnail_url": "...",
          "category": "..."
        }
        """
        if self.thumbnail and hasattr(self.thumbnail, "url"):
            return self.thumbnail.url
        return ""
