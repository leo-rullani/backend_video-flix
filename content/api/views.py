# content/api/views.py

"""API views for listing videos and serving HLS playlists/segments."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from content.models import Video

User = get_user_model()

ALLOWED_RENDITIONS: set[str] = {"480p", "720p", "1080p"}


def _hls_root() -> Path:
    """Return the base directory where HLS assets are stored."""
    root = getattr(settings, "HLS_ROOT", None)
    return Path(root) if root else Path(settings.MEDIA_ROOT) / "hls"


def _auth_error() -> Response:
    """Return a standard 401 response for missing/invalid authentication."""
    return Response(
        {"detail": "Authentication credentials were not provided or are invalid."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


def _to_iso_z(dt) -> str:
    """Return an ISO-8601 UTC string ending with 'Z'."""
    value = dt.isoformat()
    return value.replace("+00:00", "Z")


def _thumbnail_url(request, video: Video) -> str | None:
    """Return an absolute thumbnail URL or None."""
    thumb = getattr(video, "thumbnail", None)
    if not thumb:
        return None
    return request.build_absolute_uri(thumb.url)


def _serialize_video(video: Video, request) -> dict:
    """Serialize one Video instance for the list endpoint."""
    return {
        "id": video.id,
        "created_at": _to_iso_z(video.created_at),
        "title": video.title,
        "description": video.description,
        "thumbnail_url": _thumbnail_url(request, video),
        "category": video.category,
    }


def _serialize_videos(videos, request) -> list[dict]:
    """Serialize a queryset of videos for the list endpoint."""
    return [_serialize_video(v, request) for v in videos]


def _ensure_video_exists(movie_id: int) -> None:
    """Raise Http404 if the requested video does not exist."""
    if not Video.objects.filter(pk=movie_id).exists():
        raise Http404("Video not found.")


def _validate_resolution(resolution: str) -> None:
    """Raise Http404 if an unknown rendition is requested."""
    if resolution not in ALLOWED_RENDITIONS:
        raise Http404("Invalid resolution.")


def _validate_segment_name(segment: str) -> None:
    """Raise Http404 for unsafe segment names."""
    if "/" in segment or ".." in segment:
        raise Http404("Invalid segment name.")


def _file_or_404(path: Path, content_type: str) -> FileResponse:
    """Return a FileResponse for an existing file."""
    if not path.is_file():
        raise Http404("File not found.")
    return FileResponse(path.open("rb"), content_type=content_type)


class CookieJWTAuthMixin:
    """Mixin that authenticates via an access_token cookie."""

    def get_authenticated_user(self, request) -> User | None:
        """Return the authenticated user from the access_token cookie."""
        token_str = request.COOKIES.get("access_token")
        if not token_str:
            return None
        try:
            token = AccessToken(token_str)
        except TokenError:
            return None
        return User.objects.filter(pk=token.get("user_id"), is_active=True).first()


class VideoListView(CookieJWTAuthMixin, APIView):
    """Return a list of videos for authenticated users."""

    permission_classes = [AllowAny]

    def get(self, request) -> Response:
        """Return all videos ordered by newest first."""
        if not self.get_authenticated_user(request):
            return _auth_error()
        videos = Video.objects.all().order_by("-created_at")
        return Response(_serialize_videos(videos, request), status=status.HTTP_200_OK)


class VideoHLSManifestView(CookieJWTAuthMixin, APIView):
    """Serve the HLS playlist (index.m3u8) for a video rendition."""

    permission_classes = [AllowAny]

    def get(self, request, movie_id: int, resolution: str) -> FileResponse | Response:
        """Return the rendition playlist file response."""
        if not self.get_authenticated_user(request):
            return _auth_error()
        _ensure_video_exists(movie_id)
        _validate_resolution(resolution)
        path = _hls_root() / str(movie_id) / resolution / "index.m3u8"
        return _file_or_404(path, "application/vnd.apple.mpegurl")


class VideoHLSSegmentView(CookieJWTAuthMixin, APIView):
    """Serve a single HLS segment (.ts) for a video rendition."""

    permission_classes = [AllowAny]

    def get(self, request, movie_id: int, resolution: str, segment: str) -> FileResponse | Response:
        """Return the segment file response."""
        if not self.get_authenticated_user(request):
            return _auth_error()
        _ensure_video_exists(movie_id)
        _validate_resolution(resolution)
        _validate_segment_name(segment)
        path = _hls_root() / str(movie_id) / resolution / segment
        return _file_or_404(path, "video/MP2T")