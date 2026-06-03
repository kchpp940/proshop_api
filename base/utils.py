from decimal import Decimal
from django.conf import settings
from .models import Cart, CartItem, Product


TAX_RATE = getattr(settings, 'TAX_RATE', Decimal('0.08'))
SHIPPING_FEE = getattr(settings, 'SHIPPING_FEE', Decimal('10.00'))
FREE_SHIPPING_THRESHOLD = getattr(settings, 'FREE_SHIPPING_THRESHOLD', Decimal('100.00'))


def get_or_create_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def calculate_subtotal(cart):
    subtotal = Decimal('0.00')
    for item in cart.items.all():
        product = item.product
        subtotal += product.price * item.qty
    return subtotal.quantize(Decimal('0.01'))


def calculate_tax(subtotal):
    return (subtotal * TAX_RATE).quantize(Decimal('0.01'))


def calculate_shipping(subtotal):
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return SHIPPING_FEE.quantize(Decimal('0.01'))


def calculate_cart_totals(user):
    cart = get_or_create_cart(user)
    subtotal = calculate_subtotal(cart)
    tax = calculate_tax(subtotal)
    shipping = calculate_shipping(subtotal)
    total = subtotal + tax + shipping
    
    return {
        'subtotal': subtotal,
        'tax': tax,
        'shipping': shipping,
        'total': total.quantize(Decimal('0.01')),
        'item_count': sum(item.qty for item in cart.items.all()),
        'items': [
            {
                'product_id': item.product._id,
                'name': item.product.name,
                'price': item.product.price,
                'quantity': item.qty,
                'image': item.product.image.url if item.product.image else None,
            }
            for item in cart.items.all()
        ]
    }
