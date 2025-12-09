# content/signals.py

import os
from pathlib import Path

import django_rq
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Video
from .tasks import convert_videos


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created: bool, **kwargs) -> None:
    """
    Signal that runs whenever a Video instance is saved.

    - If `created` is True, a new Video was created:
      -> enqueue background job to convert the video in different resolutions.
    - If `created` is False, an existing Video was updated:
      -> currently we just log the update; no conversions are triggered.
    """
    if created:
        print(
            f"[SIGNAL] New video created "
            f"(id={instance.pk}, title={getattr(instance, 'title', 'N/A')})"
        )

        if instance.video_file:
            source_path = instance.video_file.path
            queue = django_rq.get_queue("default", autocommit=True)

            # enqueue background job
            queue.enqueue(convert_videos, source_path)

            print(
                f"[SIGNAL] Enqueued background job for FFmpeg conversions: "
                f"{source_path}"
            )
        else:
            print(
                f"[SIGNAL] New video created (id={instance.pk}) "
                "but no video_file is attached. Skipping FFmpeg."
            )
    else:
        print(
            f"[SIGNAL] Video updated "
            f"(id={instance.pk}, title={getattr(instance, 'title', 'N/A')})"
        )


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance: Video, **kwargs) -> None:
    """
    Deletes the original video file and the generated variants
    (480p, 720p, 1080p) from the filesystem when the corresponding
    Video object is deleted.
    """
    if not instance.video_file:
        print(
            f"[SIGNAL] Video deleted (id={instance.pk}) "
            "but no video_file was attached."
        )
        return

    original_path = instance.video_file.path
    src = Path(original_path)

    # All possible variants we generate in tasks.py
    variant_paths = [
        original_path,
        str(src.with_name(f"{src.stem}_480p{src.suffix}")),
        str(src.with_name(f"{src.stem}_720p{src.suffix}")),
        str(src.with_name(f"{src.stem}_1080p{src.suffix}")),
    ]

    for path in variant_paths:
        if os.path.isfile(path):
            os.remove(path)
            print(f"[SIGNAL] Deleted video file from filesystem: {path}")
        else:
            # Not an error – maybe that variant was never created
            print(f"[SIGNAL] File not found (nothing to delete): {path}")