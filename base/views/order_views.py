from datetime import datetime

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Product, Order, OrderItem, Address, ShippingAddress
from base.serializer import OrderSerializer
from base.services import OrderService


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    payment_method = data.get('paymentMethod', '')
    address_id = data.get('address_id')
    coupon_code = data.get('couponCode')

    if not address_id:
        return Response(
            {'detail': 'Address ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not payment_method:
        return Response(
            {'detail': 'Payment method is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = OrderService.create_order(
            user=user,
            address_id=address_id,
            payment_method=payment_method,
            coupon_code=coupon_code,
        )
    except ValueError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)


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
            return Response(
                {'detail': 'You are not authorized to view this order'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except Order.DoesNotExist:
        return Response(
            {'detail': 'Order does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )


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
    try:
        order = Order.objects.get(_id=pk)
        OrderService.update_order_to_paid(order, operator=request.user)
    except Order.DoesNotExist:
        return Response(
            {'detail': 'Order does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response('Order paid')


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    try:
        order = Order.objects.get(_id=pk)
        OrderService.update_order_to_delivered(order, operator=request.user)
    except Order.DoesNotExist:
        return Response(
            {'detail': 'Order does not exist'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)
