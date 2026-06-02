from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from base.models import Address
from base.serializer import AddressSerializer
from base.services import AddressService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserAddresses(request):
    addresses = AddressService.list_addresses(request.user)
    serializer = AddressSerializer(addresses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserAddressById(request, pk):
    try:
        address = AddressService.get_address(request.user, pk)
    except Address.DoesNotExist:
        return Response(
            {"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND
        )
    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addAddress(request):
    try:
        address = AddressService.create_address(request.user, request.data)
    except Address.DoesNotExist:
        return Response(
            {"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND
        )
    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateAddress(request, pk):
    try:
        address = AddressService.update_address(request.user, pk, request.data)
    except Address.DoesNotExist:
        return Response(
            {"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND
        )
    serializer = AddressSerializer(address, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteAddress(request, pk):
    try:
        address_id = AddressService.delete_address(request.user, pk)
    except Address.DoesNotExist:
        return Response(
            {"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND
        )
    return Response(address_id, status=status.HTTP_200_OK)
