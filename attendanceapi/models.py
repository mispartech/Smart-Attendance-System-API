# attendance/models.py
from django.db import models
from userauth.models import CustomUser, TempUser
from django.utils import timezone
from django.conf import settings

class Attendance(models.Model):
    member = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    face_detections = models.PositiveIntegerField(default=1)  # Count of face detections
    face_roi = models.ImageField(upload_to="attendance_faces/", blank=True, null=True)  # Saved JPEG of the detected face
    recognized_emotion = models.CharField(max_length=50, blank=True, null=True)  # Detected emotion
    distance = models.FloatField(blank=True, null=True)  # Cosine similarity score
    gender = models.CharField(max_length=10, default='undefined')
    role = models.CharField(max_length=20, choices=CustomUser.ROLE_CHOICES, default='member')
    department = models.ForeignKey('base.Department', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    time = models.TimeField()
    
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Attendance: {self.member.first_name} {self.member.last_name} - {self.date}"

class FaceEmbedding(models.Model):
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="face_embedding")
    embedding = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Embedding for {self.user.get_full_name() or self.user.email}"

class TempAttendance(models.Model):
    temp_user = models.ForeignKey(TempUser, on_delete=models.CASCADE)
    face_detections = models.PositiveIntegerField(default=1)
    face_roi = models.ImageField(upload_to="temp_attendance_faces/", blank=True, null=True)
    recognized_emotion = models.CharField(max_length=50, blank=True, null=True)
    distance = models.FloatField(blank=True, null=True)
    gender = models.CharField(max_length=10, default='undefined')
    role = models.CharField(max_length=20, default='visitor')  # For reporting
    department = models.ForeignKey('base.Department', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    time = models.TimeField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"TempAttendance: {self.temp_user.temp_username} - {self.date}"