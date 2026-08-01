# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CovalentUser, Wallet, NotificationPreferences

@receiver(post_save, sender=CovalentUser)
def create_user_dependencies(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
        NotificationPreferences.objects.create(user=instance)