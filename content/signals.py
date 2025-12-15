from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import django_rq
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import generate_hls_for_video


def _hls_dir_for_video(video_id: int) -> Path:
    """
    Returns the filesystem path where HLS files for a video should live:
    <MEDIA_ROOT>/hls/<video_id>/
    """
    media_root = Path(settings.MEDIA_ROOT)
    hls_root = Path(getattr(settings, "HLS_ROOT", media_root / "hls"))
    return hls_root / str(video_id)


def _enqueue_or_run(func, *args: Any, **kwargs: Any) -> None:
    """
    Enqueue via django-rq, fallback to direct execution (so it still works
    even if Redis/RQ is not available for some reason).
    """
    try:
        queue = django_rq.get_queue("default", autocommit=True)
        queue.enqueue(func, *args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[SIGNAL] Could not enqueue job ({exc}). Running directly...")
        func(*args, **kwargs)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created: bool, raw: bool = False, **kwargs) -> None:
    """
    Runs whenever a Video is saved.

    IMPORTANT:
    - If created=True and a video_file exists -> generate HLS in background.
    - raw=True happens during fixture loading -> skip heavy processing.
    """
    if raw:
        # Prevent heavy ffmpeg jobs while Django loads fixtures
        return

    if not created:
        print(f"[SIGNAL] Video updated (id={instance.pk}, title={getattr(instance, 'title', 'N/A')})")
        return

    print(f"[SIGNAL] New video created (id={instance.pk}, title={getattr(instance, 'title', 'N/A')})")

    if not instance.video_file:
        print(f"[SIGNAL] Video created (id={instance.pk}) but no video_file attached. Skipping HLS.")
        return

    # Enqueue HLS generation for this video id
    _enqueue_or_run(generate_hls_for_video, instance.pk, False)

    print(f"[SIGNAL] Enqueued HLS generation job for video_id={instance.pk}")


@receiver(post_delete, sender=Video)
def auto_delete_files_on_delete(sender, instance: Video, **kwargs) -> None:
    """
    Deletes:
    - original video file
    - legacy MP4 variants (if they exist)
    - generated HLS folder: <MEDIA_ROOT>/hls/<video_id>/
    """
    video_id = instance.pk

    # 1) delete original + legacy variants
    if instance.video_file:
        original_path = instance.video_file.path
        src = Path(original_path)

        variant_paths = [
            original_path,
            str(src.with_name(f"{src.stem}_480p{src.suffix}")),
            str(src.with_name(f"{src.stem}_720p{src.suffix}")),
            str(src.with_name(f"{src.stem}_1080p{src.suffix}")),
        ]

        for path in variant_paths:
            if os.path.isfile(path):
                os.remove(path)
                print(f"[SIGNAL] Deleted file: {path}")
            else:
                print(f"[SIGNAL] File not found (ok): {path}")
    else:
        print(f"[SIGNAL] Video deleted (id={video_id}) but no video_file attached.")

    # 2) delete HLS directory
    hls_dir = _hls_dir_for_video(video_id)
    if hls_dir.exists() and hls_dir.is_dir():
        shutil.rmtree(hls_dir, ignore_errors=True)
        print(f"[SIGNAL] Deleted HLS folder: {hls_dir}")
    else:
        print(f"[SIGNAL] No HLS folder found (ok): {hls_dir}")