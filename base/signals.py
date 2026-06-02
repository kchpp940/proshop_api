from django.db.models.signals import pre_save
from base.models import Address


def updateDefaultAddress(sender, instance, **kwargs):
    address = instance
    user = address.user

    # If the address is default, then set all other addresses of the user to not default
    if address.is_default:
        querySet = Address.objects.filter(
            user=user, is_default=True).exclude(_id=address._id)
        if querySet.exists():
            for addr in querySet:
                addr.is_default = False
                addr.save()


pre_save.connect(updateDefaultAddress, sender=Address)
