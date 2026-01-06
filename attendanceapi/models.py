from django.db import models
from django.conf import settings

# Create your models here.
class FaceEmbedding(models.Model):
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="face_embedding")
    embedding = models.JSONField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Embedding for {self.user.get_full_name() or self.user.email}"