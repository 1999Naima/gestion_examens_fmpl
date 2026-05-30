# salles/urls.py
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from . import views

app_name = 'salles'

urlpatterns = [
    path('generate-seats/<int:amphi_id>/', staff_member_required(views.generate_seats_view), name='generate_seats'),
    path('download-qrs/<int:amphi_id>/', staff_member_required(views.download_qrs_view), name='download_qrs'),
]