from datetime import datetime
from decimal import Decimal

from django.db import transaction
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Product, Order, OrderItem, Address, ShippingAddress, Coupon, Cart
from base.serializer import OrderSerializer
from base.views.coupon_views import validate_coupon_instance, calculate_discount
from base.utils import calculate_cart_totals


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def addOrderItems(request):
    user = request.user
    data = request.data

    cart = Cart.objects.select_for_update().filter(user=user).first()
    if not cart or cart.items.count() == 0:
        return Response({'detail': '购物车为空'}, status=status.HTTP_400_BAD_REQUEST)

    cart_totals = calculate_cart_totals(user)
    subtotal = cart_totals['subtotal']
    tax_price = cart_totals['tax']
    shipping_price = cart_totals['shipping']
    total_price = cart_totals['total']

    address_id = data.get('address_id')
    if not address_id:
        return Response({'detail': '请选择收货地址'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        address = Address.objects.get(_id=address_id, user=user)
    except Address.DoesNotExist:
        return Response({'detail': '收货地址不存在'}, status=status.HTTP_400_BAD_REQUEST)

    payment_method = data.get('paymentMethod')
    if not payment_method:
        return Response({'detail': '请选择支付方式'}, status=status.HTTP_400_BAD_REQUEST)

    coupon_code = data.get('coupon_code', '').strip().upper() if data.get('coupon_code') else None
    discount_amount = Decimal('0.00')
    final_price = total_price
    used_coupon = None

    if coupon_code:
        coupon = Coupon.objects.select_for_update().filter(code=coupon_code).first()
        if not coupon:
            return Response({'detail': '优惠券不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        error, status_code = validate_coupon_instance(coupon, total_price)
        if error:
            return Response(error, status=status_code)
        
        discount_amount = calculate_discount(coupon, total_price)
        final_price = (total_price - discount_amount).quantize(Decimal('0.01'))
        used_coupon = coupon

    order = Order.objects.create(
        user=user,
        paymentMethod=payment_method,
        taxPrice=tax_price,
        shippingPrice=shipping_price,
        totalPrice=total_price,
        couponCode=coupon_code,
        discountAmount=discount_amount,
        finalPrice=final_price,
    )

    if used_coupon:
        used_coupon.used_count += 1
        used_coupon.save()

    ShippingAddress.objects.create(order=order, address=address)

    cart_items = cart.items.select_related('product').all()
    for cart_item in cart_items:
        product = cart_item.product

        if product.countInStock < cart_item.qty:
            transaction.set_rollback(True)
            return Response(
                {'detail': f'商品 {product.name} 库存不足'},
                status=status.HTTP_400_BAD_REQUEST
            )

        OrderItem.objects.create(
            order=order,
            product=product,
            name=product.name,
            qty=cart_item.qty,
            price=product.price,
            image=product.image.url if product.image else None
        )

        product.countInStock -= cart_item.qty
        product.save()

    cart.items.all().delete()

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
