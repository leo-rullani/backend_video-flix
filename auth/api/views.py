from __future__ import annotations

from typing import Any

from django.conf import settings

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .cookies import clear_auth_cookies, set_access_cookie, set_auth_cookies
from .email_service import send_activation_email, send_password_reset_email
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
)
from .utils import (
    GENERIC_INPUT_ERROR,
    activate_user,
    activation_link,
    blacklist_refresh_token,
    build_activation_token,
    build_password_reset_token,
    deactivate_user,
    enqueue_or_run,
    login_error_response,
    safe_refresh_token,
    set_user_password,
    user_for_token,
)


class RegisterView(APIView):
    """Register a user and send an activation email."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": GENERIC_INPUT_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        deactivate_user(user)
        token, uidb64 = build_activation_token(user)
        enqueue_or_run(send_activation_email, user.email, uidb64, token)

        payload: dict[str, Any] = {"detail": "Registration successful. Please check your email."}
        if getattr(settings, "DEBUG", False):
            payload["activation_link"] = activation_link(uidb64, token)
        return Response(payload, status=status.HTTP_201_CREATED)


class ActivateView(APIView):
    """Activate a user account via uidb64 and token."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request, uidb64: str, token: str) -> Response:
        user = user_for_token(uidb64, token)
        if not user:
            return Response({"message": "Activation failed."}, status=status.HTTP_400_BAD_REQUEST)
        activate_user(user)
        return Response({"message": "Account successfully activated."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    """Authenticate a user and issue JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return login_error_response(serializer)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        response = Response(
            {"detail": "Login successful", "user": {"id": user.id, "username": user.email}},
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Logout the user and invalidate the refresh token."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response({"detail": "Refresh token cookie is missing."}, status=status.HTTP_400_BAD_REQUEST)

        blacklist_refresh_token(token_str)
        response = Response(
            {"detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK,
        )
        clear_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Issue a new access token based on the refresh token cookie."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token_str = request.COOKIES.get("refresh_token")
        if not token_str:
            return Response({"detail": "Refresh token cookie is missing."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = safe_refresh_token(token_str)
        if not refresh:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        access = str(refresh.access_token)
        response = Response({"detail": "Token refreshed", "access": access}, status=status.HTTP_200_OK)
        set_access_cookie(response, access)
        return response


class PasswordResetView(APIView):
    """Request a password reset link by email."""

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": GENERIC_INPUT_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data.get("user")
        if user:
            token, uidb64 = build_password_reset_token(user)
            enqueue_or_run(send_password_reset_email, user.email, uidb64, token)

        return Response(
            {"detail": "An email has been sent to reset your password."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with uidb64 and token."""

    permission_classes = [AllowAny]

    def post(self, request: Request, uidb64: str, token: str) -> Response:
        user = user_for_token(uidb64, token)
        if not user:
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": GENERIC_INPUT_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        set_user_password(user, serializer.validated_data["new_password"])
        return Response({"detail": "Your Password has been successfully reset."}, status=status.HTTP_200_OK)