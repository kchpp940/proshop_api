from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction

from base.models import Product, SubCategory, Category


class ProductAdminService:
    @staticmethod
    def validate_admin_permission(user):
        if not user.is_authenticated or not user.is_staff:
            raise PermissionError("Admin permission required")

    @staticmethod
    def parse_category(category_slug):
        if not category_slug:
            return None

        try:
            return SubCategory.objects.get(slug=category_slug)
        except SubCategory.DoesNotExist:
            try:
                category = Category.objects.get(slug=category_slug)
                sub_categories = SubCategory.objects.filter(category=category)
                if sub_categories.exists():
                    return sub_categories.first()
            except Category.DoesNotExist:
                pass
            raise ValidationError(f"Category with slug '{category_slug}' does not exist")

    @staticmethod
    def validate_price(price):
        if price is None:
            raise ValidationError("Price is required")
        try:
            price_value = float(price)
            if price_value < 0:
                raise ValidationError("Price cannot be negative")
            return price_value
        except (TypeError, ValueError):
            raise ValidationError("Price must be a valid number")

    @staticmethod
    def validate_stock(count_in_stock):
        if count_in_stock is None:
            return 0
        try:
            stock_value = int(count_in_stock)
            if stock_value < 0:
                raise ValidationError("Stock count cannot be negative")
            return stock_value
        except (TypeError, ValueError):
            raise ValidationError("Stock count must be a valid integer")

    @staticmethod
    def process_image(product, image_file=None):
        if image_file:
            product.image = image_file

    @staticmethod
    def validate_product_data(data, is_update=False):
        errors = {}

        if not is_update or 'name' in data:
            if not data.get('name'):
                errors['name'] = "Product name is required"

        if 'price' in data:
            try:
                ProductAdminService.validate_price(data.get('price'))
            except ValidationError as e:
                errors['price'] = str(e.message)

        if 'countInStock' in data:
            try:
                ProductAdminService.validate_stock(data.get('countInStock'))
            except ValidationError as e:
                errors['countInStock'] = str(e.message)

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _apply_product_data(product, data, is_update=False):
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'brand' in data:
            product.brand = data['brand']
        if 'price' in data:
            product.price = ProductAdminService.validate_price(data['price'])
        if 'countInStock' in data:
            product.countInStock = ProductAdminService.validate_stock(data['countInStock'])
        if 'category' in data:
            product.category = ProductAdminService.parse_category(data['category'])

        ProductAdminService.process_image(product, data.get('image'))

    @staticmethod
    @transaction.atomic
    def create_product(user, data=None):
        ProductAdminService.validate_admin_permission(user)

        if data is None:
            data = {}

        ProductAdminService.validate_product_data(data, is_update=False)

        product = Product.objects.create(
            user=user,
            name=data.get('name', 'Sample Name'),
            description=data.get('description', ''),
            price=data.get('price', 0),
            brand=data.get('brand', 'Sample Brand'),
            countInStock=data.get('countInStock', 0),
        )

        ProductAdminService._apply_product_data(product, data, is_update=False)
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def update_product(product_id, data, user=None):
        if user is not None:
            ProductAdminService.validate_admin_permission(user)

        try:
            product = Product.objects.get(_id=product_id)
        except Product.DoesNotExist:
            raise ObjectDoesNotExist(f"Product with id {product_id} does not exist")

        ProductAdminService.validate_product_data(data, is_update=True)
        ProductAdminService._apply_product_data(product, data, is_update=True)
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def save_product(data, user=None, product=None):
        if product is None:
            return ProductAdminService.create_product(user, data)
        else:
            ProductAdminService.validate_product_data(data, is_update=True)
            ProductAdminService._apply_product_data(product, data, is_update=True)
            product.save()
            return product

    @staticmethod
    @transaction.atomic
    def upload_product_image(product_id, image_file, user=None):
        if user is not None:
            ProductAdminService.validate_admin_permission(user)

        try:
            product = Product.objects.get(_id=product_id)
        except Product.DoesNotExist:
            raise ObjectDoesNotExist(f"Product with id {product_id} does not exist")

        ProductAdminService.process_image(product, image_file)
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def delete_product(product_id, user):
        ProductAdminService.validate_admin_permission(user)

        try:
            product = Product.objects.get(_id=product_id)
        except Product.DoesNotExist:
            raise ObjectDoesNotExist(f"Product with id {product_id} does not exist")

        product.delete()
        return True

    @staticmethod
    def get_product_by_id(product_id):
        try:
            return Product.objects.get(_id=product_id)
        except Product.DoesNotExist:
            raise ObjectDoesNotExist(f"Product with id {product_id} does not exist")
