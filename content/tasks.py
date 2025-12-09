# content/tasks.py

import subprocess
from pathlib import Path
from typing import Dict


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
    Raises an error if FFmpeg returns a non‑zero exit code.
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
        # Truncate output to avoid spamming logs
        print("[FFMPEG OK]", (completed.stdout or "")[:200])


def convert_480p(source: str) -> str:
    """
    Convert the given video to 480p inside the same directory.
    Returns the absolute path of the new file.
    """
    target = _build_target_path(source, "_480p")
    cmd = (
        'ffmpeg -i "{}" -s hd480 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_720p(source: str) -> str:
    """
    Convert the given video to 720p inside the same directory.
    Returns the absolute path of the new file.
    """
    target = _build_target_path(source, "_720p")
    cmd = (
        'ffmpeg -i "{}" -s hd720 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_1080p(source: str) -> str:
    """
    Convert the given video to 1080p inside the same directory.
    Returns the absolute path of the new file.
    """
    target = _build_target_path(source, "_1080p")
    cmd = (
        'ffmpeg -i "{}" -s hd1080 '
        '-c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'
    ).format(source, target)
    _run_ffmpeg(cmd)
    return target


def convert_videos(source: str) -> Dict[str, str]:
    """
    Main background task used by django-rq.

    Takes the absolute path of the original uploaded video and converts it to
    1080p, 720p and 480p (in that order, all in the same folder).

    Returns a mapping of resolution -> generated file path.
    """
    print(f"[TASK] Starting video conversions for: {source}")
    result: Dict[str, str] = {}
    result["1080p"] = convert_1080p(source)
    result["720p"] = convert_720p(source)
    result["480p"] = convert_480p(source)
    print(f"[TASK] Finished video conversions for: {source}")
    return result