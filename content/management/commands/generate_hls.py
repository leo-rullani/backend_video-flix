# content/management/commands/generate_hls.py

"""Management command to generate HLS video streams for Videoflix."""

from pathlib import Path
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.models import Video


class Command(BaseCommand):
    """Generate HLS renditions (480p, 720p, 1080p) for all or selected videos."""

    help = "Generate HLS streams (480p, 720p, 1080p) for all videos."

    RESOLUTIONS = [("480p", 480), ("720p", 720), ("1080p", 1080)]

    def add_arguments(self, parser):
        """Add CLI arguments for filtering and overwriting HLS output."""
        parser.add_argument(
            "--video-id",
            type=int,
            help="Only generate HLS files for this video id.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing HLS files if they already exist.",
        )

    def handle(self, *args, **options):
        """Entry point for HLS generation command."""
        video_id = options.get("video_id")
        overwrite = options.get("overwrite", False)
        media_root = Path(settings.MEDIA_ROOT)
        hls_root = Path(getattr(settings, "HLS_ROOT", media_root / "hls"))
        videos = self._get_videos(video_id)
        self.stdout.write(self.style.NOTICE(f"HLS root: {hls_root}"))
        hls_root.mkdir(parents=True, exist_ok=True)
        for video in videos:
            self._process_video(video, hls_root, overwrite)
        self.stdout.write(self.style.SUCCESS("All done."))

    def _get_videos(self, video_id):
        """Return queryset of videos filtered by optional id."""
        qs = Video.objects.all().order_by("id")
        if video_id is not None:
            qs = qs.filter(pk=video_id)
        if not qs.exists():
            raise CommandError("No videos found for the given filters.")
        return qs

    def _process_video(self, video, hls_root: Path, overwrite: bool):
        """Validate video file and generate HLS renditions."""
        input_path = self._get_input_path(video)
        if input_path is None:
            return
        self.stdout.write(
            self.style.NOTICE(
                f"Processing video {video.id} ({video.title}) from {input_path}"
            )
        )
        for label, height in self.RESOLUTIONS:
            self._generate_rendition(
                video, input_path, hls_root, label, height, overwrite
            )

    def _get_input_path(self, video):
        """Return Path to source file or None if missing."""
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

    def _generate_rendition(self, video, input_path, hls_root, label, height, overwrite):
        """Generate a single HLS rendition for a video."""
        out_dir = hls_root / str(video.id) / label
        playlist_path = out_dir / "index.m3u8"
        out_dir.mkdir(parents=True, exist_ok=True)
        if not self._prepare_output_dir(out_dir, playlist_path, label, overwrite):
            return
        segment_pattern = out_dir / "%03d.ts"
        cmd = self._build_ffmpeg_command(
            input_path, height, segment_pattern, playlist_path
        )
        self._run_ffmpeg(video, label, cmd, playlist_path)

    def _prepare_output_dir(self, out_dir, playlist_path, label, overwrite):
        """Prepare destination directory; return False if work is skipped."""
        if playlist_path.exists() and not overwrite:
            msg = f"  [{label}] {playlist_path} exists – skipping (use --overwrite)."
            self.stdout.write(self.style.WARNING(msg))
            return False
        if playlist_path.exists() and overwrite:
            self._clean_output_dir(out_dir)
        return True

    def _clean_output_dir(self, out_dir):
        """Remove all files from a HLS output directory."""
        for path in out_dir.glob("*"):
            try:
                path.unlink()
            except Exception:  # noqa: BLE001
                continue

    def _build_ffmpeg_command(self, input_path, height, segment_pattern, playlist_path):
        """Return ffmpeg CLI arguments for one HLS rendition."""
        return [
            "ffmpeg", "-y", "-i", str(input_path), "-vf", f"scale=-2:{height}",
            "-c:v", "libx264", "-c:a", "aac", "-ac", "2", "-preset", "veryfast",
            "-crf", "23", "-f", "hls", "-hls_time", "10",
            "-hls_playlist_type", "vod", "-hls_segment_filename",
            str(segment_pattern), str(playlist_path),
        ]

    def _run_ffmpeg(self, video, label, cmd, playlist_path):
        """Run ffmpeg and report progress for a single rendition."""
        msg = f"  [{label}] Generating HLS → {playlist_path}"
        self.stdout.write(self.style.NOTICE(msg))
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise CommandError(
                f"ffmpeg failed for video {video.id} ({label}): {exc}"
            )
        success = f"  [{label}] HLS generation finished for video {video.id}"
        self.stdout.write(self.style.SUCCESS(success))