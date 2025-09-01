from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponse
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.urls import reverse_lazy
from django.db.models import Q, Avg, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta, datetime, time 
import json
import logging
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

User = get_user_model()

# Import models and forms
from .models import (
    Profile, Specialization, Doctor, Patient,
    Appointment, MedicalRecord, Review, Prescription,
    DoctorAvailability, Payment, Notification
)
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm,
    ProfileForm, DoctorProfileForm, PatientProfileForm,
    AppointmentForm, AppointmentRescheduleForm,
    MedicalRecordForm, PrescriptionForm, ReviewForm,
    DoctorAvailabilityForm, NotificationForm,
    DoctorSearchForm, PatientSearchForm,
    TimeSlotSelectionForm, ReportGenerationForm, DoctorForm,AdminAddDoctorForm,PasswordChangeForm,OnlinePaymentForm,ReviewForm
)

logger = logging.getLogger(__name__)

# ==========================
# Utility Functions
# ==========================
def get_or_create_patient(user):
    if not hasattr(user, 'role') or user.role != 'patient':
        return None
    patient, _ = Patient.objects.get_or_create(user=user)
    return patient

def get_or_create_doctor(user):
    if not hasattr(user, 'role') or user.role != 'doctor':
        return None
    doctor, _ = Doctor.objects.get_or_create(user=user, defaults={
        'experience_years': 0,
        'consultation_fee': 0.00,
        'license_number': 'temp-license-{}'.format(user.id),
        'clinic_address': 'temp address',
        'available_days': '',
        'available_from': '09:00',
        'available_to': '17:00'
    })
    return doctor

def is_patient(user): return user.is_authenticated and user.role == 'patient'
def is_doctor(user): return user.is_authenticated and user.role == 'doctor'
def is_admin(user): return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

# ==========================
# Home View
# ==========================
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "home.html")

# ==========================
# Authentication Views
# ==========================
def register(request):
    if request.user.is_authenticated: return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.role == "patient": get_or_create_patient(user)
            elif user.role == "doctor": get_or_create_doctor(user)
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated: return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == role:
            login(request, user)
            return redirect('dashboard')
        else: 
            messages.error(request, 'Invalid username, password, or role.')
    return render(request, 'login.html')


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


@user_passes_test(is_admin)
def user_list(request):
    queryset = User.objects.all().order_by("-date_joined")
    search_query = request.GET.get('q', '')

    if search_query:
        # If a search term was provided, filter the queryset
        queryset = queryset.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        ).distinct()
    # ==========================================================

    # Paginate the final, filtered results
    paginator = Paginator(queryset, 15) # Show 15 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, "user_list.html", context)



# ==========================
# Dashboard Views
# ==========================
@login_required
def dashboard(request):
    role = getattr(request.user, 'role', None)
    if is_admin(request.user):
        return redirect('admin_dashboard')
    elif role == 'doctor':
        return redirect('doctor_dashboard')
    elif role == 'patient':
        return redirect('patient_dashboard')
    # Fallback for users with no role
    logout(request)
    messages.error(request, 'Your user role is not configured. Please contact support.')
    return redirect('login')

@login_required
@user_passes_test(is_patient)
def patient_dashboard(request):
    patient = get_or_create_patient(request.user)
    if not patient:
        messages.error(request, "Could not find or create patient profile.")
        return redirect('home')

    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=timezone.now().date(),
        status__in=['confirmed', 'pending', 'rescheduled']
    ).order_by('appointment_date', 'appointment_time')[:5]

    context = {
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'medical_records': MedicalRecord.objects.filter(patient=patient).order_by('-created_at')[:5],
        'pending_appointments_count': Appointment.objects.filter(patient=patient, status='pending').count(),
        'recent_notifications': Notification.objects.filter(recipient=request.user, is_deleted=False).order_by('-created_at')[:5],
        'unread_notifications_count': Notification.objects.filter(recipient=request.user, is_read=False, is_deleted=False).count(),
    }
    return render(request, 'patient_dashboard.html', context)

@login_required
@user_passes_test(is_doctor)
def doctor_dashboard(request):
    doctor = get_or_create_doctor(request.user)
    today = timezone.now().date()
    
    today_appointments = Appointment.objects.filter(
        doctor=doctor, 
        appointment_date=today,
        status__in=['pending', 'confirmed', 'rescheduled']
    ).order_by('appointment_time')
    
    patient_count = Patient.objects.filter(appointments__doctor=doctor).distinct().count()
    
    # This line fetches the count of unread notifications for the doctor
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False, is_deleted=False).count()
    
    context = {
        'doctor': doctor, 
        'today_appointments': today_appointments, 
        'patient_count': patient_count,
        'unread_notifications_count': unread_notifications_count, # Pass the count to the template
    }
    return render(request, 'doctor_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    context = {
        'total_patients': User.objects.filter(role='patient').count(),
        'total_doctors': User.objects.filter(role='doctor').count(),
        'total_appointments': Appointment.objects.count(),
        'completed_appointments': Appointment.objects.filter(status='completed').count(),
    }
    return render(request, 'admin_dashboard.html', context)

# ==========================
# Profile Views
# ==========================
@login_required
def profile_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    user_form = CustomUserChangeForm(instance=user)
    profile_form = ProfileForm(instance=profile)
    doctor_form = patient_form = None

    if user.role == 'doctor':
        doctor = get_or_create_doctor(user)
        doctor_form = DoctorProfileForm(instance=doctor)
    elif user.role == 'patient':
        patient = get_or_create_patient(user)
        patient_form = PatientProfileForm(instance=patient)

    if request.method == 'POST':
        user_form = CustomUserChangeForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        forms_valid = user_form.is_valid() and profile_form.is_valid()
        
        if user.role == 'doctor':
            doctor_form = DoctorProfileForm(request.POST, instance=doctor)
            forms_valid = forms_valid and doctor_form.is_valid()
        elif user.role == 'patient':
            patient_form = PatientProfileForm(request.POST, instance=patient)
            forms_valid = forms_valid and patient_form.is_valid()

        if forms_valid:
            user_form.save()
            profile_form.save()
            if doctor_form: doctor_form.save()
            if patient_form: patient_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')

    context = {
        'user_form': user_form, 'profile_form': profile_form,
        'doctor_form': doctor_form, 'patient_form': patient_form,
    }
    return render(request, 'profile.html', context)

# ==========================================================
# ------------ CHANGE PASSWORD VIEW (FINAL) ----------------
# ==========================================================
@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # This line is important to keep the user logged in after a password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
        messages.error(request, 'Please correct the error below.')
    
    return render(request, 'change_password.html', {'form': form})
# ==========================
# Doctor Views
# ==========================
@login_required
@user_passes_test(is_admin)
def add_doctor(request):
    if request.method == 'POST':
        form = AdminAddDoctorForm(request.POST)
        if form.is_valid():
            # Create the User account first
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                role='doctor' # Set the role to 'doctor'
            )
            
            # Now, create the associated Doctor profile
            doctor = Doctor.objects.create(
                user=user,
                specialization=form.cleaned_data['specialization'],
                license_number=form.cleaned_data['license_number'],
                experience_years=form.cleaned_data['experience_years'],
                consultation_fee=form.cleaned_data['consultation_fee'],
                clinic_address=form.cleaned_data['clinic_address']
                # Add defaults for other non-form fields if needed
            )
            
            messages.success(request, f"Doctor account for Dr. {user.get_full_name()} created successfully.")
            return redirect('admin_dashboard') # Or redirect to a doctor list page
    else:
        form = AdminAddDoctorForm()

    context = {
        'form': form
    }
    return render(request, 'add_doctor.html', context)


class DoctorListView(ListView):
    model = Doctor
    template_name = 'doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Doctor.objects.filter(is_active=True).select_related('user').annotate(avg_rating=Avg('appointments__review__rating'))
        form = DoctorSearchForm(self.request.GET)
        if form.is_valid():
            pass
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = DoctorSearchForm(self.request.GET or None)
        context['specializations'] = Specialization.objects.all()
        return context

class DoctorDetailView(DetailView):
    model = Doctor
    template_name = 'doctor_detail.html'
    context_object_name = 'doctor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object
        reviews = Review.objects.filter(appointment__doctor=doctor).select_related('appointment__patient__user')
        context.update({
            'availability': DoctorAvailability.objects.filter(doctor=doctor, is_available=True),
            'reviews': reviews,
            'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'],
            'review_count': reviews.count(),
            'is_patient': is_patient(self.request.user)
        })
        return context

# ==========================
# Appointment Views
# ==========================
@login_required
@user_passes_test(is_patient)
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    patient = get_or_create_patient(request.user)

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.doctor = doctor
            appointment.save()

            messages.success(request, f"Appointment booked with Dr. {doctor.user.get_full_name()}!")
            return redirect('appointment_detail', pk=appointment.id)
    else:
        form = AppointmentForm(initial={'doctor': doctor})
        messages.error(request, 'Booking failed. Please check the errors in the form.')

    return render(request, 'book_appointment.html', {
        'doctor': doctor,
        'form': form
    })


# -----------------------------
# Appointment Detail (Doctor/Patient/Admin)
# -----------------------------
@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    user = request.user

    # Security check: User must be part of the appointment or an admin
    if not (is_admin(user) or 
            (is_patient(user) and appointment.patient.user == user) or
            (is_doctor(user) and appointment.doctor.user == user)):
        return HttpResponseForbidden("You do not have permission to view this appointment.")

    review_form = ReviewForm()
    
    if request.method == 'POST':
        # Handle review submission by the patient
        if is_patient(user) and 'submit_review' in request.POST:
            if appointment.status == 'completed':
                review_form = ReviewForm(request.POST)
                if review_form.is_valid():
                    # Use update_or_create to link review to appointment and prevent duplicates
                    Review.objects.update_or_create(
                        appointment=appointment,
                        defaults=review_form.cleaned_data
                    )
                    messages.success(request, 'Thank you for your review!')
                    return redirect('appointment_detail', pk=pk)
            else:
                messages.error(request, "You can only review completed appointments.")
        
        # Handle status update by the doctor
        elif is_doctor(user) and 'update_status' in request.POST:
            new_status = request.POST.get('status')
            if new_status in [choice[0] for choice in Appointment.STATUS_CHOICES]:
                appointment.status = new_status
                appointment.save()
                messages.success(request, f'Appointment status updated to {appointment.get_status_display()}.')
                return redirect('appointment_detail', pk=pk)

    # ==========================================================
    # ------------------- THE FIX IS HERE ----------------------
    # ==========================================================
    # This logic correctly determines if the patient can leave a review.
    # It checks if the user is a patient, if the appointment is completed,
    # and if a review for this specific appointment does NOT already exist.
    can_review = (
        is_patient(user) and
        appointment.status == 'completed' and
        not Review.objects.filter(appointment=appointment).exists()
    )
    # ==========================================================

    context = {
        'appointment': appointment,
        'review_form': review_form,
        'can_review': can_review, # Pass the correct flag to the template
        'status_choices': Appointment.STATUS_CHOICES,
    }
    return render(request, 'appointment_detail.html', context)

# -----------------------------
# Appointment List (Patient/Doctor/Admin)
# -----------------------------
@login_required
def appointment_list(request):
    user = request.user

    if is_patient(user):
        appointments = Appointment.objects.filter(patient__user=user)
    elif is_doctor(user):
        appointments = Appointment.objects.filter(doctor__user=user)
    elif is_admin(user):
        appointments = Appointment.objects.all()
    else:
        return HttpResponseForbidden()
    
    search_query = request.GET.get('q', '')

    if search_query:
        # If a search term exists, filter the 'appointments' queryset further
        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query) |
            Q(appointment_number__icontains=search_query) 
          
     

            
            

        ).distinct()

    appointments = appointments.order_by('-appointment_date', '-appointment_time')

    context = {
        'appointments': appointments,
        'status_choices': Appointment.STATUS_CHOICES,
        'search_query': search_query, # Add this to the context
    }
    
    return render(request, 'appointment_list.html', context)

@login_required
@user_passes_test(is_patient)
def select_doctor(request):
    doctors = Doctor.objects.filter(is_active=True)
    # Filtering logic from original file
    specializations = Specialization.objects.all()
    context = {'doctors': doctors, 'specializations': specializations}
    return render(request, 'select_doctor.html', context)

