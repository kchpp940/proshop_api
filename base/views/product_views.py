import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status

from base.models import Product, Review, SubCategory, ImportTask
from base.serializer import ProductSerializer, ReviewSerializer, ImportTaskSerializer


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


def _validate_row(row, row_num):
    errors = []

    name = str(row.get('name', '')).strip()
    if not name:
        errors.append('name is required')

    brand = str(row.get('brand', '')).strip()
    if not brand:
        errors.append('brand is required')

    price_raw = row.get('price')
    price = None
    if price_raw is None or str(price_raw).strip() == '':
        errors.append('price is required')
    else:
        try:
            price = Decimal(str(price_raw).strip())
            if price < 0:
                errors.append('price must be non-negative')
        except InvalidOperation:
            errors.append('price must be a valid decimal number')

    stock_raw = row.get('countInStock')
    count_in_stock = None
    if stock_raw is None or str(stock_raw).strip() == '':
        errors.append('countInStock is required')
    else:
        try:
            count_in_stock = int(str(stock_raw).strip())
            if count_in_stock < 0:
                errors.append('countInStock must be non-negative')
        except (ValueError, TypeError):
            errors.append('countInStock must be a valid integer')

    category_slug = str(row.get('category', '')).strip()
    sub_category = None
    if not category_slug:
        errors.append('category (slug) is required')
    else:
        try:
            sub_category = SubCategory.objects.get(slug=category_slug)
        except SubCategory.DoesNotExist:
            errors.append(
                f'category slug "{category_slug}" does not exist')

    image = str(row.get('image', '')).strip()
    if image and not image.lower().endswith(
            ('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        errors.append(
            'image must be a valid image filename '
            '(.jpg/.jpeg/.png/.gif/.webp)')

    description = str(row.get('description', '')).strip()

    return {
        'errors': errors,
        'cleaned': {
            'name': name,
            'brand': brand,
            'price': price,
            'countInStock': count_in_stock,
            'category': sub_category,
            'image': image,
            'description': description,
        }
    }


def _parse_file(file):
    name_lower = file.name.lower()
    if name_lower.endswith('.csv'):
        try:
            decoded = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            return list(reader), 'csv', None
        except (UnicodeDecodeError, csv.Error) as e:
            return None, 'csv', str(e)
    elif name_lower.endswith('.json'):
        try:
            decoded = file.read().decode('utf-8')
            data = json.loads(decoded)
            if isinstance(data, list):
                return data, 'json', None
            return [data], 'json', None
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, 'json', str(e)
    else:
        return None, None, None


@api_view(['POST'])
@permission_classes([IsAdminUser])
def importProducts(request):
    file = request.FILES.get('file')
    if not file:
        return Response(
            {'detail': 'No file provided. Upload a CSV or JSON file.'},
            status=status.HTTP_400_BAD_REQUEST)

    rows, file_type, parse_error = _parse_file(file)

    if rows is None:
        import_task = ImportTask.objects.create(
            created_by=request.user,
            file_name=file.name,
            status='failed',
            total_rows=0,
            failed_count=0,
            results={
                'parse_error': parse_error or 'Unsupported file format. Use .csv or .json.',
                'file_type': file_type,
            },
        )
        serializer = ImportTaskSerializer(import_task)
        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    error_by_row = {}
    seen_names = {}
    cleaned_by_idx = {}

    for idx, row in enumerate(rows, start=1):
        validation = _validate_row(row, idx)
        if validation['errors']:
            error_by_row[idx] = validation['errors']
        else:
            cleaned = validation['cleaned']
            product_name = cleaned['name']
            if product_name in seen_names:
                error_by_row[idx] = [
                    f'duplicate product name "{product_name}" '
                    f'in row {seen_names[product_name]} and row {idx}'
                ]
                if seen_names[product_name] not in error_by_row:
                    error_by_row[seen_names[product_name]] = [
                        f'duplicate product name "{product_name}" '
                        f'in row {seen_names[product_name]} and row {idx}'
                    ]
            else:
                seen_names[product_name] = idx
                cleaned_by_idx[idx] = cleaned

    if error_by_row:
        row_results = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, row in enumerate(rows, start=1):
            if idx in error_by_row:
                failed_count += 1
                row_results.append({
                    'row': idx,
                    'status': 'failed',
                    'errors': error_by_row[idx],
                })
            else:
                skipped_count += 1
                row_results.append({
                    'row': idx,
                    'status': 'skipped_due_to_batch_error',
                    'name': str(row.get('name', '')),
                    'reason': 'Batch import aborted due to errors in other rows',
                })

        import_task = ImportTask.objects.create(
            created_by=request.user,
            file_name=file.name,
            status='failed',
            total_rows=len(rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            results={'rows': row_results},
        )

        serializer = ImportTaskSerializer(import_task)
        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        import_task = ImportTask.objects.create(
            created_by=request.user,
            file_name=file.name,
            status='processing',
            total_rows=len(rows),
        )

        row_results = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0

        existing_products = Product.objects.filter(
            name__in=[c['name'] for c in cleaned_by_idx.values()]
        ).in_bulk(field_name='name')

        for idx, cleaned in cleaned_by_idx.items():
            product_name = cleaned['name']

            try:
                existing = existing_products.get(product_name)

                if existing:
                    if (existing.brand == cleaned['brand']
                            and existing.price == cleaned['price']
                            and existing.countInStock == cleaned['countInStock']
                            and existing.category == cleaned['category']
                            and existing.description == cleaned['description']):
                        skipped_count += 1
                        row_results.append({
                            'row': idx,
                            'status': 'skipped',
                            'product_id': existing._id,
                            'name': product_name,
                            'reason': 'No changes detected',
                        })
                    else:
                        existing.brand = cleaned['brand']
                        existing.price = cleaned['price']
                        existing.countInStock = cleaned['countInStock']
                        existing.category = cleaned['category']
                        existing.description = cleaned['description']
                        if cleaned['image']:
                            existing.image = cleaned['image']
                        existing.save()
                        updated_count += 1
                        row_results.append({
                            'row': idx,
                            'status': 'updated',
                            'product_id': existing._id,
                            'name': product_name,
                        })
                else:
                    product_data = {
                        'user': request.user,
                        'name': product_name,
                        'brand': cleaned['brand'],
                        'price': cleaned['price'],
                        'countInStock': cleaned['countInStock'],
                        'category': cleaned['category'],
                        'description': cleaned['description'],
                    }
                    if cleaned['image']:
                        product_data['image'] = cleaned['image']
                    Product.objects.create(**product_data)
                    created_count += 1
                    row_results.append({
                        'row': idx,
                        'status': 'created',
                        'name': product_name,
                    })
            except Exception as e:
                failed_count += 1
                row_results.append({
                    'row': idx,
                    'status': 'failed',
                    'errors': [str(e)],
                })

        import_task.status = 'completed'
        import_task.created_count = created_count
        import_task.updated_count = updated_count
        import_task.skipped_count = skipped_count
        import_task.failed_count = failed_count
        import_task.results = {'rows': row_results}
        import_task.save()

    serializer = ImportTaskSerializer(import_task)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getImportTasks(request):
    tasks = ImportTask.objects.all().order_by('-created_at')
    serializer = ImportTaskSerializer(tasks, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getImportTask(request, pk):
    task = ImportTask.objects.get(_id=pk)
    serializer = ImportTaskSerializer(task, many=False)
    return Response(serializer.data)
