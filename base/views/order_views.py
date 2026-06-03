from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Product, Order, OrderItem, Address, ShippingAddress, Cart, CartItem
from base.serializer import OrderSerializer


def _calc_tax(subtotal):
    rate = getattr(settings, 'ORDER_TAX_RATE', Decimal('0'))
    return (subtotal * rate).quantize(Decimal('0.01'))


def _calc_shipping(subtotal):
    cfg = getattr(settings, 'ORDER_SHIPPING_CONFIG', {})
    free_threshold = Decimal(str(cfg.get('free_above', '0')))
    flat_fee = Decimal(str(cfg.get('flat_fee', '0')))
    if free_threshold and subtotal >= free_threshold:
        return Decimal('0')
    return flat_fee


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    try:
        cart = Cart.objects.get(user=user)
    except Cart.DoesNotExist:
        return Response({
            'detail': 'Cart is empty',
            'code': 'cart_empty'
        }, status=status.HTTP_400_BAD_REQUEST)

    cart_items = list(CartItem.objects.filter(cart=cart).select_related('product'))

    if not cart_items:
        return Response({
            'detail': 'No order items in cart',
            'code': 'cart_empty'
        }, status=status.HTTP_400_BAD_REQUEST)

    product_ids = [item.product._id for item in cart_items]

    with transaction.atomic():
        products = {
            p._id: p for p in Product.objects.filter(
                _id__in=product_ids
            ).select_for_update().order_by('_id')
        }

        errors = []
        price_changes = []
        for cart_item in cart_items:
            product = products[cart_item.product._id]
            qty = cart_item.qty

            if qty > product.countInStock:
                errors.append({
                    'product_id': product._id,
                    'product_name': product.name,
                    'requested_qty': qty,
                    'available_qty': product.countInStock,
                })

            snapshot_price = cart_item.priceSnapshot
            current_price = product.price
            if snapshot_price is not None and current_price is not None and snapshot_price != current_price:
                price_changes.append({
                    'product_id': product._id,
                    'product_name': product.name,
                    'snapshot_price': snapshot_price,
                    'current_price': current_price,
                    'qty': qty,
                    'price_diff': current_price - snapshot_price,
                    'line_total_diff': qty * (current_price - snapshot_price),
                })

        if errors:
            return Response({
                'detail': 'Insufficient stock for some items',
                'code': 'insufficient_stock',
                'items': errors,
                'price_changes': price_changes
            }, status=status.HTTP_400_BAD_REQUEST)

        subtotal = Decimal('0')
        for cart_item in cart_items:
            product = products[cart_item.product._id]
            subtotal += cart_item.qty * (product.price or Decimal('0'))

        tax_price = _calc_tax(subtotal)
        shipping_price = _calc_shipping(subtotal)
        total_price = subtotal + tax_price + shipping_price

        order = Order.objects.create(
            user=user,
            paymentMethod=data['paymentMethod'],
            taxPrice=tax_price,
            shippingPrice=shipping_price,
            totalPrice=total_price,
        )

        address = Address.objects.get(_id=data['address_id'])
        ShippingAddress.objects.create(order=order, address=address)

        for cart_item in cart_items:
            product = products[cart_item.product._id]
            qty = cart_item.qty
            price = product.price

            OrderItem.objects.create(
                order=order,
                product=product,
                name=product.name,
                qty=qty,
                price=price,
                image=product.image.url
            )

            product.countInStock -= qty
            product.save()

        cart.items.all().delete()

    serializer = OrderSerializer(order, many=False)
    response_data = serializer.data
    if price_changes:
        response_data['price_changes'] = price_changes
        response_data['has_price_changes'] = True
    else:
        response_data['has_price_changes'] = False
    return Response(response_data)


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
