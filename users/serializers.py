from djoser.serializers import (
    UserCreateSerializer,
    SendEmailResetSerializer as DjoserSendEmailResetSerializer,
    UidAndTokenSerializer as DjoserUidAndTokenSerializer,
)
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .services import (
    normalize_email,
    check_email_available,
    get_account_by_email,
    get_account_by_uidb64,
    check_account_inactive,
    check_activation_token,
)

User = get_user_model()


class UserSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'gender',
                  'dob', 'password', 'is_active', 'is_staff')

    def validate_email(self, value):
        normalized_email = normalize_email(value)
        check_email_available(
            normalized_email,
            exclude_user_id=self.instance.pk if self.instance else None,
        )
        return normalized_email

    def create(self, validated_data):
        if 'email' in validated_data:
            validated_data['email'] = normalize_email(validated_data['email'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            validated_data['email'] = normalize_email(validated_data['email'])
        return super().update(instance, validated_data)


class SendEmailResetSerializer(DjoserSendEmailResetSerializer):
    def get_user(self, is_active=True):
        try:
            email = self.data.get(self.email_field, "")
            user = get_account_by_email(email, include_inactive=not is_active)
            if user.has_usable_password():
                return user
        except Exception:
            pass
        return None


class UidAndTokenSerializer(DjoserUidAndTokenSerializer):
    def validate(self, attrs):
        uidb64 = self.initial_data.get("uid", "")
        token = self.initial_data.get("token", "")
        self.user = get_account_by_uidb64(uidb64)
        check_activation_token(self.user, token)
        return attrs


class ActivationSerializer(UidAndTokenSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        check_account_inactive(self.user)
        return attrs
