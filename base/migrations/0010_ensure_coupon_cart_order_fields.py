# Correction migration: ensure Coupon, Cart, CartItem tables and Order discount fields exist
# This migration is idempotent and safe to run regardless of previous migration state

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator


def table_exists(cursor, table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None


def get_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def ensure_coupon_table(apps, schema_editor):
    """Ensure Coupon table exists with correct structure."""
    cursor = schema_editor.connection.cursor()

    if not table_exists(cursor, 'base_coupon'):
        Coupon = apps.get_model('base', 'Coupon')
        schema_editor.create_model(Coupon)
        return

    columns = get_columns(cursor, 'base_coupon')
    required_columns = {
        'code': 'VARCHAR(50) NULL',
        'name': 'VARCHAR(100) NULL',
        'discount_type': 'VARCHAR(20) NULL',
        'discount_value': 'DECIMAL(10,2) NOT NULL DEFAULT 0',
        'minimum_order_amount': 'DECIMAL(10,2) NOT NULL DEFAULT 0',
        'valid_from': 'DATETIME NULL',
        'valid_to': 'DATETIME NULL',
        'usage_limit': 'INTEGER NOT NULL DEFAULT 1',
        'used_count': 'INTEGER NOT NULL DEFAULT 0',
        'is_active': 'INTEGER NOT NULL DEFAULT 1',
        'createdAt': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
        '_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    }

    for col, definition in required_columns.items():
        if col not in columns:
            try:
                schema_editor.execute(f'ALTER TABLE base_coupon ADD COLUMN "{col}" {definition}')
            except Exception:
                pass


def ensure_order_discount_fields(apps, schema_editor):
    """Ensure Order table has couponCode, discountAmount, finalPrice fields."""
    cursor = schema_editor.connection.cursor()

    if not table_exists(cursor, 'base_order'):
        return

    columns = get_columns(cursor, 'base_order')

    if 'couponCode' not in columns:
        try:
            schema_editor.execute(
                'ALTER TABLE base_order ADD COLUMN "couponCode" VARCHAR(50) NULL'
            )
        except Exception:
            pass
    if 'discountAmount' not in columns:
        try:
            schema_editor.execute(
                'ALTER TABLE base_order ADD COLUMN "discountAmount" DECIMAL(7,2) NULL DEFAULT 0'
            )
        except Exception:
            pass
    if 'finalPrice' not in columns:
        try:
            schema_editor.execute(
                'ALTER TABLE base_order ADD COLUMN "finalPrice" DECIMAL(7,2) NULL'
            )
        except Exception:
            pass


def ensure_cart_tables(apps, schema_editor):
    """Ensure Cart and CartItem tables exist with correct structure."""
    cursor = schema_editor.connection.cursor()

    if not table_exists(cursor, 'base_cart'):
        Cart = apps.get_model('base', 'Cart')
        schema_editor.create_model(Cart)

    if not table_exists(cursor, 'base_cartitem'):
        CartItem = apps.get_model('base', 'CartItem')
        schema_editor.create_model(CartItem)
        return

    columns = get_columns(cursor, 'base_cartitem')
    required_columns = {
        '_id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'qty': 'INTEGER NOT NULL DEFAULT 1',
        'addedAt': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
        'updatedAt': 'DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
    }

    for col, definition in required_columns.items():
        if col not in columns:
            try:
                schema_editor.execute(f'ALTER TABLE base_cartitem ADD COLUMN "{col}" {definition}')
            except Exception:
                pass

    cursor.execute("PRAGMA index_list(base_cartitem)")
    indexes = [idx[1] for idx in cursor.fetchall()]
    has_unique = any('cart' in idx.lower() and 'product' in idx.lower() for idx in indexes)

    if not has_unique:
        try:
            schema_editor.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS "base_cartitem_cart_id_product_id_uniq" ON "base_cartitem" ("cart_id", "product_id")'
            )
        except Exception:
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0009_cart_cartitem'),
    ]

    operations = [
        migrations.RunPython(ensure_coupon_table, noop),
        migrations.RunPython(ensure_order_discount_fields, noop),
        migrations.RunPython(ensure_cart_tables, noop),
    ]
