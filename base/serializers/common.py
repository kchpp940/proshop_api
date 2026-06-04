from rest_framework import serializers


class ProductBaseFields(serializers.Serializer):
    _id = serializers.IntegerField()
    name = serializers.CharField()
    image = serializers.ImageField()
    brand = serializers.CharField()
    description = serializers.CharField()

    class Meta:
        fields = ['_id', 'name', 'image', 'brand', 'description']


class PriceSnapshotFields(serializers.Serializer):
    price = serializers.DecimalField(max_digits=7, decimal_places=2)
    qty = serializers.IntegerField()

    class Meta:
        fields = ['price', 'qty']


class OrderAmountDisplayFields(serializers.Serializer):
    taxPrice = serializers.DecimalField(max_digits=7, decimal_places=2)
    shippingPrice = serializers.DecimalField(max_digits=7, decimal_places=2)
    totalPrice = serializers.DecimalField(max_digits=7, decimal_places=2)
    isPaid = serializers.BooleanField()
    isDelivered = serializers.BooleanField()

    class Meta:
        fields = ['taxPrice', 'shippingPrice', 'totalPrice', 'isPaid', 'isDelivered']
