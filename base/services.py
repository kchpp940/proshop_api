from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from base.models import Product, Order, OrderItem, Address, ShippingAddress


class OrderServiceError(Exception):
    """订单服务基础异常类"""
    status_code = 400

    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ProductNotFoundError(OrderServiceError):
    """商品不存在异常"""
    status_code = 400


class InsufficientStockError(OrderServiceError):
    """库存不足异常"""
    status_code = 400


class AddressNotFoundError(OrderServiceError):
    """地址不存在异常"""
    status_code = 400


class AddressPermissionError(OrderServiceError):
    """地址越权异常"""
    status_code = 403


class EmptyOrderItemsError(OrderServiceError):
    """订单项为空异常"""
    status_code = 400


class InvalidOrderItemDataError(OrderServiceError):
    """订单项数据非法异常"""
    status_code = 400


class InvalidOrderInputError(OrderServiceError):
    """订单输入数据非法异常"""
    status_code = 400


class OrderService:
    """订单创建服务"""

    DECIMAL_PLACES = 2
    MAX_DIGITS = 7

    @classmethod
    def create_order(cls, user, order_data):
        """
        创建订单（原子事务）
        
        Args:
            user: 当前用户对象
            order_data: 请求数据字典（只信任 productId/quantity/paymentMethod/address_id/shippingPrice/taxPrice）
            
        Returns:
            Order: 创建成功的订单对象
            
        Raises:
            OrderServiceError: 订单创建失败时抛出
        """
        order_items_data = order_data.get('orderItems', [])

        if not order_items_data:
            raise EmptyOrderItemsError('No order items')

        cls._validate_order_input(order_data)

        product_ids, quantity_map = cls._parse_order_items(order_items_data)

        return cls._create_order_in_transaction(
            user=user,
            order_data=order_data,
            product_ids=product_ids,
            quantity_map=quantity_map,
        )

    @classmethod
    def _validate_order_input(cls, order_data):
        """校验订单必填字段"""
        payment_method = order_data.get('paymentMethod')
        if not payment_method:
            raise InvalidOrderInputError('paymentMethod is required')

        address_id = order_data.get('address_id')
        if not address_id:
            raise InvalidOrderInputError('address_id is required')

        cls._validate_decimal_field(order_data, 'shippingPrice')
        cls._validate_decimal_field(order_data, 'taxPrice')

    @classmethod
    def _validate_decimal_field(cls, order_data, field_name):
        """校验金额字段格式"""
        value = order_data.get(field_name)
        if value is None:
            raise InvalidOrderInputError(f'{field_name} is required')

        try:
            decimal_value = Decimal(str(value))
        except (TypeError, ValueError):
            raise InvalidOrderInputError(f'{field_name} must be a valid number')

        if decimal_value < 0:
            raise InvalidOrderInputError(f'{field_name} cannot be negative')

        if len(decimal_value.as_tuple().digits) > cls.MAX_DIGITS:
            raise InvalidOrderInputError(f'{field_name} exceeds maximum digits')

    @classmethod
    def _parse_order_items(cls, order_items_data):
        """
        解析订单项数据
        
        校验字段完整性、数量合法性，重复商品按总数量合并
        
        Returns:
            tuple: (product_ids, quantity_map)
        """
        quantity_map = {}

        for idx, item in enumerate(order_items_data):
            if 'productId' not in item or item['productId'] is None:
                raise InvalidOrderItemDataError(
                    f'Order item {idx}: productId is required'
                )

            product_id = str(item['productId'])

            if 'quantity' not in item:
                raise InvalidOrderItemDataError(
                    f'Order item {idx} (product {product_id}): quantity is required'
                )

            try:
                quantity = int(item['quantity'])
            except (TypeError, ValueError):
                raise InvalidOrderItemDataError(
                    f'Order item {idx} (product {product_id}): quantity must be an integer'
                )

            if quantity <= 0:
                raise InvalidOrderItemDataError(
                    f'Order item {idx} (product {product_id}): quantity must be greater than 0'
                )

            quantity_map[product_id] = quantity_map.get(product_id, 0) + quantity

        product_ids = list(quantity_map.keys())

        return product_ids, quantity_map

    @classmethod
    def _round_decimal(cls, value):
        """按模型字段精度四舍五入（max_digits=7, decimal_places=2）"""
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def _calculate_order_amounts(cls, products, quantity_map, order_data):
        """
        计算订单金额（按项目原有口径：shipping/tax 来自请求，服务端校验并重算总价）
        
        Args:
            products: 锁定后的商品列表
            quantity_map: 商品ID到数量的映射
            order_data: 请求数据字典
            
        Returns:
            dict: {items_total, shipping_price, tax_price, total_price}
        """
        items_total = Decimal('0')
        for product in products:
            qty = quantity_map[str(product._id)]
            items_total += product.price * qty

        items_total = cls._round_decimal(items_total)
        shipping_price = cls._round_decimal(Decimal(str(order_data['shippingPrice'])))
        tax_price = cls._round_decimal(Decimal(str(order_data['taxPrice'])))
        total_price = cls._round_decimal(items_total + shipping_price + tax_price)

        return {
            'items_total': items_total,
            'shipping_price': shipping_price,
            'tax_price': tax_price,
            'total_price': total_price,
        }

    @classmethod
    @transaction.atomic
    def _create_order_in_transaction(cls, user, order_data, product_ids, quantity_map):
        """在事务内执行订单创建"""
        address = cls._validate_address(user, order_data['address_id'])

        products = cls._lock_and_validate_products(product_ids, quantity_map)

        amounts = cls._calculate_order_amounts(products, quantity_map, order_data)

        order = cls._create_order_record(user, order_data, amounts)

        cls._create_shipping_address(order, address)

        cls._create_order_items_and_deduct_stock(
            order, products, quantity_map
        )

        return order

    @classmethod
    def _validate_address(cls, user, address_id):
        """验证地址存在性及归属"""
        if not address_id:
            raise AddressNotFoundError('Address ID is required')

        try:
            address = Address.objects.get(_id=address_id)
        except ObjectDoesNotExist:
            raise AddressNotFoundError(f'Address {address_id} does not exist')

        if address.user_id != user.id:
            raise AddressPermissionError(
                f'Address {address_id} does not belong to current user'
            )

        return address

    @classmethod
    def _lock_and_validate_products(cls, product_ids, quantity_map):
        """锁定商品并验证存在性和库存"""
        products = list(
            Product.objects.select_for_update().filter(_id__in=product_ids)
        )

        existing_ids = {str(p._id) for p in products}
        requested_ids = {str(pid) for pid in product_ids}
        missing_ids = requested_ids - existing_ids

        if missing_ids:
            raise ProductNotFoundError(
                f'Products not found: {", ".join(sorted(missing_ids))}'
            )

        for product in products:
            qty = quantity_map[str(product._id)]
            if product.countInStock < qty:
                raise InsufficientStockError(
                    f'Insufficient stock for product {product.name} (ID: {product._id}). '
                    f'Available: {product.countInStock}, requested: {qty}'
                )

        return products

    @classmethod
    def _create_order_record(cls, user, order_data, amounts):
        """创建订单主记录（金额基于服务端计算）"""
        return Order.objects.create(
            user=user,
            paymentMethod=order_data['paymentMethod'],
            taxPrice=amounts['tax_price'],
            shippingPrice=amounts['shipping_price'],
            totalPrice=amounts['total_price'],
        )

    @classmethod
    def _create_shipping_address(cls, order, address):
        """创建订单配送地址关联"""
        ShippingAddress.objects.create(order=order, address=address)

    @classmethod
    def _create_order_items_and_deduct_stock(cls, order, products, quantity_map):
        """创建订单项并扣减库存（价格基于数据库商品数据）"""
        for product in products:
            product_id = str(product._id)
            qty = quantity_map[product_id]

            OrderItem.objects.create(
                order=order,
                product=product,
                name=product.name,
                qty=qty,
                price=product.price,
                image=product.image.url
            )

            product.countInStock -= qty
            product.save()
