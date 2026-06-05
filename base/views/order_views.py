from datetime import datetime

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Product, Order, OrderItem, Address, ShippingAddress
from base.serializer import OrderSerializer
from base.exceptions import (
    EmptyOrderItemsError,
    OrderNotFoundError,
    ProductNotFoundError,
    AddressNotFoundError,
    PermissionDeniedError
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    orderItems = data['orderItems']

    if orderItems and len(orderItems) == 0:
        raise EmptyOrderItemsError()
    else:
        order = Order.objects.create(
            user=user,
            paymentMethod=data['paymentMethod'],
            taxPrice=data['taxPrice'],
            shippingPrice=data['shippingPrice'],
            totalPrice=data['totalPrice'],
        )

        try:
            address = Address.objects.get(_id=data['address_id'])
        except Address.DoesNotExist:
            raise AddressNotFoundError()

        ShippingAddress.objects.create(order=order, address=address)

        for orderItem in orderItems:
            try:
                product = Product.objects.get(_id=orderItem['productId'])
            except Product.DoesNotExist:
                raise ProductNotFoundError()

            item = OrderItem.objects.create(
                order=order,
                product=product,
                name=product.name,
                qty=orderItem['quantity'],
                price=orderItem['price'],
                image=product.image.url
            )

            product.countInStock -= item.qty
            product.save()

        serializer = OrderSerializer(order, many=False)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrderById(request, pk):
    user = request.user

    try:
        order = Order.objects.get(_id=pk)
    except Order.DoesNotExist:
        raise OrderNotFoundError()

    if user.is_staff or user == order.user:
        serializer = OrderSerializer(order, many=False)
        return Response(serializer.data)
    else:
        raise PermissionDeniedError(detail='You are not authorized to view this order')


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
    except Order.DoesNotExist:
        raise OrderNotFoundError()

    order.isPaid = True
    order.paidAt = datetime.now()

    order.save()

    return Response({'detail': 'Order paid', 'code': 'order_paid'}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    try:
        order = Order.objects.get(_id=pk)
    except Order.DoesNotExist:
        raise OrderNotFoundError()

    order.isDelivered = True
    order.deliveredAt = datetime.now()

    order.save()

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)
