# Placeholder migration - bridges gap between 0006 and 0008
# This file exists solely to satisfy the dependency chain referenced by 0008

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_cart_cartitem'),
    ]

    operations = []
