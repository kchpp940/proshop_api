from datetime import datetime
from decimal import Decimal

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from base.models import Coupon
from base.serializer import CouponSerializer
from base.utils import calculate_cart_totals


def calculate_discount(coupon, order_amount):
    order_amount = Decimal(str(order_amount))
    if coupon.discount_type == 'fixed':
        discount = min(coupon.discount_value, order_amount)
    else:
        discount = order_amount * (coupon.discount_value / Decimal('100'))
        discount = min(discount, order_amount)
    return discount.quantize(Decimal('0.01'))


def validate_coupon_instance(coupon, order_amount=None):
    if not coupon.is_active:
        return {'detail': '优惠券已失效'}, status.HTTP_400_BAD_REQUEST

    now = datetime.now()
    if coupon.valid_from > now:
        return {'detail': '优惠券尚未生效'}, status.HTTP_400_BAD_REQUEST

    if coupon.valid_to < now:
        return {'detail': '优惠券已过期'}, status.HTTP_400_BAD_REQUEST

    if coupon.used_count >= coupon.usage_limit:
        return {'detail': '优惠券已被使用完毕'}, status.HTTP_400_BAD_REQUEST

    if order_amount is not None:
        order_amount = Decimal(str(order_amount))
        if order_amount < coupon.minimum_order_amount:
            return {
                'detail': f'订单金额未达到最低要求，最低金额为 {coupon.minimum_order_amount}'
            }, status.HTTP_400_BAD_REQUEST

    return None, None


def validate_coupon_code(coupon_code, order_amount=None):
    try:
        coupon = Coupon.objects.get(code=coupon_code)
    except Coupon.DoesNotExist:
        return None, {'detail': '优惠券不存在'}, status.HTTP_404_NOT_FOUND

    error, status_code = validate_coupon_instance(coupon, order_amount)
    if error:
        return None, error, status_code

    return coupon, None, None


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getCoupons(request):
    coupons = Coupon.objects.all().order_by('-createdAt')
    serializer = CouponSerializer(coupons, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getCouponById(request, pk):
    try:
        coupon = Coupon.objects.get(_id=pk)
        serializer = CouponSerializer(coupon, many=False)
        return Response(serializer.data)
    except Coupon.DoesNotExist:
        return Response({'detail': '优惠券不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def createCoupon(request):
    data = request.data
    try:
        coupon = Coupon.objects.create(
            code=data['code'].upper(),
            name=data.get('name', ''),
            discount_type=data['discount_type'],
            discount_value=Decimal(str(data['discount_value'])),
            minimum_order_amount=Decimal(str(data.get('minimum_order_amount', 0))),
            valid_from=data['valid_from'],
            valid_to=data['valid_to'],
            usage_limit=data.get('usage_limit', 1),
            is_active=data.get('is_active', True),
        )
        serializer = CouponSerializer(coupon, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateCoupon(request, pk):
    try:
        coupon = Coupon.objects.get(_id=pk)
        data = request.data

        coupon.code = data.get('code', coupon.code).upper()
        coupon.name = data.get('name', coupon.name)
        coupon.discount_type = data.get('discount_type', coupon.discount_type)
        coupon.discount_value = Decimal(str(data.get('discount_value', coupon.discount_value)))
        coupon.minimum_order_amount = Decimal(str(data.get('minimum_order_amount', coupon.minimum_order_amount)))
        coupon.valid_from = data.get('valid_from', coupon.valid_from)
        coupon.valid_to = data.get('valid_to', coupon.valid_to)
        coupon.usage_limit = data.get('usage_limit', coupon.usage_limit)
        coupon.is_active = data.get('is_active', coupon.is_active)

        coupon.save()
        serializer = CouponSerializer(coupon, many=False)
        return Response(serializer.data)
    except Coupon.DoesNotExist:
        return Response({'detail': '优惠券不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteCoupon(request, pk):
    try:
        coupon = Coupon.objects.get(_id=pk)
        coupon.delete()
        return Response({'detail': '优惠券已删除'}, status=status.HTTP_204_NO_CONTENT)
    except Coupon.DoesNotExist:
        return Response({'detail': '优惠券不存在'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validateCoupon(request):
    data = request.data
    coupon_code = data.get('coupon_code', '').strip().upper()

    if not coupon_code:
        return Response({'detail': '请输入优惠券码'}, status=status.HTTP_400_BAD_REQUEST)

    cart_totals = calculate_cart_totals(request.user)
    order_amount = cart_totals['total']

    if cart_totals['item_count'] == 0:
        return Response({'detail': '购物车为空'}, status=status.HTTP_400_BAD_REQUEST)

    coupon, error, status_code = validate_coupon_code(coupon_code, order_amount)
    if error:
        return Response(error, status=status_code)

    discount = calculate_discount(coupon, order_amount)
    final_price = (order_amount - discount).quantize(Decimal('0.01'))

    return Response({
        'coupon_code': coupon.code,
        'name': coupon.name,
        'discount_type': coupon.discount_type,
        'discount_value': coupon.discount_value,
        'discount_amount': discount,
        'minimum_order_amount': coupon.minimum_order_amount,
        'subtotal': cart_totals['subtotal'],
        'tax': cart_totals['tax'],
        'shipping': cart_totals['shipping'],
        'original_total': order_amount,
        'final_price': final_price,
        'valid_from': coupon.valid_from,
        'valid_to': coupon.valid_to,
    })
