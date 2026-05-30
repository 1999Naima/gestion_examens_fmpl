from django.urls import path

from examens import views

app_name = 'examens'


urlpatterns = [
     path('calendrier/', views.calendrier_examens, name='calendrier_examens'),
     path('ajax/get-students-by-exam/', views.get_students_by_exam, name='get_students_by_exam'),
     path('test/', views.test_view, name='test'),  # Temporary test
     path('presence-pdf/<int:repartition_id>/', views.generate_presence_pdf, name='generate_presence_pdf'),
     path('presence-multiple-pdf/', views.generate_multiple_presence_pdf, name='generate_multiple_presence_pdf'),
     path('proces-verbal/<int:repartition_id>/', views.generate_proces_verbal, name='proces_verbal'),
     path('convocations/', views.convocations_list, name='convocations_list'),
    path('convocation/<int:surveillant_id>/', views.generate_convocation_pdf, name='generate_convocation_surveillant'),
    path('convocation/<int:surveillant_id>/session/<int:session_id>/', views.generate_convocation_pdf, name='generate_convocation_surveillant_session'),
    path('convocations/bulk/', views.convocation_bulk_pdf, name='convocation_bulk_pdf'),
]