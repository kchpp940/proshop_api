# Generated manually for Coupon model and Order discount fields

from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_cart_cartitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('_id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('discount_type', models.CharField(choices=[('fixed', '固定金额'), ('percentage', '百分比折扣')], max_length=20)),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('minimum_order_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, validators=[MinValueValidator(0)])),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('usage_limit', models.IntegerField(default=1, validators=[MinValueValidator(1)])),
                ('used_count', models.IntegerField(default=0, validators=[MinValueValidator(0)])),
                ('is_active', models.BooleanField(default=True)),
                ('createdAt', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Coupons',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='couponCode',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='discountAmount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=7, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='finalPrice',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True),
        ),
    ]
