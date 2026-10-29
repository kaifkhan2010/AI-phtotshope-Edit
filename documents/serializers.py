from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'doc_type',
            'raw_file', 'processed_file',
            'extracted_data', 'is_processed', 'created_at'
        ]
        read_only_fields = ['processed_file', 'extracted_data', 'is_processed', 'created_at']
        extra_kwargs = {'user': {'required': False}}