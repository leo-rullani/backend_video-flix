# content/api/views.py

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
from .serializers import VideoListSerializer

User = get_user_model()


def _hls_root() -> Path:
    """Return base directory for HLS files."""
    root = getattr(settings, "HLS_ROOT", None)
    if root:
        return Path(root)
    return Path(settings.MEDIA_ROOT) / "hls"


def _auth_error() -> Response:
    """Standard 401 response for missing or invalid auth."""
    return Response(
        {"detail": "Authentication credentials were not provided or are invalid."},
        status=status.HTTP_401_UNAUTHORIZED,
    )


class CookieJWTAuthMixin:
    """Helper mixin to authenticate user via access_token cookie."""

    def get_authenticated_user(self, request):
        token_str = request.COOKIES.get("access_token")
        if not token_str:
            return None

        try:
            token = AccessToken(token_str)
        except TokenError:
            return None

        user_id = token.get("user_id")
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None


class VideoListView(APIView):
    """Return list of available videos for authenticated users."""

    # DRF soll hier NICHT IsAuthenticated erzwingen – wir prüfen Cookie selbst
    permission_classes = [AllowAny]

    def get(self, request):
        token_str = request.COOKIES.get("access_token")
        if not token_str:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            token = AccessToken(token_str)
        except TokenError:
            return Response(
                {"detail": "Invalid or expired access token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_id = token.get("user_id")
        if not user_id:
            return Response(
                {"detail": "Invalid token payload."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        videos = Video.objects.all().order_by("-created_at")

        data = [
            {
                "id": video.id,
                "created_at": video.created_at.isoformat().replace("+00:00", "Z"),
                "title": video.title,
                "description": video.description,
                "thumbnail_url": request.build_absolute_uri(video.thumbnail.url)
                if getattr(video, "thumbnail", None)
                else None,
                "category": video.category,
            }
            for video in videos
        ]

        return Response(data, status=status.HTTP_200_OK)


class VideoHLSManifestView(CookieJWTAuthMixin, APIView):
    """
    Return HLS master playlist (index.m3u8)
    for a given movie and resolution.
    """

    # Auch hier Cookie-Auth statt DRF-IsAuthenticated
    permission_classes = [AllowAny]

    def get(self, request, movie_id: int, resolution: str):
        user = self.get_authenticated_user(request)
        if not user:
            return _auth_error()

        if not Video.objects.filter(pk=movie_id).exists():
            raise Http404("Video not found.")

        base_dir = _hls_root() / str(movie_id) / resolution
        manifest_path = base_dir / "index.m3u8"
        if not manifest_path.is_file():
            raise Http404("Manifest not found.")

        return FileResponse(
            open(manifest_path, "rb"),
            content_type="application/vnd.apple.mpegurl",
        )


class VideoHLSSegmentView(CookieJWTAuthMixin, APIView):
    """
    Return a single HLS segment (.ts) for a given movie and resolution.
    """

    # WICHTIG: sonst 401 durch IsAuthenticated, bevor Cookie geprüft wird
    permission_classes = [AllowAny]

    def get(self, request, movie_id: int, resolution: str, segment: str):
        user = self.get_authenticated_user(request)
        if not user:
            return _auth_error()

        if "/" in segment or ".." in segment:
            raise Http404("Invalid segment name.")

        if not Video.objects.filter(pk=movie_id).exists():
            raise Http404("Video not found.")

        base_dir = _hls_root() / str(movie_id) / resolution
        segment_path = base_dir / segment
        if not segment_path.is_file():
            raise Http404("Segment not found.")

        return FileResponse(
            open(segment_path, "rb"),
            content_type="video/MP2T",
        )