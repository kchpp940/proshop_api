from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status

from base.models import Product, Review, SubCategory, Wishlist
from base.serializer import ProductSerializer, ReviewSerializer


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


@api_view(['GET'])
@permission_classes([AllowAny])
def getProducts(request):
    query = request.query_params.get('query')

    if query == None:
        query = ''

    products = Product.objects.filter(name__icontains=query)
    product_ids = list(products.values_list('_id', flat=True))

    serializer = ProductSerializer(products, many=True, context=_get_serializer_context(request, product_ids))
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProductsByCategory(request, slug):
    sub_categories = SubCategory.objects.filter(category__slug=slug)
    products = Product.objects.filter(category__in=sub_categories)
    product_ids = list(products.values_list('_id', flat=True))
    serializer = ProductSerializer(products, many=True, context=_get_serializer_context(request, product_ids))
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProductsBySubCategory(request, slug):
    products = Product.objects.filter(category__slug=slug)
    product_ids = list(products.values_list('_id', flat=True))
    serializer = ProductSerializer(products, many=True, context=_get_serializer_context(request, product_ids))
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getTopRatedProducts(request):
    products = Product.objects.filter(rating__gte=4).order_by('-rating')[:5]
    product_ids = list(products.values_list('_id', flat=True))
    serializer = ProductSerializer(products, many=True, context=_get_serializer_context(request, product_ids))
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProduct(request, pk):
    try:
        product = Product.objects.get(_id=pk)
        serializer = ProductSerializer(product, many=False, context=_get_serializer_context(request, [pk]))
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response(
            {'detail': 'Product does not exist', 'code': 'product_not_found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateProduct(request, pk):
    data = request.data

    product = Product.objects.get(_id=pk)

    category = SubCategory.objects.get(slug=data['category'])

    product.name = data['name']
    product.price = data['price']
    product.brand = data['brand']
    product.category = category
    product.countInStock = data['countInStock']
    product.description = data['description']

    product.save()

    serializer = ProductSerializer(product, many=False, context=_get_serializer_context(request))
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def createProduct(request):
    user = request.user

    product = Product.objects.create(
        user=user,
        name='Sample Name',
        description='',
        price=0,
        brand='Sample Brand',
        countInStock=0,
    )

    serializer = ProductSerializer(product, many=False, context=_get_serializer_context(request))
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteProduct(request, pk):
    product = Product.objects.get(_id=pk)
    product.delete()

    content = {'detail': 'Product deleted successfully'}
    return Response(content, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([AllowAny])
def incrementClickCount(request, pk):
    product = Product.objects.get(_id=pk)
    product.clickCount += 1
    product.save()

    content = {'detail': 'Click count was incremented'}
    return Response(content, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def getHotCategories(request):
    hot_categories = []
    products = Product.objects.all()
    categories = SubCategory.objects.all()

    for category in categories:
        category_clicks = 0
        for product in products:
            if product.category == category:
                category_clicks += product.clickCount
        hot_categories.append({
            'category': category.name,
            'main_category': category.category.name,
            'main_category_slug': category.category.slug,
            'slug': category.slug,
            'image': category.image.url,
            'clicks': category_clicks
        })

    # Sort by clicks in descending order and get top 10
    hot_categories.sort(key=lambda x: x['clicks'], reverse=True)
    hot_categories = hot_categories[:10]

    return Response(hot_categories)


@api_view(['POST'])
@permission_classes([AllowAny])
def uploadImage(request):
    data = request.data

    product_id = data['product_id']
    product = Product.objects.get(_id=product_id)

    product.image = request.FILES.get('image')
    product.save()

    content = {'detail': 'Image was uploaded'}

    return Response(content, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserReviews(request):
    user = request.user
    reviews = user.review_set.all()
    serializer = ReviewSerializer(reviews, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createProductReview(request, pk):
    user = request.user
    data = request.data

    product = Product.objects.get(_id=pk)

    alreadyReviewed = product.review_set.all().filter(user=user).exists()

    if alreadyReviewed:
        content = {'detail': 'Product already reviewed'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    elif data['rating'] == 0:
        content = {'detail': 'Please select a rating'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    else:
        review = Review.objects.create(
            user=user,
            product=product,
            name=data['name'],
            rating=data['rating'],
            comment=data['comment'],
        )

        reviews = product.review_set.all()

        total = 0

        for i in reviews:
            total += i.rating

        product.rating = total / len(reviews)
        product.numReviews = len(reviews)
        product.save()

        serializer = ProductSerializer(product, many=False, context=_get_serializer_context(request))
        return Response(serializer.data)
