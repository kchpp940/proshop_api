from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_remove_shippingaddress__id_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='review',
            unique_together={('product', 'user')},
        ),
    ]
