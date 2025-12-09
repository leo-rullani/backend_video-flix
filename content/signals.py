import os
from typing import Any

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Video
from content.tasks import convert_480p, convert_720p, convert_1080p


@receiver(post_save, sender=Video)
def video_post_save(sender: type[Video], instance: Video, created: bool, **kwargs: Any) -> None:
    """
    Signal that runs whenever a Video instance is saved.

    - If `created` is True, a new Video was created.
    - If `created` is False, an existing Video was updated.
    """
    if created:
        print(
            f"[SIGNAL] New video created (id={instance.pk}, "
            f"title={getattr(instance, 'title', 'N/A')})"
        )
        source_path = instance.video_file.path

        # For now: synchronous conversions.
        # Later we will move this into a background job (django-rq).
        convert_480p(source_path)
        convert_720p(source_path)
        convert_1080p(source_path)
    else:
        print(
            f"[SIGNAL] Video updated (id={instance.pk}, "
            f"title={getattr(instance, 'title', 'N/A')})"
        )


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(
    sender: type[Video], instance: Video, **kwargs: Any
) -> None:
    """
    Deletes the video file from the filesystem
    when the corresponding Video object is deleted.
    """
    if instance.video_file:
        file_path = instance.video_file.path
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"[SIGNAL] Video file deleted from filesystem: {file_path}")