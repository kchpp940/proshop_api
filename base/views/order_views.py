from datetime import datetime

from django.db import DatabaseError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Order
from base.serializer import OrderSerializer
from base.services import OrderService, OrderServiceError


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    try:
        order = OrderService.create_order(request.user, request.data)
        serializer = OrderSerializer(order, many=False)
        return Response(serializer.data)
    except OrderServiceError as e:
        return Response({'detail': e.message}, status=e.status_code)
    except DatabaseError as e:
        return Response(
            {'detail': f'Order creation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrderById(request, pk):
    user = request.user

    try:
        order = Order.objects.get(_id=pk)

        if user.is_staff or user == order.user:
            serializer = OrderSerializer(order, many=False)
            return Response(serializer.data)
        else:
            return Response({'detail': 'You are not authorized to view this order'}, status=status.HTTP_401_UNAUTHORIZED)
    except:
        return Response({'detail': 'Order does not exist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserOrders(request):
    user = request.user

    orders = user.order_set.all()

    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getOrders(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateOrderToPaid(request, pk):
    order = Order.objects.get(_id=pk)

    order.isPaid = True
    order.paidAt = datetime.now()

    order.save()

    return Response('Order paid')


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    order = Order.objects.get(_id=pk)

    order.isDelivered = True
    order.deliveredAt = datetime.now()

    order.save()

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)
