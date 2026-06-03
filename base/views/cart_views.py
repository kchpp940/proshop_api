from decimal import Decimal

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from base.models import Product, Cart, CartItem
from base.serializer import CartSerializer
from base.utils import get_or_create_cart, calculate_cart_totals


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getCart(request):
    cart = get_or_create_cart(request.user)
    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addToCart(request):
    data = request.data
    product_id = data.get('product_id')
    qty = int(data.get('qty', 1))

    if not product_id:
        return Response({'detail': '请提供商品ID'}, status=status.HTTP_400_BAD_REQUEST)

    if qty < 1:
        return Response({'detail': '数量至少为1'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(_id=product_id)
    except Product.DoesNotExist:
        return Response({'detail': '商品不存在'}, status=status.HTTP_404_NOT_FOUND)

    if product.countInStock < qty:
        return Response({'detail': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)

    cart = get_or_create_cart(request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'qty': qty}
    )

    if not created:
        new_qty = cart_item.qty + qty
        if product.countInStock < new_qty:
            return Response({'detail': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)
        cart_item.qty = new_qty
        cart_item.save()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateCartItem(request, pk):
    data = request.data
    qty = int(data.get('qty', 1))

    if qty < 1:
        return Response({'detail': '数量至少为1'}, status=status.HTTP_400_BAD_REQUEST)

    cart = get_or_create_cart(request.user)

    try:
        cart_item = CartItem.objects.get(_id=pk, cart=cart)
    except CartItem.DoesNotExist:
        return Response({'detail': '购物车商品不存在'}, status=status.HTTP_404_NOT_FOUND)

    if cart_item.product.countInStock < qty:
        return Response({'detail': '库存不足'}, status=status.HTTP_400_BAD_REQUEST)

    cart_item.qty = qty
    cart_item.save()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def removeFromCart(request, pk):
    cart = get_or_create_cart(request.user)

    try:
        cart_item = CartItem.objects.get(_id=pk, cart=cart)
    except CartItem.DoesNotExist:
        return Response({'detail': '购物车商品不存在'}, status=status.HTTP_404_NOT_FOUND)

    cart_item.delete()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clearCart(request):
    cart = get_or_create_cart(request.user)
    cart.items.all().delete()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getCartTotals(request):
    totals = calculate_cart_totals(request.user)
    return Response(totals)
