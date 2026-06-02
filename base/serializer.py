from rest_framework import serializers

from .models import Product, Order, OrderItem, Address, ShippingAddress, Review, Category, SubCategory
from users.serializers import UserSerializer


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class SubCategorySerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

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
        return None

    def get_image_url(self, obj):
        if obj.image:
            try:
                return obj.image.url
            except:
                return '/static/images/placeholder.png'
        return '/static/images/placeholder.png'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    reviews = serializers.SerializerMethodField(read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    image_name = serializers.SerializerMethodField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    is_uncategorized = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

    def get_reviews(self, obj):
        try:
            reviews = obj.review_set.all()
            serializer = ReviewSerializer(reviews, many=True)
            return serializer.data
        except:
            return []

    def get_category(self, obj):
        if obj.category is not None:
            try:
                main_category = obj.category.category
                if main_category is not None:
                    return {
                        'name': main_category.name,
                        'sub_category': obj.category.name,
                        'slug': obj.category.slug,
                        'cat_slug': main_category.slug,
                    }
                return {
                    'name': None,
                    'sub_category': obj.category.name,
                    'slug': obj.category.slug,
                    'cat_slug': None,
                }
            except:
                return None
        return None

    def get_is_uncategorized(self, obj):
        if obj.category is None:
            return True
        try:
            if obj.category.category is None:
                return True
        except:
            return True
        return False

    def get_image_name(self, obj):
        try:
            if obj.image and obj.image.name:
                return obj.image.name.split('/')[-1]
        except:
            pass
        return 'placeholder.png'

    def get_image_url(self, obj):
        try:
            if obj.image:
                return obj.image.url
        except:
            pass
        return '/static/images/placeholder.png'


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderItem
        fields = '__all__'

    def get_product_info(self, obj):
        try:
            if obj.product is not None:
                return {
                    '_id': obj.product._id,
                    'name': obj.product.name,
                    'image_url': obj.product.image.url if obj.product.image else None,
                    'is_available': True,
                }
        except:
            pass
        return {
            '_id': None,
            'name': obj.name,
            'image_url': obj.image,
            'is_available': False,
        }


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
        try:
            items = obj.orderitem_set.all()
            serializer = OrderItemSerializer(items, many=True)
            return serializer.data
        except:
            return []

    def get_shippingAddress(self, obj):
        try:
            address = ShippingAddressSerializer(
                obj.shippingaddress, many=False).data
        except:
            address = None

        return address

    def get_user(self, obj):
        try:
            if obj.user is not None:
                serializer = UserSerializer(obj.user, many=False)
                return serializer.data
        except:
            pass
        return None
