from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from .models import Profile, User

# This signal now correctly listens to the custom User model specified in settings
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile when a User object is saved.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        # Ensure profile exists and save it (in case it was created manually)
        if hasattr(instance, 'profile'):
            instance.profile.save()