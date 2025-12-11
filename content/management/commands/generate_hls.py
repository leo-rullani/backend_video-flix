# content/management/commands/generate_hls.py

from pathlib import Path
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.models import Video


class Command(BaseCommand):
    help = "Generate HLS streams (480p, 720p, 1080p) for all videos."

    # Optional: einzelne Video-ID wählen, ansonsten alle
    def add_arguments(self, parser):
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
        video_id = options.get("video_id")
        overwrite = options.get("overwrite", False)

        # HLS-Root wie in content.api.views._hls_root
        media_root = Path(settings.MEDIA_ROOT)
        hls_root = Path(getattr(settings, "HLS_ROOT", media_root / "hls"))

        # Welche Auflösungen wollen wir erzeugen?
        # label -> Zielhöhe
        resolutions = [
            ("480p", 480),
            ("720p", 720),
            ("1080p", 1080),
        ]

        qs = Video.objects.all().order_by("id")
        if video_id is not None:
            qs = qs.filter(pk=video_id)

        if not qs.exists():
            raise CommandError("No videos found for the given filters.")

        self.stdout.write(self.style.NOTICE(f"HLS root: {hls_root}"))
        hls_root.mkdir(parents=True, exist_ok=True)

        for video in qs:
            if not video.video_file:
                self.stdout.write(
                    self.style.WARNING(
                        f"Video {video.id} ({video.title}) has no video_file – skipping."
                    )
                )
                continue

            input_path = Path(video.video_file.path)
            if not input_path.is_file():
                self.stdout.write(
                    self.style.WARNING(
                        f"Input file not found for video {video.id}: {input_path}"
                    )
                )
                continue

            self.stdout.write(
                self.style.NOTICE(
                    f"Processing video {video.id} ({video.title}) from {input_path}"
                )
            )

            for label, height in resolutions:
                out_dir = hls_root / str(video.id) / label
                out_dir.mkdir(parents=True, exist_ok=True)
                playlist_path = out_dir / "index.m3u8"

                # Existing files?
                if playlist_path.exists() and not overwrite:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [{label}] {playlist_path} exists – skipping "
                            "(use --overwrite to regenerate)."
                        )
                    )
                    continue

                # Wenn overwrite: alte Dateien weg
                if playlist_path.exists() and overwrite:
                    for p in out_dir.glob("*"):
                        try:
                            p.unlink()
                        except Exception:
                            pass

                segment_pattern = out_dir / "%03d.ts"

                cmd = [
                    "ffmpeg",
                    "-y",  # overwrite without asking
                    "-i",
                    str(input_path),
                    "-vf",
                    f"scale=-2:{height}",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-ac",
                    "2",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-f",
                    "hls",
                    "-hls_time",
                    "10",
                    "-hls_playlist_type",
                    "vod",
                    "-hls_segment_filename",
                    str(segment_pattern),
                    str(playlist_path),
                ]

                self.stdout.write(
                    self.style.NOTICE(
                        f"  [{label}] Generating HLS → {playlist_path}"
                    )
                )

                try:
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as exc:
                    raise CommandError(
                        f"ffmpeg failed for video {video.id} ({label}): {exc}"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{label}] HLS generation finished for video {video.id}"
                    )
                )

        self.stdout.write(self.style.SUCCESS("All done."))
