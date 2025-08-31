
# mi_proyecto/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importa las vistas desde el módulo de Pacientes que no están en la app
from Pacientes import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.HomeSinInicio, name='HomeSinInicio'),
    path('doctor_home/', views.doctor_home_view, name='doctor_home'),
    path('signup/', views.signup_view, name='signup'),
    path('signin/', views.signin_view, name='signin'),
    path('logout/', views.logout_view, name='logout'),
    
    # Esta es la línea clave para incluir todas las URLs de tu app 'Pacientes'
    path('pacientes/', include('Pacientes.urls')),

        
    # NUEVAS URLs para la Agenda
    path('agenda', views.agenda_view, name='agenda'), # Vista de la agenda
    path('crear', views.crear_cita_view, name='crear_cita'), # Crear nueva cita
    path('<int:pk>/editarcita/', views.editar_cita_view, name='editar_cita'), # Editar cita
    path('<int:pk>/eliminarcita/', views.eliminar_cita_view, name='eliminar_cita'), # Eliminar cita
    
    # URLS para inventario
    path('inventario/', include('Inventario.urls')),


        #FARMACIA
    path('login/', views.login_view, name='login'), # URL de inicio de sesión de Farmacia
    path('farmacia/dashboard/', views.dashboard_farmacia, name='dashboard_farmacia'), # Dashboard de Farmacia
    path('farmacia/registro/', views.registro_farmacia_view, name='registro_farmacia'), # Registro de Farmacia
    
    
# ... (tus otras URLs)
    path('recuperar-cuenta/', views.recovery_request_view, name='recovery_request'),
    path('recuperar-cuenta/verificar/', views.recovery_verify_view, name='recovery_verify'),
    path('recuperar-cuenta/cambiar-contrasena/', views.recovery_password_reset_view, name='recovery_password_reset'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)