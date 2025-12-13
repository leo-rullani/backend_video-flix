# content/management/commands/generate_hls.py

"""Management command to generate HLS video streams for Videoflix."""

from __future__ import annotations

from pathlib import Path
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.models import Video

FFMPEG_BASE = ("ffmpeg", "-y")
VIDEO_ARGS = ("-c:v", "libx264", "-preset", "veryfast", "-crf", "23")
AUDIO_ARGS = ("-c:a", "aac", "-ac", "2")
HLS_ARGS = (
    "-f",
    "hls",
    "-hls_time",
    "10",
    "-hls_playlist_type",
    "vod",
    "-hls_flags",
    "independent_segments",
)


class Command(BaseCommand):
    """Generate HLS renditions (480p, 720p, 1080p) for all or selected videos."""

    help = "Generate HLS streams (480p, 720p, 1080p) for all videos."

    RESOLUTIONS = [("480p", 480), ("720p", 720), ("1080p", 1080)]

    def add_arguments(self, parser) -> None:
        """Add CLI arguments for filtering and overwriting output."""
        parser.add_argument("--video-id", type=int, help="Only generate HLS for this video id.")
        parser.add_argument("--overwrite", action="store_true", help="Overwrite existing HLS files.")

    def handle(self, *args, **options) -> None:
        """Generate HLS renditions for one or all videos."""
        hls_root = self._ensure_hls_root()
        videos = self._get_videos(options.get("video_id"))
        overwrite = bool(options.get("overwrite", False))
        for video in videos:
            self._process_video(video, hls_root, overwrite)
        self.stdout.write(self.style.SUCCESS("All done."))

    def _ensure_hls_root(self) -> Path:
        """Create and return the HLS root directory."""
        media_root = Path(settings.MEDIA_ROOT)
        hls_root = Path(getattr(settings, "HLS_ROOT", media_root / "hls"))
        hls_root.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.NOTICE(f"HLS root: {hls_root}"))
        return hls_root

    def _get_videos(self, video_id: int | None):
        """Return a queryset of videos filtered by an optional id."""
        qs = Video.objects.all().order_by("id")
        qs = qs.filter(pk=video_id) if video_id is not None else qs
        if not qs.exists():
            raise CommandError("No videos found for the given filters.")
        return qs

    def _process_video(self, video: Video, hls_root: Path, overwrite: bool) -> None:
        """Validate the source file and generate all renditions for one video."""
        input_path = self._get_input_path(video)
        if not input_path:
            return
        msg = f"Processing video {video.id} ({video.title}) from {input_path}"
        self.stdout.write(self.style.NOTICE(msg))
        for label, height in self.RESOLUTIONS:
            self._generate_rendition(video, input_path, hls_root, label, height, overwrite)

    def _get_input_path(self, video: Video) -> Path | None:
        """Return the source file path or None if the file is missing."""
        if not video.video_file:
            msg = f"Video {video.id} ({video.title}) has no video_file – skipping."
            self.stdout.write(self.style.WARNING(msg))
            return None
        input_path = Path(video.video_file.path)
        if not input_path.is_file():
            msg = f"Input file not found for video {video.id}: {input_path}"
            self.stdout.write(self.style.WARNING(msg))
            return None
        return input_path

    def _generate_rendition(
        self,
        video: Video,
        input_path: Path,
        hls_root: Path,
        label: str,
        height: int,
        overwrite: bool,
    ) -> None:
        """Generate a single HLS rendition for a video."""
        out_dir = hls_root / str(video.id) / label
        playlist_path = out_dir / "index.m3u8"
        out_dir.mkdir(parents=True, exist_ok=True)
        if not self._prepare_output_dir(out_dir, playlist_path, label, overwrite):
            return
        segment_pattern = out_dir / "%03d.ts"
        cmd = self._build_ffmpeg_command(input_path, height, segment_pattern, playlist_path)
        self._run_ffmpeg(video, label, cmd, playlist_path)

    def _prepare_output_dir(
        self, out_dir: Path, playlist_path: Path, label: str, overwrite: bool
    ) -> bool:
        """Prepare destination directory; return False if work is skipped."""
        if playlist_path.exists() and not overwrite:
            msg = f"  [{label}] {playlist_path} exists – skipping (use --overwrite)."
            self.stdout.write(self.style.WARNING(msg))
            return False
        if playlist_path.exists() and overwrite:
            self._clean_output_dir(out_dir)
        return True

    def _clean_output_dir(self, out_dir: Path) -> None:
        """Remove all files from a HLS output directory."""
        for path in out_dir.glob("*"):
            try:
                path.unlink()
            except Exception:  # noqa: BLE001
                continue

    def _build_ffmpeg_command(
        self, input_path: Path, height: int, segment_pattern: Path, playlist_path: Path
    ) -> list[str]:
        """Build the ffmpeg CLI args for one HLS rendition."""
        src = ("-i", str(input_path), "-vf", f"scale=-2:{height}")
        out = ("-hls_segment_filename", str(segment_pattern), str(playlist_path))
        return [*FFMPEG_BASE, *src, *VIDEO_ARGS, *AUDIO_ARGS, *HLS_ARGS, *out]

    def _run_ffmpeg(self, video: Video, label: str, cmd: list[str], playlist_path: Path) -> None:
        """Run ffmpeg and report progress for a single rendition."""
        self.stdout.write(self.style.NOTICE(f"  [{label}] Generating HLS → {playlist_path}"))
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"ffmpeg failed for video {video.id} ({label}): {exc}")
        msg = f"  [{label}] HLS generation finished for video {video.id}"
        self.stdout.write(self.style.SUCCESS(msg))