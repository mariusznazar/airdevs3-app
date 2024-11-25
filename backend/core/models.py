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

class FileAnalysis(models.Model):
    file_name = models.CharField(max_length=255, unique=True)
    file_type = models.CharField(max_length=10)  # 'txt', 'mp3', 'png'
    content = models.TextField()
    raw_content = models.BinaryField(null=True, blank=True)
    category = models.CharField(max_length=10, null=True)  # 'people', 'hardware', 'none'
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['file_name']),
            models.Index(fields=['file_type']),
        ] 

class Document(models.Model):
    url = models.URLField(max_length=2000, unique=True)
    original_content = models.TextField()
    processed_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['url'], name='document_url_idx'),
            models.Index(fields=['created_at'], name='document_created_at_idx'),
        ]

    def __str__(self):
        return self.url