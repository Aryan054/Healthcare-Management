from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from core import views as core_views
from . import views

urlpatterns = [
    # Admin URL is now in the project-level urls.py, but can be kept here too.
    # It's best practice to have it at the project level.
    

    path("", core_views.home, name="home"),

    # ==========================
    # Authentication URLs
    # ==========================
    path("users/", views.user_list, name="user_list"),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Password reset URLs
#     path('password-reset/', 
#          auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), 
#          name='password_reset'),
#     path('password-reset/done/', 
#          auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
#          name='password_reset_done'),
#     path('password-reset-confirm/<uidb64>/<token>/', 
#          auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), 
#          name='password_reset_confirm'),
#     path('password-reset-complete/', 
#          auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
#          name='password_reset_complete'),
    
    # ==========================
    # Dashboard URLs
    # ==========================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
        
    # ==========================
    # Profile URLs
    # ==========================
    path('profile/', views.profile_view, name='profile'),
     path('password/', views.change_password, name='change_password'),
    
    # ==========================
    # Doctor URLs
    # ==========================
    path("add-doctor/", views.add_doctor, name="add_doctor"),
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('doctors/<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    
    # ==========================
    # Appointment URLs
    # ==========================
    path('book-appointment/', views.select_doctor, name='select_doctor'),
    path('book-appointment/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:pk>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    
    # ==========================
    # Medical Record URLs
    # ==========================
    path('appointment/<int:appointment_id>/create-record/', views.create_medical_record, name='create_medical_record'),
    path('medical-records/', views.medical_record_list, name='medical_record_list'),
    path('medical-records/<int:pk>/', views.medical_record_detail, name='medical_record_detail'),
   
    
    # ==========================
    # Availability URLs
    # ==========================
    path('availability/', views.manage_availability, name='manage_availability'),
    path('availability/<int:pk>/delete/', views.delete_availability, name='delete_availability'),
    
    # ==========================
    # Notification URLs
    # ==========================
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    
    # ==========================
    # API URLs
    # ==========================
    path('api/time-slots/', views.get_available_time_slots, name='get_available_time_slots'),
    
    # ==========================
    # Report URLs
    # ==========================
    

    path('reports/', views.generate_report, name='generate_report'),

     # ==========================
    # Payment Urls 
    # ==========================

    path('payment/process/<int:appointment_id>/', views.process_payment, name='process_payment'),
    path('payment/success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('payments/', views.payment_list, name='payment_list'),
]