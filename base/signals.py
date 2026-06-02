from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from base.models import Address, Review, Product
from base.services import ProductReviewService

User = get_user_model()


def updateDefaultAddress(sender, instance, **kwargs):
    address = instance
    user = address.user

    if address.is_default:
        querySet = Address.objects.filter(
            user=user, is_default=True).exclude(_id=address._id)
        if querySet.exists():
            for addr in querySet:
                addr.is_default = False
                addr.save()


pre_save.connect(updateDefaultAddress, sender=Address)


@receiver(post_save, sender=Review)
def recalculate_rating_on_review_save(sender, instance, **kwargs):
    ProductReviewService.recalculate_product_rating(instance.product)


@receiver(post_delete, sender=Review)
def recalculate_rating_on_review_delete(sender, instance, **kwargs):
    ProductReviewService.recalculate_product_rating(instance.product)


@receiver(pre_delete, sender=User)
def capture_affected_products_on_user_delete(sender, instance, **kwargs):
    product_ids = list(
        Review.objects.filter(
            user_id=instance.id
        ).values_list('product_id', flat=True).distinct()
    )
    instance._review_affected_product_ids = product_ids


@receiver(post_delete, sender=User)
def recalculate_ratings_on_user_delete(sender, instance, **kwargs):
    product_ids = getattr(instance, '_review_affected_product_ids', [])
    for product_id in product_ids:
        try:
            product = Product.objects.get(_id=product_id)
            ProductReviewService.recalculate_product_rating(product)
        except Product.DoesNotExist:
            continue
