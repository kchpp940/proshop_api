from django.db import transaction

from base.models import Category, SubCategory, Product, OrderItem, Review


@transaction.atomic
def delete_category(category_id):
    category = Category.objects.get(_id=category_id)

    subcategories = SubCategory.objects.filter(category=category)
    subcategory_ids = list(subcategories.values_list('_id', flat=True))

    affected_products = Product.objects.filter(category__in=subcategory_ids)
    affected_products_count = affected_products.count()

    affected_products.update(category=None)

    subcategories.delete()

    category.delete()

    return {
        'category_deleted': category.name,
        'subcategories_deleted': len(subcategory_ids),
        'products_category_cleared': affected_products_count,
    }


@transaction.atomic
def delete_subcategory(subcategory_id):
    subcategory = SubCategory.objects.get(_id=subcategory_id)

    affected_products = Product.objects.filter(category=subcategory)
    affected_products_count = affected_products.count()

    affected_products.update(category=None)

    subcategory.delete()

    return {
        'subcategory_deleted': subcategory.name,
        'products_category_cleared': affected_products_count,
    }


@transaction.atomic
def delete_product(product_id):
    product = Product.objects.get(_id=product_id)

    image_url = '/static/images/placeholder.png'
    if product.image:
        try:
            image_url = product.image.url
        except:
            image_url = '/static/images/placeholder.png'

    order_items = OrderItem.objects.filter(product=product)
    order_items_count = order_items.count()

    order_items.filter(name__isnull=True).update(name=product.name or '')
    order_items.filter(price__isnull=True).update(price=product.price or 0)
    order_items.filter(image__isnull=True).update(image=image_url)

    order_items.update(product=None)

    reviews = Review.objects.filter(product=product)
    reviews_count = reviews.count()

    reviews.update(product=None)

    product.delete()

    return {
        'product_deleted': product.name,
        'order_items_updated': order_items_count,
        'reviews_updated': reviews_count,
    }
