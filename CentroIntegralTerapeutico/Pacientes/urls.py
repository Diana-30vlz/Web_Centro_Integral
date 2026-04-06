# Pacientes/urls.py

from django.urls import path
from . import views
from .views import CuestionarioHistoriaClinicaWizard, CuestionarioMusculoEsqueleticoWizard
from .forms import (
    HistoriaClinicaUnificadaForm, HistoriaClinicaSegundaHoja, CuestionarioExploracionGlasgow,
    CuestionarioExploracionFinalForm, HistoriaClinicaMusculoEsqueleticoCompletoForm
)

# Definir los formularios en el mismo archivo
FORMS = [
    ("Historia Clínica", HistoriaClinicaUnificadaForm),
    ("Interrogatorio por Aparatos y Sistemas", HistoriaClinicaSegundaHoja),
    ("Exploración", HistoriaClinicaSegundaHoja),
    ("Exploración 3", CuestionarioExploracionGlasgow),
    ("Exploración 5", CuestionarioExploracionFinalForm),
]

FORMS_ME = [
    ("parte_1", HistoriaClinicaMusculoEsqueleticoCompletoForm),
]
urlpatterns = [
    # URLs para pacientes
    path('CrearPaciente', views.Crear_Pacientes_view, name='CrearPaciente'),
    path('lista_pacientes', views.Lista_Pacientes_view, name='lista_pacientes'),
    path('<int:pk>/editar/', views.editar_paciente_view, name='editar_paciente'),
    path('<int:pk>/eliminar/', views.eliminar_paciente_view, name='eliminar_paciente'),
    path('<int:pk>/expediente/', views.registros_paciente_view, name='expediente_paciente'),

    # URLs para la Agenda
    path('agenda', views.agenda_view, name='agenda'),
    path('crear', views.crear_cita_view, name='crear_cita'),
    path('<int:pk>/editarcita/', views.editar_cita_view, name='editar_cita'),
    path('<int:pk>/eliminarcita/', views.eliminar_cita_view, name='eliminar_cita'),
    # NUEVA URL PARA ACTUALIZAR ASISTENCIA
    path('citas/<int:pk>/asistencia-post/', views.actualizar_asistencia_simple, name='actualizar_asistencia_simple'),

    # URLs para las historias clínicas y orden médica
    path('<int:pk>/historia-clinica/', views.historia_clinica_paciente, name='historia_clinica_paciente'),
    path('<int:pk>/Resultados_Historial_Clinico/<int:historia_pk>/', views.Resultados_Historial_Clinico, name='Resultados_Historial_Clinico'),
    path('<int:pk>/Resultados_Historial_ClinicoME/<int:historia_pk>/', views.Resultados_Historial_ClinicoME, name='Resultados_Historial_ClinicoME'),
    path('<int:pk>/HistorialMusculoEsqueleticoPDF/<int:historia_pk>/', views.HistorialMusculoEsqueleticoPDF, name='HistorialMusculoEsqueleticoPDF'),
    path('<int:pk>/HistorialClinicoPDF/<int:historia_pk>/', views.HistorialClinicoPDF, name='HistorialClinicoPDF'),
    path('historia-clinica/eliminar/<int:historia_pk>/', views.eliminar_historial_clinico_view, name='eliminar_historial_clinico_view'),
    path('historial-clinico-me/eliminar/<int:pk>/', views.eliminar_historial_clinico_me, name='eliminar_historial_clinico_me'),





    path('paciente/<int:paciente_pk>/consentimientos-legales/', views.consentimiento_real_list, name='consentimiento_real_list'),
    path('paciente/<int:paciente_pk>/consentimientos-legales/crear/', views.consentimiento_real_create, name='consentimiento_real_create'),
    path('consentimientos-legales/<int:pk>/', views.consentimiento_real_detail, name='consentimiento_real_detail'),
    path('consentimientos-legales/<int:pk>/eliminar/', views.consentimiento_real_delete, name='consentimiento_real_delete'),
    path('consentimientos-legales/<int:pk>/pdf/', views.imprimir_consentimiento_real_pdf, name='imprimir_consentimiento_real_pdf'),


    path('<int:pk>/historia-clinica-me/', views.historia_clinica_paciente_me, name='historia_clinica_paciente_me'),
    path('<int:pk>/orden-medica/', views.orden_medica_paciente, name='orden_medica_paciente'),

 # URL para la lista de consentimientos de un paciente específico
    path('<int:paciente_pk>/consentimientos/', views.consentimiento_list_by_paciente, name='consentimiento_list_by_paciente'),

    # URL para crear un nuevo consentimiento para un paciente
    path('<int:paciente_pk>/consentimientos/crear/', views.consentimiento_create, name='consentimiento_create'),

    # URL para ver los detalles de un consentimiento
    path('consentimientos/detalles/<int:pk>/', views.consentimiento_detail, name='consentimiento_detail'),

    # URL para generar el PDF del consentimiento
    path('consentimientos/imprimir/<int:pk>/', views.imprimir_consentimiento_pdf, name='consentimiento_pdf'),

    path('consentimientos/eliminar/<int:pk>/', views.eliminar_consentimiento, name='eliminar_consentimiento'),



     # --- INICIO DE LAS NUEVAS RUTAS PARA RECETAS ---
    path('recetas/<int:paciente_pk>/crear/', views.crear_receta_view, name='crear_receta'),
    path('recetas/<int:paciente_pk>/', views.lista_recetas_view, name='lista_recetas'),
    path('recetas/<int:pk>/detalle/', views.detalle_receta_view, name='detalle_receta'),
    path('recetas/<int:pk>/pdf/', views.imprimir_receta_pdf, name='imprimir_receta_pdf'),
    path('receta/<int:pk>/eliminar/', views.eliminar_receta, name='eliminar_receta'),

    # --- FIN DE LAS NUEVAS RUTAS ---

    # URLs para el FormWizard (Historia Clínica General)
    # Esta es la URL que inicia el formulario de varios pasos historia_clinica_paciente
    path('<int:paciente_id>/nueva-historia-clinica/',
         CuestionarioHistoriaClinicaWizard.as_view(FORMS),
         name='crear_historia_clinica_wizard'),
    path('<int:paciente_id>/nueva-historia-clinica_ME/',
         CuestionarioMusculoEsqueleticoWizard.as_view(FORMS_ME),
         name='crear_historia_clinica_wizard_ME'),

]