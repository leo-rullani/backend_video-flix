# auth/api/serializers.py

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration using email and password."""

    password = serializers.CharField(write_only=True)
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "password", "confirmed_password")

    def validate(self, attrs):
        """Validate registration data."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": "Passwords do not match."}
            )
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError(
                {"email": "Email already registered."}
            )
        return attrs

    def create(self, validated_data):
        """Create inactive user with email as username."""
        password = validated_data.pop("password")
        validated_data.pop("confirmed_password", None)
        user = User(
            email=validated_data["email"],
            username=validated_data["email"],
            is_active=False,
        )
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login using email and password."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate credentials and attach the user instance."""
        request = self.context.get("request")
        user = authenticate(
            request=request,
            username=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError(
                {"detail": "Invalid email or password."}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "Account is not activated."}
            )
        attrs["user"] = user
        return attrs