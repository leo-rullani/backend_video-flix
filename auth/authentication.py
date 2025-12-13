"""
Authentication backend for cookie-based JWT usage in Videoflix.
"""

from __future__ import annotations

from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken

User = get_user_model()


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth that reads from:
    1) Authorization: Bearer <token>
    2) Cookie: access_token

    Invalid/expired tokens are ignored so AllowAny endpoints keep working.
    """

    def authenticate(self, request: Request) -> Optional[Tuple[User, UntypedToken]]:
        """Authenticate via header or cookie; ignore invalid tokens."""
        header = self.get_header(request)
        raw = self.get_raw_token(header) if header is not None else None
        raw = raw or request.COOKIES.get("access_token")
        if raw is None:
            return None
        try:
            token = self.get_validated_token(raw)
        except Exception:
            return None
        user = self.get_user(token)
        return (user, token) if getattr(user, "is_active", True) else None