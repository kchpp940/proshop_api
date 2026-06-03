from djoser.serializers import (
    UserCreateSerializer,
    SetUsernameSerializer,
    UsernameResetConfirmSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .utils import (
    normalize_email,
    check_email_availability,
    validate_email_for_registration,
    EmailConflictError,
)

User = get_user_model()


class UserSerializer(UserCreateSerializer):
    email = serializers.EmailField(required=True)

    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'gender',
                  'dob', 'password', 'is_active', 'is_staff')

    def validate_email(self, value):
        validate_email_for_registration(value)
        return normalize_email(value)

    def create(self, validated_data):
        validated_data['email'] = normalize_email(validated_data['email'])
        return super().create(validated_data)


class CustomSetUsernameSerializer(SetUsernameSerializer):
    def validate_new_username(self, value):
        normalized_email = normalize_email(value)
        is_available, error_msg = check_email_availability(
            normalized_email,
            exclude_user_id=self.instance.id
        )
        if not is_available:
            raise EmailConflictError(detail=error_msg)
        return normalized_email


class CustomUsernameResetConfirmSerializer(UsernameResetConfirmSerializer):
    def validate_new_username(self, value):
        normalized_email = normalize_email(value)
        is_available, error_msg = check_email_availability(
            normalized_email,
            exclude_user_id=self.user.id
        )
        if not is_available:
            raise EmailConflictError(detail=error_msg)
        return normalized_email
