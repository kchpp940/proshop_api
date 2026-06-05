# Generated manually - Admin Action Audit model
# Mounted at the last confirmable complete leaf node in the migration graph

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('base', '0006_cart_cartitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminActionAudit',
            fields=[
                ('_id', models.AutoField(editable=False, primary_key=True, serialize=False)),
                ('operator_email', models.EmailField(blank=True, max_length=255, null=True)),
                ('resource_type', models.CharField(choices=[('PRODUCT', 'Product'), ('ORDER', 'Order'), ('USER', 'User'), ('ADDRESS', 'Address'), ('CATEGORY', 'Category')], max_length=50)),
                ('resource_id', models.CharField(blank=True, max_length=100, null=True)),
                ('action_type', models.CharField(choices=[('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete'), ('STATUS_CHANGE', 'Status Change'), ('VIEW', 'View')], max_length=50)),
                ('request_path', models.CharField(blank=True, max_length=500, null=True)),
                ('request_method', models.CharField(blank=True, max_length=10, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500, null=True)),
                ('status', models.CharField(choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')], max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('request_data', models.JSONField(blank=True, null=True)),
                ('response_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('operator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Admin Action Audits',
                'ordering': ['-created_at'],
            },
        ),
    ]
