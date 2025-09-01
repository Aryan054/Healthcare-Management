from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from .models import Profile, User
from django.db.models.signals import post_save
from django.urls import reverse
from .models import Appointment, Payment, Notification

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


# In core/signals.py



# This function will run EVERY time a new Appointment is created and saved.
@receiver(post_save, sender=Appointment)
def create_appointment_notification(sender, instance, created, **kwargs):
    """
    Create a notification for the doctor when a new appointment is booked by a patient.
    """
    # The 'created' flag is True only when a brand new record is made.
    if created:
        doctor_user = instance.doctor.user
        patient_user = instance.patient.user
        
        # We create a new notification object in the database
        Notification.objects.create(
            recipient=doctor_user,
            notification_type='appointment',
            title='New Appointment Booking',
            message=f"Patient {patient_user.get_full_name()} has booked a new appointment with you on {instance.appointment_date} at {instance.appointment_time.strftime('%I:%M %p')}.",
            action_url=reverse('appointment_detail', kwargs={'pk': instance.pk})
        )

# This function will run EVERY time a Payment object is saved.
@receiver(post_save, sender=Payment)
def create_payment_notification(sender, instance, created, **kwargs):
    """
    Create a notification for the doctor when a payment's status is updated to 'completed'.
    """
    # We only care when the payment is successfully completed.
    if instance.payment_status == 'completed':
        doctor_user = instance.appointment.doctor.user
        patient_user = instance.patient.user

        # Use update_or_create to prevent sending duplicate notifications if the object is saved again.
        # It finds a notification for this appointment of type 'payment' and either updates it or creates it.
        Notification.objects.update_or_create(
            recipient=doctor_user,
            notification_type='payment',
            related_object_id=instance.appointment.pk, # A way to uniquely identify this notification
            defaults={
                'title': 'Payment Received',
                'message': f"Payment of ${instance.amount} was successfully processed for your appointment with {patient_user.get_full_name()}.",
                'action_url': reverse('appointment_detail', kwargs={'pk': instance.appointment.pk})
            }
        )