@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, id=pk)
    # Permission check
    if not (is_admin(request.user) or request.user in [appointment.patient.user, appointment.doctor.user]):
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = AppointmentRescheduleForm(request.POST, appointment=appointment)
        if form.is_valid():
            appointment.appointment_date = form.cleaned_data['new_date']
            appointment.appointment_time = form.cleaned_data['new_time']
            appointment.status = 'rescheduled'
            appointment.save()
            messages.success(request, 'Appointment rescheduled successfully!')
            return redirect('appointment_detail', pk=pk)
    else:
        form = AppointmentRescheduleForm(appointment=appointment)
    
    return render(request, 'reschedule_appointment.html', {'form': form, 'appointment': appointment})

# ==========================================================
# ------------ MANAGE AVAILABILITY VIEW (FINAL) ------------
# ==========================================================
@login_required
@user_passes_test(is_doctor)
def manage_availability(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    availabilities = DoctorAvailability.objects.filter(doctor=doctor).order_by('day_of_week', 'start_time')

    if request.method == 'POST':
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            new_availability = form.save(commit=False)
            new_availability.doctor = doctor
            
            # Prevent overlapping schedules
            overlapping = DoctorAvailability.objects.filter(
                doctor=doctor,
                day_of_week=new_availability.day_of_week,
                start_time__lt=new_availability.end_time,
                end_time__gt=new_availability.start_time
            ).exists()

            if overlapping:
                messages.error(request, 'This time slot overlaps with an existing schedule.')
            else:
                new_availability.save()
                messages.success(request, 'New availability slot added successfully!')
                return redirect('manage_availability')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = DoctorAvailabilityForm()

    context = {
        'form': form,
        'availabilities': availabilities,
    }
    return render(request, 'manage_availability.html', context)


# ==========================================================
# ------------ DELETE AVAILABILITY VIEW (FINAL) ------------
# ==========================================================
@login_required
@user_passes_test(is_doctor)
def delete_availability(request, pk):
    # Ensure the slot exists and belongs to the logged-in doctor for security
    availability = get_object_or_404(DoctorAvailability, pk=pk, doctor__user=request.user)
    
    day = availability.get_day_of_week_display()
    availability.delete()
    messages.success(request, f'The availability slot for {day} has been deleted.')
    
    return redirect('manage_availability')

# ==========================================================
# ------------ MEDICAL RECORD VIEWS (FINAL) ------------
# ==========================================================
@login_required
@user_passes_test(is_doctor)
def create_medical_record(request, appointment_id):
    # This view's signature now correctly accepts 'appointment_id'
    appointment = get_object_or_404(Appointment, pk=appointment_id, doctor__user=request.user)
    patient = appointment.patient
    doctor = appointment.doctor

    if MedicalRecord.objects.filter(appointment=appointment).exists():
        messages.info(request, "A medical record for this appointment already exists.")
        return redirect('appointment_detail', pk=appointment.id)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = patient
            record.doctor = doctor
            record.appointment = appointment
            record.save()
            messages.success(request, "Medical record created successfully.")
            return redirect('appointment_detail', pk=appointment.id)
    else:
        form = MedicalRecordForm(initial={'title': f"Consultation on {appointment.appointment_date}"})

    context = {'form': form, 'appointment': appointment, 'patient': patient}
    return render(request, 'create_medical_record.html', context)




# ================================
# List Medical Records
# ================================
@login_required
def medical_record_list(request):
    user = request.user

    if is_patient(user):
        try:
            patient = user.patient
            records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
        except Patient.DoesNotExist:
            messages.warning(request, "Your patient profile is not yet complete.")
            return redirect('profile')

    elif is_doctor(user):
        try:
            doctor = user.doctor
            records = MedicalRecord.objects.filter(doctor=doctor).order_by('-created_at')
        except Doctor.DoesNotExist:
            messages.warning(request, "Your doctor profile is not yet complete.")
            return redirect('profile')

    else:
        # Admins or staff can see all records
        records = MedicalRecord.objects.all().order_by('-created_at')

    # Paginate the results
    paginator = Paginator(records, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }
    return render(request, 'medical_record_list.html', context)


# ================================
# Medical Record Detail
# ================================
@login_required
def medical_record_detail(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    user = request.user

    # Security check: ensure the user has permission to view this record
    if is_patient(user) and record.patient.user != user:
        return HttpResponseForbidden("You do not have permission to view this record.")
    if is_doctor(user) and record.doctor.user != user:
        return HttpResponseForbidden("You do not have permission to view this record.")

    context = {
        'record': record
    }
    return render(request, 'medical_record_detail.html', context)


# ==========================================================
# ------------ NOTIFICATION VIEWS (FINAL) ------------
# ==========================================================

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user, 
        is_deleted=False
    ).order_by('is_read', '-created_at')
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'notification_list.html', context)


