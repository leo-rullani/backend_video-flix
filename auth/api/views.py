# auth/api/views.py

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer

User = get_user_model()


def build_activation_token(user):
    """Return token and uidb64 used for account activation."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uidb64


def send_activation_email(request, user, uidb64, token):
    """Send activation email containing the activation link."""
    path = reverse("auth_api:activate", kwargs={"uidb64": uidb64, "token": token})
    activation_link = request.build_absolute_uri(path)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    send_mail(
        "Activate your Videoflix account",
        f"Click to activate your account:\n{activation_link}",
        from_email,
        [user.email],
        fail_silently=True,
    )
    print("[ACTIVATION LINK]", activation_link)


def get_user_from_uid(uidb64):
    """Decode uidb64 and return user instance or None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except Exception:
        return None


def get_tokens_for_user(user):
    """Return refresh and access tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh), str(refresh.access_token)


def set_auth_cookies(response, refresh_token, access_token):
    """Attach JWT tokens as HttpOnly cookies."""
    secure_cookie = not settings.DEBUG
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="Lax",
    )
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="Lax",
    )


class RegisterView(APIView):
    """Register a user and send activation email."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user registration."""
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
        """Validate token and activate the account."""
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
    """Authenticate a user and set JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validate credentials and set JWT cookies."""
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]
        refresh, access = get_tokens_for_user(user)
        body = {
            "detail": "Login successful",
            "user": {"id": user.id, "username": user.email},
        }
        response = Response(body, status=status.HTTP_200_OK)
        set_auth_cookies(response, refresh, access)
        return response