from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from base.models import Product, Cart, CartItem
from base.serializer import CartSerializer, CartItemSerializer


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getCart(request):
    cart = get_or_create_cart(request.user)
    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addItemToCart(request):
    user = request.user
    data = request.data

    product_id = data.get('productId')
    qty = data.get('qty', 1)

    try:
        product = Product.objects.get(_id=product_id)
    except Product.DoesNotExist:
        return Response(
            {'detail': 'Product not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if qty <= 0:
        return Response(
            {'detail': 'Quantity must be greater than 0'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if qty > product.countInStock:
        return Response({
            'detail': f'Only {product.countInStock} items available',
            'code': 'insufficient_stock',
            'items': [{
                'product_id': product._id,
                'product_name': product.name,
                'requested_qty': qty,
                'available_qty': product.countInStock,
            }]
        }, status=status.HTTP_400_BAD_REQUEST)

    cart = get_or_create_cart(user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={
            'qty': qty,
            'priceSnapshot': product.price
        }
    )

    if not created:
        new_qty = cart_item.qty + qty
        if new_qty > product.countInStock:
            return Response({
                'detail': f'Only {product.countInStock} items available. Cart has {cart_item.qty} already.',
                'code': 'insufficient_stock',
                'items': [{
                    'product_id': product._id,
                    'product_name': product.name,
                    'requested_qty': new_qty,
                    'available_qty': product.countInStock,
                    'current_cart_qty': cart_item.qty,
                }]
            }, status=status.HTTP_400_BAD_REQUEST)
        cart_item.qty = new_qty
        cart_item.save()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateCartItem(request, pk):
    user = request.user
    data = request.data
    qty = data.get('qty')

    try:
        cart_item = CartItem.objects.get(_id=pk, cart__user=user)
    except CartItem.DoesNotExist:
        return Response(
            {'detail': 'Cart item not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if qty is None or qty <= 0:
        return Response(
            {'detail': 'Quantity must be greater than 0'},
            status=status.HTTP_400_BAD_REQUEST
        )

    product = cart_item.product
    if qty > product.countInStock:
        return Response({
            'detail': f'Only {product.countInStock} items available',
            'code': 'insufficient_stock',
            'items': [{
                'product_id': product._id,
                'product_name': product.name,
                'requested_qty': qty,
                'available_qty': product.countInStock,
            }]
        }, status=status.HTTP_400_BAD_REQUEST)

    cart_item.qty = qty
    cart_item.priceSnapshot = product.price
    cart_item.save()

    cart = get_or_create_cart(user)
    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def removeFromCart(request, pk):
    user = request.user

    try:
        cart_item = CartItem.objects.get(_id=pk, cart__user=user)
    except CartItem.DoesNotExist:
        return Response(
            {'detail': 'Cart item not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    cart_item.delete()

    cart = get_or_create_cart(user)
    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clearCart(request):
    user = request.user
    cart = get_or_create_cart(user)
    cart.items.all().delete()

    serializer = CartSerializer(cart, many=False)
    return Response(serializer.data)
