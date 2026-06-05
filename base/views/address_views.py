from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status

from base.models import Address
from base.serializer import AddressSerializer
from base.audit import admin_audit, extract_id_from_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_audit(resource_type='ADDRESS', action_type='VIEW')
def getUserAddresses(request):
    user = request.user
    addresses = user.address_set.all()
    serializer = AddressSerializer(addresses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_audit(resource_type='ADDRESS', action_type='VIEW')
def getUserAddressById(request, pk):
    address = Address.objects.get(_id=pk)
    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@admin_audit(resource_type='ADDRESS', action_type='CREATE', extract_resource_id_from_response=extract_id_from_response)
def addAddress(request):
    user = request.user
    data = request.data

    address = Address.objects.create(
        user=user,
        first_name=data['first_name'],
        last_name=data['last_name'],
        address=data['address'],
        city=data['city'],
        postal_code=data['postal_code'],
        country=data['country'],
        phone_number=data['phone_number'],
        is_default=data['is_default'],
    )

    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@admin_audit(resource_type='ADDRESS', action_type='UPDATE')
def updateAddress(request, pk):
    data = request.data
    address = Address.objects.get(_id=pk)

    address.first_name = data['first_name']
    address.last_name = data['last_name']
    address.address = data['address']
    address.city = data['city']
    address.postal_code = data['postal_code']
    address.country = data['country']
    address.phone_number = data['phone_number']
    address.is_default = data['is_default']

    address.save()

    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@admin_audit(resource_type='ADDRESS', action_type='DELETE')
def deleteAddress(request, pk):
    address = Address.objects.get(_id=pk)
    address.delete()

    return Response(address._id, status=status.HTTP_200_OK)
