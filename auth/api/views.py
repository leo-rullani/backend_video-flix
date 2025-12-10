# auth/api/views.py

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


def _cookie_options() -> dict:
    """Return common options for auth cookies."""
    return {
        "httponly": True,
        "secure": getattr(settings, "COOKIE_SECURE", False),
        "samesite": getattr(settings, "COOKIE_SAMESITE", "Lax"),
        "path": "/",
    }


def _set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Set access and refresh token cookies on the response."""
    access = str(refresh.access_token)
    opts = _cookie_options()
    response.set_cookie("access_token", access, **opts)
    response.set_cookie("refresh_token", str(refresh), **opts)


def build_activation_token(user):
    """Return token and uidb64 used for account activation."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uidb64


def build_password_reset_token(user):
    """Return token and uidb64 used for password reset."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uidb64


def _build_link(request, name: str, uidb64: str, token: str) -> str:
    """Build an absolute URL for a named route with uid and token."""
    path = reverse(name, kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def send_activation_email(request, user, uidb64, token):
    """Send activation email containing the activation link."""
    link = _build_link(request, "auth_api:activate", uidb64, token)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    send_mail(
        "Activate your Videoflix account",
        f"Click to activate your account:\n{link}",
        from_email,
        [user.email],
        fail_silently=True,
    )
    print("[ACTIVATION LINK]", link)


def send_password_reset_email(request, user, uidb64, token):
    """Send password reset email containing the reset link."""
    link = _build_link(request, "auth_api:password_confirm", uidb64, token)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    send_mail(
        "Reset your Videoflix password",
        f"Use this link to reset your password:\n{link}",
        from_email,
        [user.email],
        fail_silently=True,
    )
    print("[PASSWORD RESET LINK]", link)


def get_user_from_uid(uidb64):
    """Decode uidb64 and return user instance or None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except Exception:
        return None


class RegisterView(APIView):
    """Register a user and send activation email."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        token, uidb64 = build_activation_token(user)
        send_activation_email(request, user, uidb64, token)

        body = {
            "user": {"id": user.id, "email": user.email},
            "token": token,
        }
        return Response(body, status=status.HTTP_201_CREATED)


class ActivateView(APIView):
    """Activate a user account via uidb64 and token from the activation link."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request, uidb64: str, token: str) -> Response:
        user = get_user_from_uid(uidb64)
        if not user:
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return Response(
            {"message": "Account successfully activated."},
            status=status.HTTP_200_OK,
        )


class LoginView(APIView):
    """Authenticate user and issue JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            errors = serializer.errors
            detail = errors.get("detail")

            if detail:
                message = detail[0] if isinstance(detail, list) else str(detail)
                status_code = status.HTTP_401_UNAUTHORIZED
                if "activated" in message:
                    status_code = status.HTTP_403_FORBIDDEN
                return Response({"detail": message}, status=status_code)

            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "detail": "Login successful",
                "user": {"id": user.id, "username": user.email},
            },
            status=status.HTTP_200_OK,
        )
        _set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Logout user and invalidate the refresh token."""

    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response(
                {"detail": "Refresh token cookie is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(token_str)
            try:
                token.blacklist()
            except Exception:
                # If blacklist app is not enabled, just ignore.
                pass
        except TokenError:
            pass

        response = Response(
            {
                "detail": (
                    "Logout successful! All tokens will be deleted. "
                    "Refresh token is now invalid."
                )
            },
            status=status.HTTP_200_OK,
        )
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class TokenRefreshView(APIView):
    """Issue a new access token based on the refresh token cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response(
                {"detail": "Refresh token cookie is missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(token_str)
        except TokenError:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        access = str(refresh.access_token)
        response = Response(
            {"detail": "Token refreshed", "access": access},
            status=status.HTTP_200_OK,
        )
        response.set_cookie("access_token", access, **_cookie_options())
        return response


class PasswordResetView(APIView):
    """Request a password reset link by email."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data.get("user")
        if user:
            token, uidb64 = build_password_reset_token(user)
            send_password_reset_email(request, user, uidb64, token)

        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with uid and token."""

    permission_classes = [AllowAny]

    def post(self, request, uidb64: str, token: str) -> Response:
        user = get_user_from_uid(uidb64)
        if not user or not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Your Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )