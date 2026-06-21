# salles/urls.py
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from . import views

app_name = 'salles'

urlpatterns = [
    path('generate-sieges/<int:amphi_id>/', staff_member_required(views.generate_sieges_view), name='generate_sieges'),
    path('download-qrs/<int:amphi_id>/', staff_member_required(views.download_qrs_view), name='download_qrs'),
]