from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('base', '0010_order_status_history'),
        ('base', '0010_orderstatushistory_alter_cartitem_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportTask',
            fields=[
                ('_id', models.AutoField(primary_key=True, serialize=False)),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('total_rows', models.IntegerField(default=0)),
                ('created_count', models.IntegerField(default=0)),
                ('updated_count', models.IntegerField(default=0)),
                ('skipped_count', models.IntegerField(default=0)),
                ('failed_count', models.IntegerField(default=0)),
                ('results', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
