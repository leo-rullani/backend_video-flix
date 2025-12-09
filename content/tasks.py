import subprocess
from pathlib import Path


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
        # For now just print; later you could log this properly
        print("[FFMPEG ERROR]", completed.stderr)
        raise RuntimeError(f"FFmpeg failed with code {completed.returncode}")
    else:
        print("[FFMPEG OK]", completed.stdout[:200])  # truncate output


def convert_480p(source: str) -> str:
    """
    Convert the given video to 480p inside the same directory.
    Returns the absolute path of the new file.
    """
    target = _build_target_path(source, "_480p")
    cmd = 'ffmpeg -i "{}" -s hd480 -c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'.format(
        source, target
    )
    _run_ffmpeg(cmd)
    return target


def convert_720p(source: str) -> str:
    """
    Convert the given video to 720p inside the same directory.
    """
    target = _build_target_path(source, "_720p")
    cmd = 'ffmpeg -i "{}" -s hd720 -c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'.format(
        source, target
    )
    _run_ffmpeg(cmd)
    return target


def convert_1080p(source: str) -> str:
    """
    Convert the given video to 1080p inside the same directory.
    """
    target = _build_target_path(source, "_1080p")
    cmd = 'ffmpeg -i "{}" -s hd1080 -c:v libx264 -crf 23 -c:a aac -strict -2 "{}"'.format(
        source, target
    )
    _run_ffmpeg(cmd)
    return target