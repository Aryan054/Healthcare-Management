from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings
import uuid
import os


# ==========================
# Custom User Model (Extended from AbstractUser)
# ==========================
class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    is_verified = models.BooleanField(default=False)
    
    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, 'Patient')


# ==========================
# Profile Model (Separate from User for extensibility)
# ==========================
def profile_picture_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profiles', str(instance.user.id), filename)

class Profile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    bio = models.TextField(blank=True, null=True, max_length=500)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']

    
    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None


# ==========================
# Specializations
# ==========================
class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # For icon class or image reference
    created_at = models.DateTimeField(auto_now_add=True)  # auto timestamp
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Specialization"
        verbose_name_plural = "Specializations"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==========================
# Doctor details
# ==========================
class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'doctor'})
    specializations = models.ManyToManyField(Specialization, related_name='doctors')
    experience_years = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(60)]
    )
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    license_number = models.CharField(max_length=50, unique=True)
    clinic_address = models.TextField()
    available_days = models.CharField(max_length=50)  # e.g., "Mon,Tue,Wed,Fri"
    available_from = models.TimeField()
    available_to = models.TimeField()
    is_active = models.BooleanField(default=False) # Changed to False for manual verification
    education = models.TextField(default='', blank=True)
    languages = models.CharField(max_length=200, default="English")  # Comma-separated languages
    awards = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

    def clean(self):
        if self.available_from >= self.available_to:
            raise ValidationError("Available 'from' time must be before 'to' time.")

    @property
    def average_rating(self):
        from django.db.models import Avg
        return self.appointments.filter(review__isnull=False).aggregate(Avg('review__rating'))['review__rating__avg']


# ==========================
# Patient details
# ==========================
class Patient(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'patient'})
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Height in cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Weight in kg")
    allergies = models.TextField(blank=True, null=True)
    chronic_conditions = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def bmi(self):
        if self.height and self.weight:
            return round(self.weight / ((self.height/100) ** 2), 2)
        return None


# ==========================
# Appointment
# ==========================
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_number = models.CharField(max_length=20, unique=True, blank=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    meeting_link = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_reminder_sent = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        unique_together = ('doctor', 'appointment_date', 'appointment_time')
        ordering = ['-appointment_date', '-appointment_time']

    def __str__(self):
        return f"Appointment #{self.appointment_number} - {self.patient.user.username} with Dr. {self.doctor.user.username}"

    def save(self, *args, **kwargs):
        if not self.appointment_number:
            self.appointment_number = f"APT-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.end_time:
            from datetime import timedelta, datetime
            dummy_datetime = datetime.combine(self.appointment_date, self.appointment_time)
            self.end_time = (dummy_datetime + timedelta(minutes=30)).time()
        super().save(*args, **kwargs)

    def clean(self):
        if not self.appointment_date or not self.appointment_time:
            # Let the form's validation handle the "field is required" error.
            return
        
        if self.appointment_date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past.")
        
        if self.appointment_date == timezone.now().date() and self.appointment_time < timezone.now().time():
            raise ValidationError("Appointment time cannot be in the past for today's date.")


# ==========================
# Medical Record
# ==========================
def medical_record_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('medical_records', str(instance.patient.user.id), filename)

class MedicalRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('diagnosis', 'Diagnosis'),
        ('prescription', 'Prescription'),
        ('lab_report', 'Lab Report'),
        ('imaging', 'Imaging Report'),
        ('procedure', 'Procedure Note'),
        ('progress', 'Progress Note'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPE_CHOICES, default='diagnosis')
    title = models.CharField(max_length=200)
    diagnosis = models.TextField(blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    document = models.FileField(
        upload_to=medical_record_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])]
    )
    is_shared = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medical Record"
        verbose_name_plural = "Medical Records"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_record_type_display()} for {self.patient.user.get_full_name()}"


# ==========================
# Review and Rating
# ==========================
class Review(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (worst) to 5 (best)"
    )
    comment = models.TextField(blank=True, null=True)
    doctor_response = models.TextField(blank=True, null=True)
    is_anonymous = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for Appointment #{self.appointment.appointment_number} - {self.rating} Stars"


# ==========================
# Soft Delete Mixin
# ==========================
class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self):
        super().delete()


# ==========================
# Notification System
# ==========================
class Notification(SoftDeleteMixin):
    NOTIFICATION_TYPES = [
        ('appointment', 'Appointment'),
        ('prescription', 'Prescription'),
        ('payment', 'Payment'),
        ('system', 'System'),
        ('other', 'Other'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    related_content_type = models.CharField(max_length=100, blank=True, null=True)
    action_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} Notification for {self.recipient.username}"


# ==========================
# Prescription Model (Extended from MedicalRecord)
# ==========================
class Prescription(models.Model):
    medical_record = models.OneToOneField(MedicalRecord, on_delete=models.CASCADE, related_name='prescription_detail')
    medicines = models.JSONField()  # Store list of medicines with details
    instructions = models.TextField()
    refill_info = models.CharField(max_length=100, blank=True, null=True)
    valid_until = models.DateField(blank=True, null=True)
    is_digital = models.BooleanField(default=True)
    digital_signature = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"

    def __str__(self):
        return f"Prescription #{self.medical_record.id} for {self.medical_record.patient.user.get_full_name()}"


# ==========================
# Availability and Schedule
# ==========================
class DoctorAvailability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    recurring = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor Availability"
        verbose_name_plural = "Doctor Availabilities"
        unique_together = ('doctor', 'day_of_week', 'start_time', 'end_time')
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


# ==========================
# Payment Model
# ==========================
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('net_banking', 'Net Banking'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    payment_date = models.DateTimeField(blank=True, null=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_gateway_response = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment #{self.invoice_number} - {self.amount} {self.get_payment_status_display()}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.transaction_id and self.payment_status == 'completed':
            self.transaction_id = f"TXN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)