from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer

User = get_user_model()


def build_activation_token(user):
    """Return token + uidb64 for account activation."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return token, uid


def send_activation_email(request, user, uidb64, token):
    """Send activation email with backend activation link."""
    path = reverse("auth_api:activate", kwargs={"uidb64": uidb64, "token": token})
    link = request.build_absolute_uri(path)
    send_mail(
        "Activate your Videoflix account",
        f"Click to activate your account:\n{link}",
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        [user.email],
        fail_silently=True,
    )
    print("[ACTIVATION LINK]", link)


def get_user_from_uid(uidb64):
    """Decode uidb64 and return user instance or None."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=uid)
    except Exception:
        return None


class RegisterView(APIView):
    """Register user and send activation email."""

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = serializer.save()
        token, uidb64 = build_activation_token(user)
        send_activation_email(request, user, uidb64, token)

        body = {"user": {"id": user.id, "email": user.email}, "token": token}
        return Response(body, status=201)


class ActivateView(APIView):
    """Activate user using uidb64 + token."""

    def get(self, request, uidb64, token):
        user = get_user_from_uid(uidb64)
        if not user or not default_token_generator.check_token(user, token):
            return Response({"message": "Activation failed."}, status=400)

        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"message": "Account successfully activated."})
