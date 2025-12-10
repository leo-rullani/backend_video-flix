# auth/authentication.py

from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken

User = get_user_model()


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT auth that also reads the token from the 'access_token' cookie.

    Priority:
    1. Authorization header 'Bearer <token>'
    2. Cookie 'access_token'
    """

    def authenticate(self, request: Request) -> Optional[Tuple[User, UntypedToken]]:
        header = self.get_header(request)
        raw_token = None

        if header is not None:
            # Normal SimpleJWT behaviour (Authorization: Bearer <token>)
            raw_token = self.get_raw_token(header)
        else:
            # Our cookie-based auth
            raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        return user, validated_token
