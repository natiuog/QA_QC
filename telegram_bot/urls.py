from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.telegram_webhook, name='telegram_webhook'),
    path('health/', views.health_check, name='health_check'),
    path('generate-excel/', views.generate_excel_report, name='generate_excel_report'),
    path('document-status/', views.get_document_status, name='get_document_status'),
]