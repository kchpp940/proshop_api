from django.contrib.auth import get_user_model
from django.db import transaction

from base.models import Address

User = get_user_model()

_ADDRESS_FIELDS = (
    "first_name",
    "last_name",
    "address",
    "city",
    "postal_code",
    "country",
    "phone_number",
)


class AddressService:
    @staticmethod
    @transaction.atomic
    def create_address(user, data):
        User.objects.select_for_update().get(pk=user.pk)
        if data.get("is_default", False):
            Address.objects.filter(user=user, is_default=True).update(
                is_default=False
            )
        address = Address.objects.create(
            user=user,
            **{field: data[field] for field in _ADDRESS_FIELDS},
            is_default=data.get("is_default", False),
        )
        return address

    @staticmethod
    @transaction.atomic
    def update_address(user, pk, data):
        User.objects.select_for_update().get(pk=user.pk)
        address = Address.objects.get(_id=pk, user=user)
        for field in _ADDRESS_FIELDS:
            setattr(address, field, data[field])
        address.is_default = data.get("is_default", False)
        if address.is_default:
            Address.objects.filter(user=user, is_default=True).update(
                is_default=False
            )
        address.save()
        return address

    @staticmethod
    @transaction.atomic
    def set_default_address(user, pk):
        User.objects.select_for_update().get(pk=user.pk)
        address = Address.objects.get(_id=pk, user=user)
        Address.objects.filter(user=user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])
        return address

    @staticmethod
    def delete_address(user, pk):
        address = Address.objects.get(_id=pk, user=user)
        address_id = address._id
        address.delete()
        return address_id

    @staticmethod
    def get_address(user, pk):
        return Address.objects.get(_id=pk, user=user)

    @staticmethod
    def list_addresses(user):
        return user.address_set.all()
