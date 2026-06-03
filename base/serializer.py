from rest_framework import serializers

from .models import Product, Order, OrderItem, Address, ShippingAddress, Review, Category, SubCategory, Coupon, Cart, CartItem
from users.serializers import UserSerializer


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'
        read_only_fields = ('used_count', 'createdAt')


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = '__all__'

    def get_product(self, obj):
        return {
            '_id': obj.product._id,
            'name': obj.product.name,
            'price': obj.product.price,
            'image': obj.product.image.url if obj.product.image else None,
            'countInStock': obj.product.countInStock,
        }


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'

    def get_totals(self, obj):
        from base.utils import calculate_subtotal, calculate_tax, calculate_shipping
        subtotal = calculate_subtotal(obj)
        tax = calculate_tax(subtotal)
        shipping = calculate_shipping(subtotal)
        return {
            'subtotal': subtotal,
            'tax': tax,
            'shipping': shipping,
            'total': subtotal + tax + shipping,
        }


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class SubCategorySerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubCategory
        fields = '__all__'

    def get_category(self, obj):
        if obj.category is not None:
            return {
                '_id': obj.category._id,
                'name': obj.category.name,
                'slug': obj.category.slug,
            }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    reviews = serializers.SerializerMethodField(read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    image_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_reviews(self, obj):
        reviews = obj.review_set.all()
        serializer = ReviewSerializer(reviews, many=True)
        return serializer.data

    def get_category(self, obj):
        if obj.category is not None:
            return {
                'name': obj.category.category.name,
                'sub_category': obj.category.name,
                'slug': obj.category.slug,
                'cat_slug': obj.category.category.slug,
            }

    def get_image_name(self, obj):
        return obj.image.name.split('/')[-1]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'


class ShippingAddressSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ShippingAddress
        fields = '__all__'

    def get_address(self, obj):
        serializer = AddressSerializer(obj.address, many=False)
        return serializer.data


class OrderSerializer(serializers.ModelSerializer):
    orderItems = serializers.SerializerMethodField(read_only=True)
    shippingAddress = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    def get_orderItems(self, obj):
        items = obj.orderitem_set.all()
        serializer = OrderItemSerializer(items, many=True)
        return serializer.data

    def get_shippingAddress(self, obj):
        try:
            address = ShippingAddressSerializer(
                obj.shippingaddress, many=False).data
        except:
            address = False

        return address

    def get_user(self, obj):
        serializer = UserSerializer(obj.user, many=False)
        return serializer.data
