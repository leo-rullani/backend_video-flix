# content/api/urls.py

from django.urls import path

from .views import (
    VideoListView,
    VideoHLSManifestView,
    VideoHLSSegmentView,
)

app_name = "content_api"

urlpatterns = [
    path("video/", VideoListView.as_view(), name="video_list"),
    path(
        "video/<int:movie_id>/<str:resolution>/index.m3u8",
        VideoHLSManifestView.as_view(),
        name="video_manifest",
    ),
    path(
        "video/<int:movie_id>/<str:resolution>/<str:segment>/",
        VideoHLSSegmentView.as_view(),
        name="video_segment",
    ),
]
