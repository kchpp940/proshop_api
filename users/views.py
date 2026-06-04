from django.views.generic import TemplateView

from djoser.conf import settings
from djoser.compat import get_user_email

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

import os

from .serializers import UserSerializer
from .services import (
    get_account_by_email,
    get_account_by_id,
    get_account_by_uidb64,
    check_account_active,
    check_account_inactive,
    check_activation_token,
    check_password,
    check_email_available,
    activate_account,
    normalize_email,
)
from django.contrib.auth import get_user_model
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login_view(request):
    email = request.data['email']
    password = request.data['password']

    user = get_account_by_email(email)
    check_password(user, password)
    check_account_active(user)

    refresh = RefreshToken.for_user(user)
    token = {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

    return Response(token, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_activation_view(request):
    uidb64 = request.data['uid']
    token = request.data['token']

    user = get_account_by_uidb64(uidb64)
    check_account_inactive(user)
    check_activation_token(user, token)
    activate_account(user)

    context = {'user': user}
    to = [get_user_email(user)]
    settings.EMAIL.confirmation(request, context).send(to)

    refresh = RefreshToken.for_user(user)
    token = {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

    return Response(token, status=status.HTTP_200_OK)


class GoogleCodeVerificationView(TemplateView):
    permission_classes = [AllowAny]
    template_name = 'google_auth.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["redirect_uri"] = os.environ.get("REDIRECT_URL")
        context['success_redirect_uri'] = os.environ.get(
            "SUCCESS_GOOGLE_AUTH_CLIENT_REDIRECT_URL")

        return context


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_request_password_reset(request):
    email = request.data['email']

    user = get_account_by_email(email)

    context = {'user': user}
    to = [get_user_email(user)]
    settings.EMAIL.password_reset(request, context).send(to)

    return Response({'detail': 'Password reset email has been sent'}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateUserProfile(request):
    user = request.user
    data = request.data

    user.first_name = data['first_name']
    user.last_name = data['last_name']
    user.gender = data['gender']
    user.dob = data['dob']
    user.save()

    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUsers(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteUser(request, pk):
    userToDelete = get_account_by_id(pk)
    userToDelete.delete()

    content = {'detail': 'User deleted successfully'}
    return Response(content, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    user = get_account_by_id(pk)
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateUser(request, pk):
    user = get_account_by_id(pk)
    data = request.data

    if 'email' in data and data['email'] != user.email:
        check_email_available(data['email'], exclude_user_id=user.pk)
        data['email'] = normalize_email(data['email'])

    user.first_name = data['first_name']
    user.last_name = data['last_name']
    user.email = data.get('email', user.email)
    user.is_staff = data['isAdmin']
    user.is_active = data['isActive']

    user.save()

    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)
