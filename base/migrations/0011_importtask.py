from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0010_orderstatushistory_alter_cartitem_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportTask',
            fields=[
                ('_id', models.AutoField(primary_key=True, serialize=False, editable=False)),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('file_format', models.CharField(blank=True, max_length=10, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('total_rows', models.IntegerField(default=0)),
                ('created_count', models.IntegerField(default=0)),
                ('updated_count', models.IntegerField(default=0)),
                ('skipped_count', models.IntegerField(default=0)),
                ('failed_count', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
