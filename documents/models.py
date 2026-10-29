from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    DOC_TYPES = (
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('passport', 'Passport Photo'),
        ('id_cards', 'ID Card / Aadhaar'),
        ('other', 'Other Document'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, default='Document')
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES, default='other')

    # Original uploaded raw file
    raw_file = models.ImageField(upload_to='documents/raw/', blank=True, null=True)

    # Processed/Cropped output file (View compatibility ke liye 'image' field added)
    image = models.ImageField(upload_to='documents/processed/', null=True, blank=True)
    processed_file = models.ImageField(upload_to='documents/processed/', null=True, blank=True)

    # AI extracted data stored securely in JSON format
    extracted_data = models.JSONField(default=dict, blank=True)

    # Status tracking for background processing
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title or 'Document'} ({self.doc_type}) - {self.id}"