from rest_framework import serializers

from .models import Product, Order, OrderItem, Address, ShippingAddress, Review, Category, SubCategory, Cart, CartItem
from users.serializers import UserSerializer


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


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)
    current_price = serializers.SerializerMethodField(read_only=True)
    available_qty = serializers.SerializerMethodField(read_only=True)
    can_purchase = serializers.SerializerMethodField(read_only=True)
    price_changed = serializers.SerializerMethodField(read_only=True)
    snapshot_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = ['_id', 'product', 'qty', 'snapshot_price',
                  'current_price', 'available_qty', 'can_purchase',
                  'price_changed', 'addedAt']

    def get_product(self, obj):
        product = obj.product
        return {
            '_id': product._id,
            'name': product.name,
            'image': product.image.url if product.image else None,
            'brand': product.brand,
        }

    def get_snapshot_price(self, obj):
        return obj.priceSnapshot

    def get_current_price(self, obj):
        return obj.product.price

    def get_available_qty(self, obj):
        return obj.product.countInStock

    def get_can_purchase(self, obj):
        return obj.qty <= obj.product.countInStock and obj.product.countInStock > 0

    def get_price_changed(self, obj):
        if obj.priceSnapshot is None or obj.product.price is None:
            return False
        return obj.priceSnapshot != obj.product.price


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField(read_only=True)
    total_items = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    total_price_at_add = serializers.SerializerMethodField(read_only=True)
    has_price_changes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cart
        fields = ['user_id', 'items', 'total_items', 'total_price',
                  'total_price_at_add', 'has_price_changes',
                  'createdAt', 'updatedAt']

    def get_items(self, obj):
        items = obj.items.all().select_related('product')
        serializer = CartItemSerializer(items, many=True)
        return serializer.data

    def get_total_items(self, obj):
        return sum(item.qty for item in obj.items.all())

    def get_total_price(self, obj):
        return sum(
            item.qty * (item.product.price or 0)
            for item in obj.items.all().select_related('product')
        )

    def get_total_price_at_add(self, obj):
        return sum(
            item.qty * (item.priceSnapshot or item.product.price or 0)
            for item in obj.items.all().select_related('product')
        )

    def get_has_price_changes(self, obj):
        return any(
            (item.priceSnapshot is not None
             and item.product.price is not None
             and item.priceSnapshot != item.product.price)
            for item in obj.items.all().select_related('product')
        )
