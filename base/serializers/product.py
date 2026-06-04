from rest_framework import serializers

from base.models import Product, Review


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
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
