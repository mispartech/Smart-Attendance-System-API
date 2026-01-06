from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('parish_pastor', 'Parish Pastor'),
        ('department_head', 'Department Head'),
        ('ushering_head_admin', 'Ushering Head Admin'),
        ('usher_admin', 'Usher Admin'),
        ('member', 'Member'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    department = models.ForeignKey('base.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    is_department_head = models.BooleanField(default=False)

    # Additional fields
    age_range = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    face_image = models.ImageField(upload_to="faces/", null=True, blank=True)
    captured_image = models.ImageField(upload_to="faces/", null=True, blank=True)
    user_face_embedding = models.JSONField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.phone_number:
            if not self.phone_number.isdigit() or len(self.phone_number) != 11:
                raise ValidationError({'phone_number': 'Phone number must be exactly 11 digits.'})

    def save(self, *args, **kwargs):
        """
        Automatically assign appropriate role:
        - createsuperuser → super_admin
        - member registration → member (default)
        - others remain manually assigned
        """
        if self.is_superuser and self.role != 'super_admin':
            self.role = 'super_admin'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

@receiver(post_save, sender=CustomUser)
def assign_default_department(sender, instance, created, **kwargs):
    if created and not instance.department:
        from base.models import Department

        default_dept, _ = Department.objects.get_or_create(
            name='Congregation',
            defaults={'allowed_roles': ['member']}
        )
        instance.department = default_dept
        instance.save()
        default_dept.update_stats()
        
class TempUser(models.Model):
    visitor_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    temp_username = models.CharField(max_length=150, unique=True)  # e.g. "visitor_abcd1234"
    temp_email = models.EmailField(unique=True)  # ✅ Added for identification
    age_range = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    department = models.ForeignKey('base.Department', on_delete=models.SET_NULL, null=True, blank=True)
    face_image = models.ImageField(upload_to="temp_faces/", null=True, blank=True)
    captured_image = models.ImageField(upload_to="temp_faces/", null=True, blank=True)
    face_embedding = models.JSONField(null=True, blank=True)
    claimed = models.BooleanField(default=False)  # ✅ True when migrated to CustomUser
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.temp_username} ({'Claimed' if self.claimed else 'Unclaimed'})"