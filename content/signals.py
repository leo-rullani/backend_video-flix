import os

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created: bool, **kwargs) -> None:
    """
    Signal that runs whenever a Video instance is saved.

    - If `created` is True, a new Video was created.
    - If `created` is False, an existing Video was updated.
    """
    if created:
        print(
            f"[SIGNAL] New video created (id={instance.pk}, title={getattr(instance, 'title', 'N/A')})"
        )
        # TODO: Trigger background job for HLS/FFMPEG conversion here
        # e.g. convert_video.delay(instance.id)
    else:
        print(
            f"[SIGNAL] Video updated (id={instance.pk}, title={getattr(instance, 'title', 'N/A')})"
        )


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance: Video, **kwargs) -> None:
    """
    Deletes the video file from the filesystem
    when the corresponding Video object is deleted.
    """
    if instance.video_file:
        file_path = instance.video_file.path
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"[SIGNAL] Video file deleted from filesystem: {file_path}")