from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import UserAccount
from .utils import normalize_email


@receiver(pre_save, sender=UserAccount)
def normalize_user_email_on_create(sender, instance, **kwargs):
    if instance._state.adding and instance.email:
        instance.email = normalize_email(instance.email)
