# auth/api/views.py

"""
Auth API views for registration, activation, login, logout and password reset.
"""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
)

User = get_user_model()

GENERIC_INPUT_ERROR = "Please check your inputs and try again."

EMAIL_TEMPLATE_HTML = """\
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta charset="utf-8" />
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background:#0b0b0b;color:#ffffff;font-family:Arial,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:24px;">
      <h2 style="color:#e50914;margin:0 0 16px 0;">{title}</h2>
      <p style="margin:0 0 24px 0;line-height:1.6;">{message}</p>
      <a href="{link}" style="display:inline-block;background:#e50914;color:#ffffff;padding:12px 18px;border-radius:6px;text-decoration:none;">
        {button_text}
      </a>
      <p style="margin:24px 0 0 0;font-size:12px;opacity:0.85;word-break:break-all;">
        {link}
      </p>
    </div>
  </body>
</html>
"""


def _cookie_options() -> dict[str, Any]:
    """Return common options for auth cookies."""
    return {
        "httponly": True,
        "secure": getattr(settings, "COOKIE_SECURE", False),
        "samesite": getattr(settings, "COOKIE_SAMESITE", "Lax"),
        "path": "/",
    }


def _set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Set access and refresh token cookies on the response."""
    opts = _cookie_options()
    response.set_cookie("access_token", str(refresh.access_token), **opts)
    response.set_cookie("refresh_token", str(refresh), **opts)


def _clear_auth_cookies(response: Response) -> None:
    """Delete auth cookies from the response."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


def _token_and_uidb64(user: User) -> tuple[str, str]:
    """Create token and uidb64 for a given user."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uidb64


def build_activation_token(user: User) -> tuple[str, str]:
    """Return token and uidb64 used for account activation."""
    return _token_and_uidb64(user)


def build_password_reset_token(user: User) -> tuple[str, str]:
    """Return token and uidb64 used for password reset."""
    return _token_and_uidb64(user)


def _frontend_base_url() -> str:
    """Return configured frontend base URL."""
    return getattr(settings, "FRONTEND_BASE_URL", "http://127.0.0.1:5500").rstrip("/")


def _frontend_link(path: str, uidb64: str, token: str) -> str:
    """Build a frontend link with uid/token query params."""
    clean_path = path if path.startswith("/") else f"/{path}"
    params = urlencode({"uid": uidb64, "token": token})
    return f"{_frontend_base_url()}{clean_path}?{params}"


def _activation_link(uidb64: str, token: str) -> str:
    """Build the frontend activation link."""
    path = getattr(settings, "FRONTEND_ACTIVATION_PATH", "/pages/auth/activate.html")
    return _frontend_link(path, uidb64, token)


def _password_reset_link(uidb64: str, token: str) -> str:
    """Build the frontend password reset link."""
    path = getattr(settings, "FRONTEND_PASSWORD_RESET_PATH", "/pages/auth/reset_password.html")
    return _frontend_link(path, uidb64, token)


def _render_email_html(title: str, message: str, button_text: str, link: str) -> str:
    """Render a small responsive HTML email."""
    return EMAIL_TEMPLATE_HTML.format(
        title=title,
        message=message,
        button_text=button_text,
        link=link,
    )


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Send an email using Django's configured email backend."""
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    send_mail(
        subject,
        text_body,
        from_email,
        [to_email],
        html_message=html_body,
        fail_silently=False,
    )


def _print_dev_link(label: str, link: str) -> None:
    """Print a copy-paste safe link for local development."""
    print(f"[{label} LINK] {link}", flush=True)


