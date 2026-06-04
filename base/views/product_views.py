from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status

from base.models import Product, Review, SubCategory
from base.serializer import ProductSerializer, ReviewSerializer
from base.services.import_pipeline import run_pipeline, finalize_task


@api_view(['GET'])
@permission_classes([AllowAny])
def getProducts(request):
    query = request.query_params.get('query')

    if query == None:
        query = ''

    products = Product.objects.filter(name__icontains=query)

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProductsByCategory(request, slug):
    sub_categories = SubCategory.objects.filter(category__slug=slug)
    products = Product.objects.filter(category__in=sub_categories)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProductsBySubCategory(request, slug):
    products = Product.objects.filter(category__slug=slug)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getTopRatedProducts(request):
    products = Product.objects.filter(rating__gte=4).order_by('-rating')[:5]
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def getProduct(request, pk):
    product = Product.objects.get(_id=pk)
    serializer = ProductSerializer(product, many=False)
    return Response(serializer.data)


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

    serializer = ProductSerializer(product, many=False)
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

    serializer = ProductSerializer(product, many=False)
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
@permission_classes([IsAdminUser])
def importProducts(request):
    from base.models import ImportTask
    from base.services.row_result import RowResult

    file = request.FILES.get('file')
    if not file:
        task = ImportTask.objects.create(
            created_by=request.user,
            file_name='',
            file_format='',
            status='failed',
        )
        result = RowResult(
            row_number=0,
            status='failed',
            errors=['No file provided'],
        )
        task = finalize_task(task, [result], status='failed', error_message='No file provided')
        return Response({
            'task': {
                'id': task._id,
                'status': task.status,
                'file_name': task.file_name,
                'total_rows': task.total_rows,
                'created_count': task.created_count,
                'updated_count': task.updated_count,
                'skipped_count': task.skipped_count,
                'failed_count': task.failed_count,
                'error_message': task.error_message,
            },
            'rows': [result.to_dict()],
        }, status=status.HTTP_400_BAD_REQUEST)

    file_format = request.data.get('format')
    if not file_format:
        file_name = getattr(file, 'name', '')
        file_format = 'csv' if file_name.endswith('.csv') else 'json'

    if file_format not in ('csv', 'json'):
        task = ImportTask.objects.create(
            created_by=request.user,
            file_name=getattr(file, 'name', ''),
            file_format=file_format or '',
            status='failed',
        )
        result = RowResult(
            row_number=0,
            status='failed',
            errors=[f'Unsupported format: {file_format}. Use csv or json.'],
        )
        task = finalize_task(task, [result], status='failed',
                               error_message=f'Unsupported format: {file_format}. Use csv or json.')
        return Response({
            'task': {
                'id': task._id,
                'status': task.status,
                'file_name': task.file_name,
                'total_rows': task.total_rows,
                'created_count': task.created_count,
                'updated_count': task.updated_count,
                'skipped_count': task.skipped_count,
                'failed_count': task.failed_count,
                'error_message': task.error_message,
            },
            'rows': [result.to_dict()],
        }, status=status.HTTP_400_BAD_REQUEST)

    task, results = run_pipeline(file, file_format, request.user)

    response_status = status.HTTP_200_OK
    if task.status == 'failed' and task.error_message:
        response_status = status.HTTP_400_BAD_REQUEST

    return Response({
        'task': {
            'id': task._id,
            'status': task.status,
            'file_name': task.file_name,
            'total_rows': task.total_rows,
            'created_count': task.created_count,
            'updated_count': task.updated_count,
            'skipped_count': task.skipped_count,
            'failed_count': task.failed_count,
            'error_message': task.error_message,
        },
        'rows': [r.to_dict() for r in results],
    }, status=response_status)


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

        serializer = ProductSerializer(product, many=False)
        return Response(serializer.data)
