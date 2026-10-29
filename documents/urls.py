from django.urls import path
from .views import (
    kiosk_home_view,
    document_gallery_view,
    delete_document_view,
    DocumentUploadView,
    generate_kiosk_print_batch
)

urlpatterns = [
    path('', kiosk_home_view, name='kiosk_home'),
    path('gallery/', document_gallery_view, name='document_gallery'),
    path('document/delete/<int:doc_id>/', delete_document_view, name='delete_document'),
    path('upload/', DocumentUploadView, name='document_upload'),
    path('print-batch/', generate_kiosk_print_batch, name='print_batch'),
]