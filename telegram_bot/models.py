from django.db import models
import os


class DocumentType(models.TextChoices):
    SPECIFICATION = 'specification', 'Technical Specification'
    EVALUATION = 'evaluation', 'Technical Evaluation'
    AFTER_DELIVERY = 'after_delivery', 'After Delivery'
    TERMS_OF_REFERENCE = 'terms_of_reference', 'Terms of Reference'


class Document(models.Model):
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    project_name = models.CharField(max_length=200)
    user_name = models.CharField(max_length=200)
    file_name = models.CharField(max_length=500)
    file_path = models.CharField(max_length=1000, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_replied = models.BooleanField(default=False)
    scan_copy_present = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.document_type} - {self.project_name} - {self.user_name}"

    class Meta:
        ordering = ['-uploaded_at']
