from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

GENERIC_INPUT_ERROR = "Please check your inputs and try again."


def token_and_uidb64(user: User) -> tuple[str, str]:
    """Create token and uidb64 for a given user."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uidb64


def build_activation_token(user: User) -> tuple[str, str]:
    """Token + uidb64 for account activation."""
    return token_and_uidb64(user)


def build_password_reset_token(user: User) -> tuple[str, str]:
    """Token + uidb64 for password reset."""
    return token_and_uidb64(user)


def frontend_base_url() -> str:
    """Configured frontend base URL."""
    return getattr(settings, "FRONTEND_BASE_URL", "http://127.0.0.1:5500").rstrip("/")


def frontend_link(path: str, uidb64: str, token: str) -> str:
    """
    Frontend link with query params expected by your frontend:
    ?uid=<uidb64>&token=<token>
    """
    clean_path = path if path.startswith("/") else f"/{path}"
    params = urlencode({"uid": uidb64, "token": token})
    return f"{frontend_base_url()}{clean_path}?{params}"


def activation_link(uidb64: str, token: str) -> str:
    """Frontend activation link."""
    path = getattr(settings, "FRONTEND_ACTIVATION_PATH", "/pages/auth/activate.html")
    return frontend_link(path, uidb64, token)


def password_reset_link(uidb64: str, token: str) -> str:
    """Frontend password reset link."""
    path = getattr(settings, "FRONTEND_PASSWORD_RESET_PATH", "/pages/auth/reset_password.html")
    return frontend_link(path, uidb64, token)


def get_user_from_uid(uidb64: str) -> User | None:
    """Decode uidb64 and return user or None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except Exception:
        return None


def user_for_token(uidb64: str, token: str) -> User | None:
    """Return user if uidb64/token are valid, else None."""
    user = get_user_from_uid(uidb64)
    if not user or not default_token_generator.check_token(user, token):
        return None
    return user


def deactivate_user(user: User) -> None:
    """Keep user inactive until activation."""
    if not user.is_active:
        return
    user.is_active = False
    user.save(update_fields=["is_active"])


def activate_user(user: User) -> None:
    """Activate user account."""
    if user.is_active:
        return
    user.is_active = True
    user.save(update_fields=["is_active"])


def serializer_detail(serializer: Any) -> str | None:
    """Extract a serializer 'detail' if present."""
    detail = getattr(serializer, "errors", {}).get("detail")
    if not detail:
        return None
    return detail[0] if isinstance(detail, list) else str(detail)


def login_error_response(serializer: Any) -> Response:
    """Safe login error response (generic, but supports 'activate' hint)."""
    detail = serializer_detail(serializer)
    message = detail or GENERIC_INPUT_ERROR
    code = status.HTTP_401_UNAUTHORIZED
    if detail and "activate" in detail.lower():
        code = status.HTTP_403_FORBIDDEN
    return Response({"detail": message}, status=code)


def blacklist_refresh_token(token_str: str) -> None:
    """Blacklist refresh token, ignore errors safely."""
    try:
        token = RefreshToken(token_str)
    except TokenError:
        return
    try:
        token.blacklist()
    except Exception:
        return


def safe_refresh_token(token_str: str) -> RefreshToken | None:
    """Return RefreshToken or None if invalid."""
    try:
        return RefreshToken(token_str)
    except TokenError:
        return None


def set_user_password(user: User, new_password: str) -> None:
    """Update user password."""
    user.set_password(new_password)
    user.save(update_fields=["password"])


def enqueue_or_run(job: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Enqueue via RQ, fallback to direct execution."""
    try:
        import django_rq

        django_rq.get_queue("default").enqueue(job, *args, **kwargs)
    except Exception:
        job(*args, **kwargs)
