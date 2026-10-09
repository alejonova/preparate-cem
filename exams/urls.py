from django.urls import path
from .views import (
    home, test_simulacro, subject_detail, start_exam, exam_question, finish_exam, exam_result,
    history, study_guides, download_study_guide, activation_portal,
)

urlpatterns = [
    path('', home, name='home'),
    path('test-simulacro/', test_simulacro, name='test_simulacro'),
    path('activar/', activation_portal, name='activation_portal'),
    path('materia/<int:subject_id>/', subject_detail, name='subject_detail'),
    path('materia/<int:subject_id>/iniciar/', start_exam, name='start_exam'),
    path('guias/', study_guides, name='study_guides'),
    path('guias/<int:guide_id>/descargar/', download_study_guide, name='download_study_guide'),
    path('examen/pregunta/<int:position>/', exam_question, name='exam_question'),
    path('examen/finalizar/', finish_exam, name='finish_exam'),
    path('examen/resultado/', exam_result, name='exam_result'),
    path('historial/', history, name='history'),
]
