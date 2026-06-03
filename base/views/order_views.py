from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from django.core.exceptions import ValidationError
from django.db import transaction

from base.models import Product, Order, OrderItem, Address, ShippingAddress
from base.serializer import OrderSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    orderItems = data['orderItems']

    if orderItems and len(orderItems) == 0:
        return Response({'detail': 'No order items'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        order = Order.objects.create(
            user=user,
            paymentMethod=data['paymentMethod'],
            taxPrice=data['taxPrice'],
            shippingPrice=data['shippingPrice'],
            totalPrice=data['totalPrice'],
        )

        OrderStatusHistory = order.status_history.model
        OrderStatusHistory.objects.create(
            order=order,
            status=Order.STATUS_CREATED,
            operator=user,
            note='订单创建成功'
        )

        address = Address.objects.get(_id=data['address_id'])

        ShippingAddress.objects.create(order=order, address=address)

        for orderItem in orderItems:
            product = Product.objects.get(_id=orderItem['productId'])

            # create order item
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
    note = request.data.get('note', '支付确认完成')

    try:
        order.transition_status(Order.STATUS_PAID, request.user, note)
    except ValidationError as e:
        return Response({'detail': e.message, 'code': e.code}, status=status.HTTP_400_BAD_REQUEST)

    return Response('Order paid')


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    order = Order.objects.get(_id=pk)
    note = request.data.get('note', '商品已送达')

    try:
        order.transition_status(Order.STATUS_DELIVERED, request.user, note)
    except ValidationError as e:
        return Response({'detail': e.message, 'code': e.code}, status=status.HTTP_400_BAD_REQUEST)

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToShipped(request, pk):
    order = Order.objects.get(_id=pk)
    note = request.data.get('note', '商品已发货')

    try:
        order.transition_status(Order.STATUS_SHIPPED, request.user, note)
    except ValidationError as e:
        return Response({'detail': e.message, 'code': e.code}, status=status.HTTP_400_BAD_REQUEST)

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToCancelled(request, pk):
    note = request.data.get('note', '订单已取消')

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(_id=pk)
            order_items = list(order.orderitem_set.select_related('product').all())

            product_ids = [item.product_id for item in order_items if item.product_id]
            products = {
                p._id: p for p in Product.objects.select_for_update().filter(_id__in=product_ids)
            }

            order.transition_status(Order.STATUS_CANCELLED, request.user, note)

            for item in order_items:
                product = products.get(item.product_id)
                if product:
                    product.countInStock += item.qty
                    product.save()
    except ValidationError as e:
        return Response({'detail': e.message, 'code': e.code}, status=status.HTTP_400_BAD_REQUEST)

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToRefunded(request, pk):
    order = Order.objects.get(_id=pk)
    note = request.data.get('note', '退款已完成')

    try:
        order.transition_status(Order.STATUS_REFUNDED, request.user, note)
    except ValidationError as e:
        return Response({'detail': e.message, 'code': e.code}, status=status.HTTP_400_BAD_REQUEST)

    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)
