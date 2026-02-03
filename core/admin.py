from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin.models import LogEntry
from django.db.models import Avg

from .models import (
    User, Profile, Specialization, Doctor, Patient,
    Appointment, MedicalRecord, Review, Prescription,
    DoctorAvailability, Payment, Notification
)


# ==========================
# Custom Admin Classes
# ==========================
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password', 'role', 'is_active', 'is_staff'),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_role', 'date_of_birth')
    list_filter = ('gender', 'user__role')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user_link',)
    
    @admin.display(description='Role', ordering='user__role')
    def get_role(self, obj):
        return obj.user.role
    
    @admin.display(description='User')
    def user_link(self, obj):
        if obj.user_id:
            # Corrected reverse to use the app name 'core'
            url = reverse("admin:core_user_change", args=(obj.user.id,))
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'experience_years', 'consultation_fee', 'is_active', 'get_average_rating')
    list_filter = ('is_active', 'specializations')
    search_fields = ('user__username', 'user__email', 'license_number')
    filter_horizontal = ('specializations',)
    readonly_fields = ('user_link', 'get_average_rating')
    
    @admin.display(description='User')
    def user_link(self, obj):
        if obj.user_id:
            url = reverse("admin:core_user_change", args=(obj.user.id,))
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"
    
    @admin.display(description='Avg Rating', ordering='avg_rating')
    def get_average_rating(self, obj):
        result = obj.appointments.aggregate(avg_rating=Avg('review__rating'))
        return round(result['avg_rating'], 2) if result['avg_rating'] else 'N/A'

    @admin.action(description='Approve selected doctors')
    def approve_doctors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} doctor(s) successfully approved.')

    actions = [approve_doctors]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(avg_rating=Avg('appointments__review__rating'))


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'blood_group', 'get_age', 'emergency_contact_name')
    list_filter = ('blood_group',)
    search_fields = ('user__username', 'user__email', 'emergency_contact_name')
    readonly_fields = ('user_link', 'get_bmi')
    
    @admin.display(description='User')
    def user_link(self, obj):
        if obj.user_id:
            url = reverse("admin:core_user_change", args=(obj.user.id,))
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"
    
    @admin.display(description='Age')
    def get_age(self, obj):
        # The correct path is patient -> user -> profile -> age
        # We also add safety checks in case a profile or date of birth doesn't exist
        if hasattr(obj, 'user') and hasattr(obj.user, 'profile') and obj.user.profile.date_of_birth:
            return obj.user.profile.age
        return 'N/A'
    
    @admin.display(description='BMI')
    def get_bmi(self, obj):
        return obj.bmi or 'N/A'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_number', 'patient', 'doctor', 'appointment_date', 'appointment_time', 'status', 'payment_status')
    list_filter = ('status', 'payment_status', 'appointment_date', 'doctor')
    search_fields = ('appointment_number', 'patient__user__username', 'doctor__user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'appointment_date'


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'get_day_of_week_display', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available', 'doctor')
    search_fields = ('doctor__user__username',)

# ==========================
# Admin Site Customization
# ==========================
admin.site.site_header = "Healthcare Management System Admin"
admin.site.site_title = "Healthcare Admin Portal"
admin.site.index_title = "Welcome to Healthcare Administration"

# ==========================
# Main Model Registrations
# ==========================
# We register User last to ensure our CustomUserAdmin is used
admin.site.register(User, CustomUserAdmin)

# Register other models that don't need special classes
admin.site.register(MedicalRecord)
admin.site.register(Prescription)
admin.site.register(Review)
admin.site.register(Payment)
admin.site.register(Notification)
admin.site.register(LogEntry)