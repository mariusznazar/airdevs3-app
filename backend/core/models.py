from django.db import models
from django.contrib.auth.models import User

class Module(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    
    class Meta:
        abstract = True

class ProcessingTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    result = models.JSONField(null=True, blank=True) 