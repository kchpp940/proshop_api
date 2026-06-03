from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db import IntegrityError

from base.models import Product, Wishlist
from base.serializer import WishlistSerializer


def _get_wishlist_product_ids(user, product_ids=None):
    if not (user and user.is_authenticated):
        return set()
    queryset = Wishlist.objects.filter(user=user)
    if product_ids is not None:
        queryset = queryset.filter(product__id__in=product_ids)
    return set(queryset.values_list('product__id', flat=True))


def _get_serializer_context(request, product_ids=None):
    context = {'request': request}
    context['wishlist_product_ids'] = _get_wishlist_product_ids(request.user, product_ids)
    return context


@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_wishlist(request, pk):
    if not request.user or not request.user.is_authenticated:
        return Response(
            {'detail': 'Authentication required', 'code': 'unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = request.user

    try:
        product = Product.objects.get(_id=pk)
    except Product.DoesNotExist:
        return Response(
            {'detail': 'Product does not exist', 'code': 'product_not_found'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        wishlist_item, created = Wishlist.objects.get_or_create(user=user, product=product)
    except IntegrityError:
        return Response(
            {'detail': 'Product already in wishlist', 'code': 'already_wishlisted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not created:
        return Response(
            {'detail': 'Product already in wishlist', 'code': 'already_wishlisted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer = WishlistSerializer(wishlist_item, many=False, context=_get_serializer_context(request))
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_from_wishlist(request, pk):
    if not request.user or not request.user.is_authenticated:
        return Response(
            {'detail': 'Authentication required', 'code': 'unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = request.user

    try:
        product = Product.objects.get(_id=pk)
    except Product.DoesNotExist:
        return Response(
            {'detail': 'Product does not exist', 'code': 'product_not_found'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        wishlist_item = Wishlist.objects.get(user=user, product=product)
        wishlist_item.delete()
        return Response(
            {'detail': 'Product removed from wishlist', 'code': 'success'},
            status=status.HTTP_200_OK
        )
    except Wishlist.DoesNotExist:
        return Response(
            {'detail': 'Product not in wishlist', 'code': 'not_wishlisted'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_wishlist(request):
    if not request.user or not request.user.is_authenticated:
        return Response(
            {'detail': 'Authentication required', 'code': 'unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = request.user
    wishlist_items = Wishlist.objects.filter(user=user).order_by('-createdAt')
    wishlist_product_ids = set(wishlist_items.values_list('product__id', flat=True))
    context = {'request': request, 'wishlist_product_ids': wishlist_product_ids}
    serializer = WishlistSerializer(wishlist_items, many=True, context=context)
    return Response(serializer.data)