@login_required
def notification_mark_read(request, pk):
   
    if pk == 0:
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications have been marked as read.')
    else:
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save()
            messages.success(request, 'Notification marked as read.')
    
    return redirect('notification_list')


@login_required
def notification_delete(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete() 
    messages.success(request, 'Notification deleted.')
    return redirect('notification_list')



# ==========================================================
# ----------------- PAYMENT VIEWS (FINAL) ------------------
# ==========================================================
@login_required
@user_passes_test(is_patient)
def process_payment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id, patient__user=request.user)

    # Prevent re-payment
    if hasattr(appointment, 'payment') and appointment.payment.payment_status == 'completed':
        messages.warning(request, "This appointment has already been paid for.")
        return redirect('appointment_detail', pk=appointment.id)
    
    # Get or create the payment object
    payment, created = Payment.objects.get_or_create(
        appointment=appointment,
        defaults={
            'patient': appointment.patient,
            'amount': appointment.doctor.consultation_fee,
            'payment_method': 'credit_card', # Default method
        }
    )

    if request.method == 'POST':
        form = OnlinePaymentForm(request.POST)
        if form.is_valid():
            # In a real app, you would process the payment with a gateway here.
            # For this simulation, we will just assume it's successful.
            
            payment.payment_status = 'completed'
            payment.payment_date = timezone.now()
            payment.transaction_id = f"TXN-SIM-{timezone.now().timestamp()}"
            payment.save()

            # Also update the appointment's payment status
            appointment.payment_status = 'paid'
            appointment.save()

            messages.success(request, 'Payment successful!')
            return redirect('payment_success', payment_id=payment.id)
        else:
            messages.error(request, 'Invalid card details. Please try again.')
    else:
        form = OnlinePaymentForm()

    context = {
        'appointment': appointment,
        'payment': payment,
        'form': form,
    }
    return render(request, 'process_payment.html', context)


@login_required
@user_passes_test(is_patient)
def payment_success(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id, patient__user=request.user)
    context = {
        'payment': payment
    }
    return render(request, 'payment_success.html', context)

@login_required
@user_passes_test(lambda u: is_doctor(u) or is_admin(u))
def payment_list(request):
    user = request.user
    payments = Payment.objects.select_related('patient__user', 'appointment__doctor__user').all()


    if is_doctor(user):
        payments = payments.filter(appointment__doctor__user=user)
    
    query = request.GET.get('q')
    if query:
        payments = payments.filter(
            Q(invoice_number__icontains=query) |
            Q(patient__user__username__icontains=query) |
            Q(transaction_id__icontains=query)
        ).distinct()

    paginator = Paginator(payments, 15) # Show 15 payments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': query or '',
    }
    return render(request, 'payment_list.html', context)

# ==========================
# Availability Views
# ==========================
# (These views are largely correct and can be used as is)

# ==========================
# Notification Views
# ==========================
# (These views are largely correct and can be used as is)

# ==========================
# API Views
# ==========================
# In core/views.py

