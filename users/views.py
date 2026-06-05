from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
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
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_login_view(request):
    email = request.data['email']
    password = request.data['password']

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'detail': 'There is no account for this email address'}, status=status.HTTP_404_NOT_FOUND)

    if user.check_password(password):

        if user.is_active:
            refresh = RefreshToken.for_user(user)

            token = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }

            return Response(token, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Your account is not activated'}, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({'detail': 'Your password is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def custom_activation_view(request):
    uidb64 = request.data['uid']
    token = request.data['token']

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response({'detail': 'Invalid activation link'}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({'detail': 'Your account is already activated'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()

            context = {'user': user}
            to = [get_user_email(user)]
            settings.EMAIL.confirmation(request, context).send(to)

            refresh = RefreshToken.for_user(user)

            token = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }

            return Response(token, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Your token is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)


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

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'detail': 'There is no account for this email address'}, status=status.HTTP_404_NOT_FOUND)

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
    userToDelete = User.objects.get(id=pk)
    userToDelete.delete()

    content = {'detail': 'User deleted successfully'}
    return Response(content, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    user = User.objects.get(id=pk)
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateUser(request, pk):
    user = User.objects.get(id=pk)

    data = request.data

    user.first_name = data['first_name']
    user.last_name = data['last_name']
    user.email = data['email']
    user.is_staff = data['isAdmin']
    user.is_active = data['isActive']

    user.save()

    serializer = UserSerializer(user, many=False)

    return Response(serializer.data)
