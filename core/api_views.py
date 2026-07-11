from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User, Profile, Doctor, Patient, Appointment, MedicalRecord, Payment, Specialization
from .serializers import (
    UserSerializer, ProfileSerializer, DoctorSerializer, PatientSerializer,
    AppointmentSerializer, MedicalRecordSerializer, PaymentSerializer, SpecializationSerializer
)

class SpecializationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [permissions.IsAuthenticated]

class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.objects.select_related('user').prefetch_related('specializations')
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.select_related('user')
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Patients can only see their own profile, doctors/admins can see all
        user = self.request.user
        if user.role == 'patient':
            return Patient.objects.filter(user=user)
        return Patient.objects.all()

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient__user=user)
        elif user.role == 'doctor':
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'patient':
            patient = Patient.objects.get(user=user)
            serializer.save(patient=patient)
        else:
            # Admins or others can specify patient
            serializer.save()

class MedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return MedicalRecord.objects.filter(patient__user=user)
        elif user.role == 'doctor':
            return MedicalRecord.objects.filter(doctor__user=user)
        return MedicalRecord.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'doctor':
            doctor = Doctor.objects.get(user=user)
            serializer.save(doctor=doctor)
        else:
            serializer.save()

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Payment.objects.filter(patient__user=user)
        return Payment.objects.all()