def _enqueue_or_run(job: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Enqueue a job via RQ, fallback to direct execution."""
    try:
        import django_rq

        django_rq.get_queue("default").enqueue(job, *args, **kwargs)
    except Exception:
        job(*args, **kwargs)


def send_activation_email(to_email: str, uidb64: str, token: str) -> None:
    """Send activation email with frontend activation link."""
    link = _activation_link(uidb64, token)
    _print_dev_link("ACTIVATION", link)
    html = _render_email_html(
        "Activate your Videoflix account",
        "Please activate your account to sign in.",
        "Activate",
        link,
    )
    _send_email(
        to_email,
        "Activate your Videoflix account",
        f"Activate your account:\n{link}",
        html,
    )


def send_password_reset_email(to_email: str, uidb64: str, token: str) -> None:
    """Send password reset email with frontend reset link."""
    link = _password_reset_link(uidb64, token)
    _print_dev_link("RESET", link)
    html = _render_email_html(
        "Reset your Videoflix password",
        "Set a new password for your account.",
        "Reset password",
        link,
    )
    _send_email(
        to_email,
        "Reset your Videoflix password",
        f"Reset your password:\n{link}",
        html,
    )


def get_user_from_uid(uidb64: str) -> User | None:
    """Decode uidb64 and return the user instance or None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except Exception:
        return None


def _user_for_token(uidb64: str, token: str) -> User | None:
    """Return a user if uidb64 and token are valid."""
    user = get_user_from_uid(uidb64)
    if not user or not default_token_generator.check_token(user, token):
        return None
    return user


def _deactivate_user(user: User) -> None:
    """Ensure the user stays inactive until activation."""
    if not user.is_active:
        return
    user.is_active = False
    user.save(update_fields=["is_active"])


def _activate_user(user: User) -> None:
    """Activate a user account."""
    if user.is_active:
        return
    user.is_active = True
    user.save(update_fields=["is_active"])


def _serializer_detail(serializer: Any) -> str | None:
    """Extract serializer detail message if present."""
    detail = getattr(serializer, "errors", {}).get("detail")
    if not detail:
        return None
    return detail[0] if isinstance(detail, list) else str(detail)


def _login_error_response(serializer: Any) -> Response:
    """Return a safe login error response."""
    detail = _serializer_detail(serializer)
    message = detail or GENERIC_INPUT_ERROR
    code = status.HTTP_401_UNAUTHORIZED
    if detail and "activate" in detail.lower():
        code = status.HTTP_403_FORBIDDEN
    return Response({"detail": message}, status=code)


def _blacklist_refresh_token(token_str: str) -> None:
    """Try to blacklist refresh token; ignore errors safely."""
    try:
        token = RefreshToken(token_str)
    except TokenError:
        return
    try:
        token.blacklist()
    except Exception:
        return


def _safe_refresh_token(token_str: str) -> RefreshToken | None:
    """Return a RefreshToken instance or None if invalid."""
    try:
        return RefreshToken(token_str)
    except TokenError:
        return None


def _token_refresh_response(refresh: RefreshToken) -> Response:
    """Create a response that sets a new access_token cookie."""
    access = str(refresh.access_token)
    response = Response(
        {"detail": "Token refreshed", "access": access},
        status=status.HTTP_200_OK,
    )
    response.set_cookie("access_token", access, **_cookie_options())
    return response


def _set_user_password(user: User, new_password: str) -> None:
    """Update the user's password safely."""
    user.set_password(new_password)
    user.save(update_fields=["password"])


class RegisterView(APIView):
    """Register a user and send an activation email."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": GENERIC_INPUT_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        _deactivate_user(user)
        token, uidb64 = build_activation_token(user)
        _enqueue_or_run(send_activation_email, user.email, uidb64, token)

        return Response(
            {"detail": "Registration successful. Please check your email."},
            status=status.HTTP_201_CREATED,
        )


class ActivateView(APIView):
    """Activate a user account via uidb64 and token."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request, uidb64: str, token: str) -> Response:
        user = _user_for_token(uidb64, token)
        if not user:
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _activate_user(user)
        return Response(
            {"message": "Account successfully activated."},
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    """Authenticate a user and issue JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return _login_error_response(serializer)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        response = Response(
            {"detail": "Login successful", "user": {"id": user.id, "username": user.email}},
            status=status.HTTP_200_OK,
        )
        _set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Logout the user and invalidate the refresh token."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response(
                {"detail": "Refresh token cookie is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _blacklist_refresh_token(token_str)
        response = Response(
            {"detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK,
        )
        _clear_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Issue a new access token based on the refresh token cookie."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response(
                {"detail": "Refresh token cookie is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = _safe_refresh_token(token_str)
        if not refresh:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return _token_refresh_response(refresh)


class PasswordResetView(APIView):
    """Request a password reset link by email."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": GENERIC_INPUT_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data.get("user")
        if user:
            token, uidb64 = build_password_reset_token(user)
            _enqueue_or_run(send_password_reset_email, user.email, uidb64, token)

        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with uidb64 and token."""

    permission_classes = [AllowAny]

    def post(self, request: Request, uidb64: str, token: str) -> Response:
        user = _user_for_token(uidb64, token)
        if not user:
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": GENERIC_INPUT_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _set_user_password(user, serializer.validated_data["new_password"])
        return Response(
            {"detail": "Your Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )