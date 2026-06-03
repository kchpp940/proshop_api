from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Category(models.Model):
    _id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    _id = models.AutoField(primary_key=True, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(max_length=200, null=True, blank=True)
    image = models.ImageField(null=True, blank=True,
                              default='placeholder.png')

    class Meta:
        verbose_name_plural = 'Sub Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    image = models.ImageField(null=True, blank=True,
                              default='placeholder.png', upload_to='images/')
    brand = models.CharField(max_length=200, null=True, blank=True)
    category = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True)
    description = models.TextField(null=True, blank=True)
    rating = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    numReviews = models.IntegerField(null=True, blank=True, default=0)
    price = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    countInStock = models.IntegerField(null=True, blank=True, default=0)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)
    clickCount = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return self.name


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True, default=0)
    comment = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.rating)


class Order(models.Model):
    STATUS_CREATED = 'created'
    STATUS_PAID = 'paid'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_CREATED, '已创建'),
        (STATUS_PAID, '已支付'),
        (STATUS_SHIPPED, '已发货'),
        (STATUS_DELIVERED, '已送达'),
        (STATUS_CANCELLED, '已取消'),
        (STATUS_REFUNDED, '已退款'),
    ]

    VALID_TRANSITIONS = {
        STATUS_CREATED: [STATUS_PAID, STATUS_CANCELLED],
        STATUS_PAID: [STATUS_SHIPPED, STATUS_REFUNDED],
        STATUS_SHIPPED: [STATUS_DELIVERED],
    }

    STATUS_FIELD_MAP = {
        STATUS_PAID: ('isPaid', 'paidAt'),
        STATUS_DELIVERED: ('isDelivered', 'deliveredAt'),
        STATUS_CANCELLED: ('isCancelled', 'cancelledAt'),
        STATUS_REFUNDED: ('isRefunded', 'refundedAt'),
    }

    STOCK_RESTORE_STATUSES = set()
    ADMIN_ONLY_STATUSES = {STATUS_SHIPPED, STATUS_DELIVERED, STATUS_CANCELLED, STATUS_REFUNDED}

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paymentMethod = models.CharField(max_length=200, null=True, blank=True)
    taxPrice = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    shippingPrice = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    totalPrice = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED)
    isPaid = models.BooleanField(default=False)
    paidAt = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    isDelivered = models.BooleanField(default=False)
    deliveredAt = models.DateTimeField(
        auto_now_add=False, null=True, blank=True)
    isCancelled = models.BooleanField(default=False)
    cancelledAt = models.DateTimeField(
        auto_now_add=False, null=True, blank=True)
    isRefunded = models.BooleanField(default=False)
    refundedAt = models.DateTimeField(
        auto_now_add=False, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.createdAt)

    def transition_status(self, new_status, operator, note=''):
        from datetime import datetime

        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f'订单当前状态为「{self.get_status_display()}」，'
                f'不允许变更为「{dict(self.STATUS_CHOICES)[new_status]}」',
                code='invalid_transition'
            )

        if new_status in self.ADMIN_ONLY_STATUSES:
            if not operator or not operator.is_staff:
                raise ValidationError(
                    '仅管理员可执行此操作',
                    code='admin_required'
                )
        else:
            if not operator or (not operator.is_staff and operator != self.user):
                raise ValidationError(
                    '无权操作此订单',
                    code='permission_denied'
                )

        self.status = new_status

        if new_status in self.STATUS_FIELD_MAP:
            bool_field, time_field = self.STATUS_FIELD_MAP[new_status]
            setattr(self, bool_field, True)
            setattr(self, time_field, datetime.now())

        self.save()

        OrderStatusHistory.objects.create(
            order=self,
            status=new_status,
            operator=operator,
            note=note
        )

    def _restore_stock(self):
        for item in self.orderitem_set.all():
            if item.product:
                item.product.countInStock += item.qty
                item.product.save()


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(
        max_length=20, choices=Order.STATUS_CHOICES)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True, editable=False)

    class Meta:
        ordering = ['-createdAt']
        verbose_name_plural = 'Order Status Histories'

    def __str__(self):
        return f'{self.order._id} - {self.get_status_display()}'


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True, default=0)
    price = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True)
    image = models.CharField(max_length=200, null=True, blank=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return self.name


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    first_name = models.CharField(max_length=200, null=True, blank=True)
    last_name = models.CharField(max_length=200, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    postal_code = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=200, null=True, blank=True)
    phone_number = models.CharField(max_length=200, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return self.address


class ShippingAddress(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, null=True, blank=True)
    address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.address.address