@login_required
def get_available_time_slots(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    
    if not doctor_id or not date_str:
        return JsonResponse({'error': "Missing parameters"}, status=400)
    
    try:
        doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_of_week = date.weekday()
        
        availabilities = DoctorAvailability.objects.filter(
            doctor=doctor, day_of_week=day_of_week, is_available=True
        ).filter(Q(valid_to__gte=date) | Q(valid_to__isnull=True), valid_from__lte=date)
        
        slots = []
        for availability in availabilities:
            start_datetime = datetime.combine(date, availability.start_time)
            end_datetime = datetime.combine(date, availability.end_time)
            
            current_slot = start_datetime
            while current_slot < end_datetime:
                slot_time = current_slot.time()
                
                # Check if slot is in the future for today's date
                if date == timezone.now().date() and slot_time < timezone.now().time():
                    current_slot += timedelta(minutes=30)
                    continue

                is_booked = Appointment.objects.filter(
                    doctor=doctor, appointment_date=date, appointment_time=slot_time,
                    status__in=['pending', 'confirmed', 'rescheduled']
                ).exists()
                
                if not is_booked:
                    slots.append({
                        'start': slot_time.strftime('%H:%M'),
                        'formatted': slot_time.strftime('%I:%M %p')
                    })
                
                current_slot += timedelta(minutes=30)
        
        # Sort and remove duplicates just in case
        unique_slots = sorted(list({s['start']: s for s in slots}.values()), key=lambda x: x['start'])
        return JsonResponse({'slots': unique_slots})
    
    except Doctor.DoesNotExist:
        return JsonResponse({'error': 'Doctor not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_available_time_slots: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# ==========================
# Report Views
# ==========================
# (This view is largely correct and can be used as is)
@login_required
@user_passes_test(is_admin)
def generate_report(request):
    # This block handles showing the initial form page
    if request.method != 'POST' and not request.GET.get('report_type'):
        form = ReportGenerationForm()
        return render(request, 'generate_report.html', {'form': form})

    # This block handles generating the report from the POST form OR
    # filtering an existing report from the GET search form
    
    # Get all criteria from either the POST or GET request
    report_type = request.POST.get('report_type') or request.GET.get('report_type')
    date_range = request.POST.get('date_range') or request.GET.get('date_range')
    start_date_str = request.POST.get('start_date') or request.GET.get('start_date')
    end_date_str = request.POST.get('end_date') or request.GET.get('end_date')
    
    # Your existing logic for determining the date range
    try:
        if date_range == 'custom':
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            today = timezone.now().date()
            if date_range == 'today': start_date, end_date = today, today
            elif date_range == 'this_week': start_date, end_date = today - timedelta(days=today.weekday()), today
            elif date_range == 'this_month': start_date, end_date = today.replace(day=1), today
            elif date_range == 'this_year': start_date, end_date = today.replace(month=1, day=1), today
    except (ValueError, TypeError):
        messages.error(request, "Invalid date format provided.")
        return redirect('generate_report')
    
    # Prepare the context that will be passed to the report template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'report_type': report_type, # Pass these to be used in the filter form's hidden fields
        'date_range': date_range,
    }

    # Get the search query from the URL
    search_query = request.GET.get('q', '')
    context['search_query'] = search_query

    # Generate the appropriate report
    if report_type == 'appointments':
        queryset = Appointment.objects.filter(
            appointment_date__range=[start_date, end_date]
        ).select_related('patient__user', 'doctor__user').order_by('appointment_date')
        
        # ==========================================================
        # --- SEARCH FUNCTIONALITY ADDED HERE ---
        # ==========================================================
        if search_query:
            queryset = queryset.filter(
                Q(patient__user__username__icontains=search_query) |
                Q(doctor__user__username__icontains=search_query) |
                Q(appointment_number__icontains=search_query)
            ).distinct()
        # ==========================================================
            
        context.update({
            'report_title': 'Appointments Report',
            'appointments': queryset,
            'total_count': queryset.count(),
        })
        return render(request, 'appointment_report.html', context)
            
    elif report_type == 'payments':
        queryset = Payment.objects.filter(
            payment_date__date__range=[start_date, end_date],
            payment_status='completed'
        ).select_related('patient__user').order_by('payment_date')

        # ==========================================================
        # --- SEARCH FUNCTIONALITY ADDED HERE ---
        # ==========================================================
        if search_query:
            queryset = queryset.filter(
                Q(patient__user__username__icontains=search_query) |
                Q(invoice_number__icontains=search_query) |
                Q(transaction_id__icontains=search_query)
            ).distinct()
        # ==========================================================

        context.update({
            'report_title': 'Payments Report',
            'payments': queryset,
            'total_count': queryset.count(),
            'total_amount': queryset.aggregate(total=Sum('amount'))['total'] or 0
        })
        return render(request, 'payment_report.html', context)
    
    # Fallback if the report type is somehow invalid
    messages.error(request, "An unknown error occurred while generating the report.")
    return redirect('generate_report')
