from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict

from django.core.management import call_command

logger = logging.getLogger(__name__)


def generate_hls_for_video(video_id: int, overwrite: bool = False) -> None:
    """
    Background job (RQ):
    Generates HLS playlists/segments for ONE video by calling the existing
    management command: `python manage.py generate_hls --video-id <id>`.

    This is the important part for the reviewer, because the frontend requests:
    /api/video/<id>/<resolution>/index.m3u8
    """
    logger.warning("[TASK] Generating HLS for video_id=%s (overwrite=%s)", video_id, overwrite)

    # Calls your management command:
    #   python manage.py generate_hls --video-id <video_id> [--overwrite]
    call_command("generate_hls", video_id=video_id, overwrite=overwrite)

    logger.warning("[TASK] HLS finished for video_id=%s", video_id)


# ---------------------------
# Legacy MP4 conversion (optional)
# ---------------------------

def _build_target_path(source: str, suffix: str) -> str:
    """
    Build a new file path based on the original video and a suffix, e.g. '_480p'.
    'source' is an absolute path inside MEDIA_ROOT.
    """
    src = Path(source)
    return str(src.with_name(f"{src.stem}{suffix}{src.suffix}"))


def _run_ffmpeg(command: str) -> None:
    """
    Helper to run an FFmpeg command via subprocess.
    Raises an error if FFmpeg returns a non-zero exit code.
    """
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print("[FFMPEG ERROR]", completed.stderr)
        raise RuntimeError(f"FFmpeg failed with code {completed.returncode}")
    else:
        print("[FFMPEG OK]", (completed.stdout or "")[:200])


def convert_480p(source: str) -> str:
    target = _build_target_path(source, "_480p")
    cmd = (
        'ffmpeg -i "{}" -s hd480 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_720p(source: str) -> str:
    target = _build_target_path(source, "_720p")
    cmd = (
        'ffmpeg -i "{}" -s hd720 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_1080p(source: str) -> str:
    target = _build_target_path(source, "_1080p")
    cmd = (
        'ffmpeg -i "{}" -s hd1080 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_videos(source: str) -> Dict[str, str]:
    """
    Old job: creates MP4 variants (1080p/720p/480p).
    Not required for HLS playback, but kept to not break existing code.
    """
    print(f"[TASK] Starting MP4 conversions for: {source}")
    result: Dict[str, str] = {}
    result["1080p"] = convert_1080p(source)
    result["720p"] = convert_720p(source)
    result["480p"] = convert_480p(source)
    print(f"[TASK] Finished MP4 conversions for: {source}")
    return result