from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from base.models import (
    Product,
    Order,
    OrderItem,
    Address,
    ShippingAddress,
    Cart,
    CartItem,
    Coupon,
    OrderStatusHistory,
)

User = get_user_model()

TAX_RATE = getattr(settings, 'TAX_RATE', Decimal('0.08'))
FREE_SHIPPING_THRESHOLD = getattr(settings, 'FREE_SHIPPING_THRESHOLD', Decimal('100.00'))
STANDARD_SHIPPING_FEE = getattr(settings, 'STANDARD_SHIPPING_FEE', Decimal('10.00'))


class OrderService:
    @staticmethod
    def get_cart_items(user):
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise ValueError('Shopping cart is empty')

        cart_items = CartItem.objects.filter(cart=cart).select_related('product')

        if not cart_items.exists():
            raise ValueError('Shopping cart is empty')

        items = []
        for cart_item in cart_items:
            product = cart_item.product
            if not product:
                raise ValueError('One or more products in cart no longer exist')

            items.append({
                'product': product,
                'quantity': cart_item.qty,
                'price': product.price,
            })

        return items

    @staticmethod
    def lock_inventory(cart_items):
        product_ids = [item['product']._id for item in cart_items]

        products = Product.objects.filter(
            _id__in=product_ids
        ).select_for_update()

        product_map = {p._id: p for p in products}

        for item in cart_items:
            product = product_map.get(item['product']._id)
            if not product:
                raise ValueError(
                    f'Product {item["product"].name} no longer exists'
                )

            if product.countInStock < item['quantity']:
                raise ValueError(
                    f'Insufficient stock for product {product.name}. '
                    f'Available: {product.countInStock}, requested: {item["quantity"]}'
                )

        for item in cart_items:
            product = product_map[item['product']._id]
            product.countInStock -= item['quantity']
            product.save()

    @staticmethod
    def calculate_subtotal(cart_items):
        subtotal = Decimal('0.00')
        for item in cart_items:
            subtotal += item['price'] * item['quantity']
        return round(subtotal, 2)

    @staticmethod
    def calculate_tax(subtotal):
        return round(subtotal * TAX_RATE, 2)

    @staticmethod
    def calculate_shipping(subtotal):
        if subtotal >= FREE_SHIPPING_THRESHOLD:
            return Decimal('0.00')
        return STANDARD_SHIPPING_FEE

    @staticmethod
    def validate_coupon(coupon_code, subtotal):
        if not coupon_code:
            return Decimal('0.00')

        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            raise ValueError(f'Invalid coupon code: {coupon_code}')

        if not coupon.is_active:
            raise ValueError(f'Coupon {coupon_code} is not active')

        now = timezone.now()

        if coupon.valid_from and now < coupon.valid_from:
            raise ValueError(f'Coupon {coupon_code} is not yet valid')

        if coupon.valid_to and now > coupon.valid_to:
            raise ValueError(f'Coupon {coupon_code} has expired')

        if coupon.used_count >= coupon.usage_limit:
            raise ValueError(f'Coupon {coupon_code} has reached usage limit')

        if subtotal < coupon.min_order_value:
            raise ValueError(
                f'Minimum order value for coupon {coupon_code} is '
                f'{coupon.min_order_value}, current subtotal is {subtotal}'
            )

        if coupon.discount_type == 'percentage':
            discount = round(subtotal * (coupon.discount_value / Decimal('100')), 2)
        elif coupon.discount_type == 'fixed':
            discount = coupon.discount_value
        else:
            discount = Decimal('0.00')

        if discount > subtotal:
            discount = subtotal

        return discount

    @staticmethod
    def create_order_items(order, cart_items):
        order_items = []
        for item in cart_items:
            product = item['product']
            quantity = item['quantity']
            price = item['price']

            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                name=product.name,
                qty=quantity,
                price=price,
                image=product.image.url if product.image else '',
            )
            order_items.append(order_item)

        return order_items

    @staticmethod
    def clear_cart(user):
        try:
            cart = Cart.objects.get(user=user)
            CartItem.objects.filter(cart=cart).delete()
        except Cart.DoesNotExist:
            pass

    @staticmethod
    def create_shipping_address(order, address_id):
        try:
            address = Address.objects.get(_id=address_id)
        except Address.DoesNotExist:
            raise ValueError(f'Address with id {address_id} does not exist')

        if address.user != order.user:
            raise ValueError('Address does not belong to the user')

        ShippingAddress.objects.create(
            order=order,
            address=address,
        )

    @staticmethod
    def add_status_history(order, status, operator=None, note=''):
        OrderStatusHistory.objects.create(
            order=order,
            status=status,
            note=note,
            operator=operator,
        )

    @staticmethod
    @transaction.atomic
    def create_order(user, address_id, payment_method, coupon_code=None):
        cart_items = OrderService.get_cart_items(user)

        subtotal = OrderService.calculate_subtotal(cart_items)
        discount = OrderService.validate_coupon(coupon_code, subtotal)
        discounted_subtotal = subtotal - discount

        tax = OrderService.calculate_tax(discounted_subtotal)
        shipping = OrderService.calculate_shipping(discounted_subtotal)
        total = discounted_subtotal + tax + shipping

        OrderService.lock_inventory(cart_items)

        order = Order.objects.create(
            user=user,
            paymentMethod=payment_method,
            taxPrice=tax,
            shippingPrice=shipping,
            totalPrice=total,
            status='created',
        )

        OrderService.create_shipping_address(order, address_id)
        OrderService.create_order_items(order, cart_items)

        if coupon_code and discount > 0:
            coupon = Coupon.objects.get(code=coupon_code)
            coupon.used_count += 1
            coupon.save()

        OrderService.add_status_history(
            order, 'created', operator=user, note='Order created'
        )
        OrderService.clear_cart(user)

        return order

    @staticmethod
    @transaction.atomic
    def update_order_to_paid(order, operator=None):
        if order.isPaid:
            raise ValueError('Order is already paid')

        order.isPaid = True
        order.paidAt = datetime.now()
        order.status = 'paid'
        order.save()

        OrderService.add_status_history(
            order, 'paid', operator=operator, note='Order marked as paid'
        )

        return order

    @staticmethod
    @transaction.atomic
    def update_order_to_delivered(order, operator=None):
        if not order.isPaid:
            raise ValueError('Order must be paid before marking as delivered')

        if order.isDelivered:
            raise ValueError('Order is already delivered')

        order.isDelivered = True
        order.deliveredAt = datetime.now()
        order.status = 'delivered'
        order.save()

        OrderService.add_status_history(
            order, 'delivered', operator=operator, note='Order marked as delivered'
        )

        return order
