from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    allowed_roles = models.JSONField(default=list)  # Flexible roles for this department

    department_head = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_department'
    )

    number_of_members = models.PositiveIntegerField(default=1)
    number_of_roles_assigned = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    def update_stats(self):
        self.number_of_members = User.objects.filter(department=self, role='member').count()
        self.number_of_roles_assigned = User.objects.filter(department=self).exclude(role='member').count()
        self.save()

    def __str__(self):
        return self.name
    
class ActivityLog(models.Model):
    user = models.ForeignKey('userauth.CustomUser', on_delete=models.CASCADE)
    action = models.CharField(max_length=255)  # e.g. "Added New Member"
    details = models.TextField(blank=True, null=True)  # e.g. "to the Finance department"
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.action}"