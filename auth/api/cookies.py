from __future__ import annotations

from typing import Any

from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def cookie_options() -> dict[str, Any]:
    """Common options for auth cookies."""
    return {
        "httponly": True,
        "secure": getattr(settings, "COOKIE_SECURE", False),
        "samesite": getattr(settings, "COOKIE_SAMESITE", "Lax"),
        "path": "/",
    }


def set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Set access_token and refresh_token cookies."""
    opts = cookie_options()
    response.set_cookie("access_token", str(refresh.access_token), **opts)
    response.set_cookie("refresh_token", str(refresh), **opts)


def clear_auth_cookies(response: Response) -> None:
    """Delete auth cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


def set_access_cookie(response: Response, access: str) -> None:
    """Set only the access_token cookie."""
    response.set_cookie("access_token", access, **cookie_options())
