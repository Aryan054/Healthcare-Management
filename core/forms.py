from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.forms import ModelForm, Form
from .models import (
    User, Profile, Specialization, Doctor, Patient,
    Appointment, MedicalRecord, Review, Prescription,
    DoctorAvailability, Payment, Notification
)
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.core.validators import RegexValidator
from datetime import datetime, time  


# ==========================
# Authentication Forms
# ==========================
class CustomUserCreationForm(UserCreationForm):
    # We define the fields explicitly here
    email = forms.EmailField(required=True, help_text='A valid email address is required.')
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This loop adds the 'form-control' class to all fields for Bootstrap styling
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.RadioSelect): # Don't style radio buttons this way
                field.widget.attrs['class'] = 'form-control'


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')


# ==========================
# Profile Forms
# ==========================
class ProfileForm(ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    class Meta:
        model = Profile
        fields = ['profile_picture', 'bio', 'date_of_birth', 'gender', 'address']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class DoctorProfileForm(ModelForm):
    available_days = forms.MultipleChoiceField(
        choices=DoctorAvailability.DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = Doctor
        fields = [
            'specializations', 'experience_years', 'consultation_fee',
            'license_number', 'clinic_address', 'available_days',
            'available_from', 'available_to', 'education', 'languages', 'awards'
        ]
        widgets = {
            'available_from': forms.TimeInput(attrs={'type': 'time'}),
            'available_to': forms.TimeInput(attrs={'type': 'time'}),
            'clinic_address': forms.Textarea(attrs={'rows': 3}),
            'education': forms.Textarea(attrs={'rows': 3}),
            'awards': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        available_from = cleaned_data.get('available_from')
        available_to = cleaned_data.get('available_to')
        
        if available_from and available_to and available_from >= available_to:
            raise ValidationError("Available 'from' time must be before 'to' time.")
        
        return cleaned_data


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ["specializations", "experience_years", "consultation_fee","license_number","clinic_address","available_days","available_from","available_to"]


class PatientProfileForm(ModelForm):
    class Meta:
        model = Patient
        fields = [
            'blood_group', 'height', 'weight',
            'allergies', 'chronic_conditions',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation'
        ]
        widgets = {
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'chronic_conditions': forms.Textarea(attrs={'rows': 2}),
        }


# ==========================
# Appointment Forms
# ==========================


class AppointmentForm(ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now().date()
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    class Meta:
        model = Appointment
        fields = ['doctor', 'appointment_date', 'appointment_time', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'doctor': forms.HiddenInput(),  # doctor will be passed from the view
        }

    def clean(self):
        cleaned_data = super().clean()
        appointment_date = cleaned_data.get('appointment_date')
        appointment_time = cleaned_data.get('appointment_time')

        # Basic validation: check if appointment is not in the past
        if appointment_date and appointment_date < timezone.now().date():
            self.add_error('appointment_date', "Appointment date cannot be in the past.")

        if appointment_date == timezone.now().date() and appointment_time:
            if appointment_time < timezone.now().time():
                self.add_error('appointment_time', "Appointment time cannot be in the past for today's date.")

        return cleaned_data

class AppointmentRescheduleForm(forms.Form):
    new_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    new_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    def __init__(self, *args, **kwargs):
        self.appointment = kwargs.pop('appointment', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        new_date = cleaned_data.get('new_date')
        new_time = cleaned_data.get('new_time')
        
        if new_date and new_time and self.appointment:
            if new_date < timezone.now().date():
                raise ValidationError("New appointment date cannot be in the past.")
            
            if new_date == timezone.now().date() and new_time < timezone.now().time():
                raise ValidationError("New appointment time cannot be in the past for today's date.")
            
            day_of_week = new_date.weekday()
            if not DoctorAvailability.objects.filter(
                doctor=self.appointment.doctor,
                day_of_week=day_of_week,
                start_time__lte=new_time,
                end_time__gte=new_time,
                is_available=True
            ).exists():
                raise ValidationError("Doctor is not available at the selected time.")
            
            if Appointment.objects.filter(
                doctor=self.appointment.doctor,
                appointment_date=new_date,
                appointment_time=new_time,
                status__in=['pending', 'confirmed']
            ).exclude(id=self.appointment.id).exists():
                raise ValidationError("This time slot is already booked.")
        
        return cleaned_data

class AdminAddDoctorForm(forms.Form):
    # User fields
    username = forms.CharField(max_length=150, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.")
    email = forms.EmailField(help_text="A valid email address.")
    password = forms.CharField(widget=forms.PasswordInput, help_text="Set an initial password for the doctor.")
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    # Doctor profile fields
    specialization = forms.ModelChoiceField(queryset=Specialization.objects.all(), required=True)
    license_number = forms.CharField(max_length=50)
    experience_years = forms.IntegerField(min_value=0)
    consultation_fee = forms.DecimalField(min_value=0, decimal_places=2)
    clinic_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

# ==========================
# Medical Record Forms
# ==========================
class MedicalRecordForm(ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            'record_type', 'title', 'symptoms', 'diagnosis',
            'prescription', 'treatment', 'notes', 'document', 'is_shared'
        ]
        widgets = {
            'symptoms': forms.Textarea(attrs={'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'prescription': forms.Textarea(attrs={'rows': 3}),
            'treatment': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop('patient', None)
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # These fields are not directly in the form but might be needed if they were
        # if self.patient:
        #     self.fields['patient'].initial = self.patient
        # if self.doctor:
        #     self.fields['doctor'].initial = self.doctor


class PrescriptionForm(ModelForm):
    class Meta:
        model = Prescription
        fields = ['medicines', 'instructions', 'refill_info', 'valid_until']
        widgets = {
            'medicines': forms.Textarea(attrs={'rows': 5, 'placeholder': 'JSON format: [{"name": "Medicine", "dose": "500mg", ...}]'}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean_medicines(self):
        medicines = self.cleaned_data.get('medicines')
        # Add validation for JSON format if needed
        return medicines


# ==========================
# Review Forms
# ==========================
class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment', 'is_anonymous']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


# ==========================
# Availability Forms
# ==========================
class DoctorAvailabilityForm(ModelForm):
    class Meta:
        model = DoctorAvailability
        fields = ['day_of_week', 'start_time', 'end_time', 'is_available', 'recurring', 'valid_from', 'valid_to']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'valid_from': forms.DateInput(attrs={'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Start time must be before end time.")
        
        return cleaned_data


# ==========================
# Payment Forms
# ==========================
class OnlinePaymentForm(forms.Form):
    # These fields are for simulation purposes only.
    # In a real application, you would use Stripe.js or a similar library.
    card_number = forms.CharField(
        label="Card Number",
        max_length=16,
        widget=forms.TextInput(attrs={'placeholder': '0000 0000 0000 0000'})
    )
    expiry_month = forms.CharField(
        label="Expiry Month",
        max_length=2,
        widget=forms.TextInput(attrs={'placeholder': 'MM'})
    )
    expiry_year = forms.CharField(
        label="Expiry Year",
        max_length=4,
        widget=forms.TextInput(attrs={'placeholder': 'YYYY'})
    )
    cvv = forms.CharField(
        label="CVV",
        max_length=3,
        widget=forms.PasswordInput(attrs={'placeholder': '123'})
    )


# ==========================
# Notification Forms
# ==========================
class NotificationForm(ModelForm):
    class Meta:
        model = Notification
        fields = ['recipient', 'notification_type', 'title', 'message', 'action_url']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }


# ==========================
# Search Forms
# ==========================
class DoctorSearchForm(Form):
    specialization = forms.ModelChoiceField(queryset=Specialization.objects.all(), required=False)
    name = forms.CharField(required=False)
    available_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    min_experience = forms.IntegerField(min_value=0, max_value=60, required=False)
    max_fee = forms.DecimalField(min_value=0, decimal_places=2, required=False)


class PatientSearchForm(Form):
    name = forms.CharField(required=False)
    blood_group = forms.ChoiceField(choices=Patient.BLOOD_GROUP_CHOICES, required=False)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)


# ==========================
# Time Slot Selection Form
# ==========================
class TimeSlotSelectionForm(Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.filter(is_active=True))
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        doctor = cleaned_data.get('doctor')
        
        if date and doctor:
            if date < timezone.now().date():
                raise ValidationError("Date cannot be in the past.")
            
            day_of_week = date.weekday()
            if not DoctorAvailability.objects.filter(
                doctor=doctor, day_of_week=day_of_week, is_available=True
            ).exists():
                raise ValidationError("Doctor is not available on this day.")
        
        return cleaned_data


# ==========================
# Report Generation Form
# ==========================
class ReportGenerationForm(Form):
    REPORT_TYPE_CHOICES = [
        ('appointments', 'Appointments Report'),
        ('payments', 'Payments Report'),
    ]
    
    DATE_RANGE_CHOICES = [
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_year', 'This Year'),
        ('custom', 'Custom Date Range'),
    ]
    
    report_type = forms.ChoiceField(choices=REPORT_TYPE_CHOICES)
    date_range = forms.ChoiceField(choices=DATE_RANGE_CHOICES)
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if date_range == 'custom':
            if not start_date or not end_date:
                raise ValidationError("Both start and end dates are required for custom date range.")
            if start_date > end_date:
                raise ValidationError("Start date cannot be after end date.")
        
        return cleaned_data