from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm # ¡Importa estos formularios!
from django.contrib.auth import login, logout, authenticate # Importa login, logout y authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages # Para mensajes flash al usuario
from .forms import * # Importa desde el mismo directorio
from .models import *
from datetime import date, timedelta, datetime
from django.db.models import Q # Para consultas OR
import calendar
from .models import * # Asegúrate de que tu modelo Paciente esté importado
from django.contrib.auth.models import Group # Importa Group para asignar al grupo "Farmacia"
from .forms import RecoveryRequestForm, RecoveryVerifyForm, RecoveryPasswordResetForm
from django.contrib.auth import update_session_auth_hash
from formtools.wizard.views import SessionWizardView
from django.views.decorators.http import require_POST # Importa este decorador
from django.db import IntegrityError


# views.py
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from .models import (
    Paciente,
    ConsentimientoInformado,
    HistoriaClinica
)

from .forms import *




#VIEWS REPORTLAB


from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, ListFlowable,  ListItem
import os
from django.contrib.auth.decorators import login_required
from django.conf import settings


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Line # <-- Importa estos módulos
from reportlab.lib.enums import TA_CENTER, TA_LEFT






FORMS = [
    ("Historia Clínica", CuestionarioParte1Form),
    ("Historia Clínica General", CuestionarioParte2Form),
    ("Ginecológico", CuestionarioGinecologicoForm),
    ("Interrogatorio por Aparatos y Sistemas (1)", CuestionarioDigestivoForm),#Cuestionario Digestivo
    ("Interrogatorio por Aparatos y Sistemas (2)", CuestionarioCardioRespiratorioForm),
    ("Interrogatorio por Aparatos y Sistemas (3)", CuestionarioGenitalUrinarioForm),
    ("Interrogatorio por Aparatos y Sistemas (4)", CuestionarioEndocrinoCuelloForm),
    ("Exploración 1", CuestionarioExploracion1Form),
    ("Exploración 2", CuestionarioExploracion2Form),
    ("Exploración 3", CuestionarioPulsosConcienciaForm),
    ("Exploración 4", CuestionarioGlasgowVisualForm),
    ("Exploración 5", CuestionarioExploracionFinalForm),
]
TEMPLATES = {
    "Historia Clínica": "cuestionario/HC_HistoriaClinica1.html",
    "Historia Clínica General": "cuestionario/HC_HistoriaClinicaGeneral.html",
    "Ginecológico": "cuestionario/HC_Ginecologico.html",
    "Interrogatorio por Aparatos y Sistemas (1)": "cuestionario/HC_Digestivo.html",
    "Interrogatorio por Aparatos y Sistemas (2)": "cuestionario/HC_CardioRespiratorio.html",
    "Interrogatorio por Aparatos y Sistemas (3)": "cuestionario/HC_GenitalUrinario.html",
    "Interrogatorio por Aparatos y Sistemas (4)": "cuestionario/HC_EndocrinoCuello.html",
    "Exploración 1": "cuestionario/HC_Exploracion1.html",
    "Exploración 2": "cuestionario/HC_Exploracion2.html",
    "Exploración 3": "cuestionario/HC_Pulsos.html",
    "Exploración 4": "cuestionario/HC_Glasgow.html",
    "Exploración 5": "cuestionario/HC_ExploracionFinal.html",
}


FORMS_ME = [
    ("parte_1", CuestionarioParte1FormME),
    ("parte_2", CuestionarioParte2FormME),
    ("examen_fisico", ExamenFisicoForm),
]

TEMPLATES_ME = {
    "parte_1": "cuestionario/HCME_HistoriaClinica1.html",
    "parte_2": "cuestionario/HCME_HistoriaClinicaGeneral.html",
    "examen_fisico": "cuestionario/HCME_ExamenFisico.html",
}

# Funciones de ayuda para obtener el perfil del doctor
def get_doctor_profile(user):
    try:
        if user.groups.filter(name='Doctora').exists():
            return Doctor.objects.get(user=user)
        elif user.groups.filter(name='Farmacia').exists():
            farmacia_profile = FarmaciaProfile.objects.get(user=user)
            return farmacia_profile.doctor
    except (Doctor.DoesNotExist, FarmaciaProfile.DoesNotExist):
        return None
    return None

def get_doctor_user(user):
    profile = get_doctor_profile(user)
    return profile.user if profile else None


# Create your views here.

def HomeSinInicio(request):
    # Si el usuario ya está autenticado, redirigirlo a su página principal
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Farmacia').exists():
            return redirect('dashboard_farmacia')
        
        if request.user.groups.filter(name='Doctora').exists():
            return redirect('doctor_home')

    # Si no está autenticado, renderizar la página de inicio sin sesión
    is_farmacia = False
    is_doctora = False
    

    context = {
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora
    }
    
    return render(request, 'HomeSinInicio.html', context)


# VISTA DE REGISTRO CON UserCreationForm
def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            user_type = form.cleaned_data.get('user_type')

            if user_type == 'doctor':
                try:
                    group = Group.objects.get(name='Doctora')
                except Group.DoesNotExist:
                    group = Group.objects.create(name='Doctora')
                user.groups.add(group)

                Doctor.objects.create(user=user)

                messages.success(request, '¡Tu cuenta de doctor ha sido creada exitosamente!')
                return redirect('doctor_home')

            elif user_type == 'farmacia':
                try:
                    group = Group.objects.get(name='Farmacia')
                except Group.DoesNotExist:
                    group = Group.objects.create(name='Farmacia')
                user.groups.add(group)
                messages.success(request, '¡Tu cuenta de farmacia ha sido creada exitosamente!')
                return redirect('farmacia_home')

            # Si por alguna razón el tipo de usuario no es ni 'doctor' ni 'farmacia',
            # es mejor redirigir a una URL segura y genérica como el login.
            else:
                messages.error(request, 'No se pudo asignar un tipo de usuario válido. Contacte a un administrador.')
                return redirect('signin')  # O a la página de inicio de sesión

        else:
            messages.error(request, 'Hubo un error en los datos. Por favor, verifica el formulario.')
    
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'signup.html', {'form': form})

def signin_view(request):
    # Si el usuario ya está autenticado, redirige a su página de inicio.
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Doctora').exists():
            return redirect('doctor_home')
        # Si está autenticado pero no es Doctora, lo enviamos al HomeSinInicio
        else:
            return redirect('HomeSinInicio')


    if request.method == 'POST':
        # AuthenticationForm necesita el request como primer argumento
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user() # Obtiene el usuario autenticado (pero aún no logueado)
            
            # --- NUEVA LÓGICA DE VERIFICACIÓN DEL GRUPO 'Doctora' ---
            if user.groups.filter(name='Doctora').exists():
                login(request, user) # Inicia la sesión solo si es del grupo 'Doctora'
                messages.success(request, f'¡Bienvenido de nuevo, {user.username}!')
            
                # Redireccionar después de login
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('doctor_home')
            else:
                # Si el usuario no es del grupo 'Doctora', mostramos un error y no lo logueamos
                messages.error(request, "Tus credenciales no corresponden a un rol de Doctora.")
                # El código simplemente continuará para volver a renderizar el formulario
        
        # Si el formulario no es válido o el usuario no es del grupo 'Doctora',
        # el código llega aquí y se renderiza el template nuevamente
        form = AuthenticationForm(request.POST) # Para mantener los datos del formulario

    else:
        form = AuthenticationForm() # Crea un formulario vacío para peticiones GET
    
    return render(request, 'signin.html', {'form': form})

# VISTA PARA CERRAR SESIÓN (usando la función logout de Django)
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('/') # Redirige a la página de inicio de sesión o a tu página principal



def login_view(request):
    """
    Vista para manejar el inicio de sesión exclusivo del personal de Farmacia.
    """
    # Si el usuario ya está autenticado Y pertenece al grupo 'Farmacia', redirige al dashboard.
    if request.user.is_authenticated and request.user.groups.filter(name='Farmacia').exists():
        return redirect('dashboard_farmacia')
    
    # Si el usuario está autenticado pero NO es de Farmacia, le deslogueamos.
    # Esto evita que un Doctor inicie sesión a través de este formulario.
    if request.user.is_authenticated:
        logout(request)
        messages.error(request, "Este inicio de sesión es solo para personal de Farmacia.")

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Si el usuario existe, verifica si pertenece al grupo 'Farmacia'.
                if user.groups.filter(name='Farmacia').exists():
                    login(request, user)
                    messages.success(request, f"¡Bienvenido, {username}!")
                    return redirect('dashboard_farmacia')
                else:
                    # Si no es de Farmacia, muestra un error y no lo loguea.
                    messages.error(request, "Tu cuenta no está asociada al rol de Farmacia.")
            else:
                messages.error(request, "Nombre de usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Error en el formulario de login. Por favor, revisa tus credenciales.")
    else:
        form = LoginForm()

    return render(request, 'registration/login.html', {'form': form})



def registro_farmacia_view(request):
    """
    Vista para el registro exclusivo del personal de Farmacia.
    """
    if request.method == 'POST':
        form = FarmaciaRegistrationForm(request.POST)
        if form.is_valid():
            # Obtén el usuario sin guardarlo en la DB todavía
            user = form.save(commit=False)
            user.user_type = 'farmacia' # Asigna el user_type antes de guardar
            user.save()

            # Obtén el doctor seleccionado del formulario
            doctor_seleccionado = form.cleaned_data.get('doctor') # Usar .get() es más seguro

            # --- VALIDACIÓN AÑADIDA ---
            # Es crucial verificar que se haya seleccionado un doctor antes de continuar.
            if not doctor_seleccionado:
                # Si no se seleccionó un doctor, borramos el usuario recién creado para no dejar datos inconsistentes.
                user.delete() 
                messages.error(request, "Error: Debes seleccionar un doctor para asociar a la cuenta de farmacia.")
                # Volvemos a renderizar el formulario para que el usuario corrija el error.
                return render(request, 'registration/registro_farmacia.html', {'form': form})

            # Crea el FarmaciaProfile y asóciale el doctor seleccionado
            try:
                FarmaciaProfile.objects.create(
                    user=user,
                    doctor=doctor_seleccionado  # Asigna el doctor aquí
                )
            except IntegrityError:
                # Si falla la creación del perfil, borra el usuario para evitar inconsistencias
                user.delete()
                messages.error(request, "Hubo un error al crear el perfil de farmacia.")
                return redirect('registro_farmacia')

            try:
                farmacia_group = Group.objects.get(name='Farmacia')
            except Group.DoesNotExist:
                farmacia_group = Group.objects.create(name='Farmacia')

            user.groups.add(farmacia_group)
            
            messages.success(request, "¡Cuenta de Farmacia creada exitosamente! Por favor, inicia sesión.")
            return redirect('HomeSinInicio')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en '{form[field].label}': {error}")
    else:
        form = FarmaciaRegistrationForm()

    return render(request, 'registration/registro_farmacia.html', {'form': form})


@login_required
def logout_view(request):
    """
    Vista para manejar el cierre de sesión.
    """
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente.")
    return redirect('/') # Redirigir a la página de inicio después de cerrar sesión

# --- Vistas para Farmacia ---

@login_required
def dashboard_farmacia(request):
    # Verifica si el usuario pertenece al grupo 'Farmacia'
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    
    if not is_farmacia:
        messages.warning(request, "No tienes permiso para acceder a este área de Farmacia.")
        return redirect('HomeSinInicio') # Redirige a un lugar seguro si no tiene permiso

    context = {
        'is_farmacia': is_farmacia,
    }

    return render(request, 'registration/dashboard_farmacia.html', context)









@login_required
def doctor_home_view(request):
    # --- Lógica para pasar las variables del Navbar ---
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    # Si el usuario NO es Doctora, lo redirigimos (medida de seguridad)
    if not is_doctora:
        # Aquí puedes redirigir a un home genérico si no es Doctora.
        # Por ejemplo, si es Farmacia, lo rediriges a su dashboard.
        if is_farmacia:
            return redirect('dashboard_farmacia')
        else:
            return redirect('HomeSinInicio')

    # --- Tu lógica para el Dashboard del Doctor ---
    ultimos_pacientes = Paciente.objects.filter(doctor_responsable__user=request.user).order_by('-fecha_registro')[:3]
    now = datetime.now() 
    today = date.today()

    citas_hoy_pendientes = Cita.objects.filter(
        doctor=request.user,
        fecha=today,
        hora_inicio__gte=now.time()
    ).count()

    proximas_citas = Cita.objects.filter(
        (Q(fecha=today) & Q(hora_inicio__gte=now.time())) | Q(fecha__gt=today),
        doctor=request.user
    ).order_by('fecha', 'hora_inicio')[:5]

    doctor_full_name = request.user.get_full_name()
    if not doctor_full_name and request.user.first_name:
        doctor_full_name = request.user.first_name
    if not doctor_full_name:
        doctor_full_name = request.user.username

    # --- Modificamos el Contexto para incluir las variables del Navbar ---
    context = {
        'doctor_name': request.user.first_name if request.user.first_name else request.user.username,
        'ultimos_pacientes': ultimos_pacientes, 
        'total_citas_hoy_pendientes': citas_hoy_pendientes,
        'proximas_citas': proximas_citas,
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    
    return render(request, 'doctor_home.html', context)










def recovery_request_view(request):
    """
    Vista para solicitar la recuperación de la cuenta.
    """
    if request.method == 'POST':
        form = RecoveryRequestForm(request.POST)
        if form.is_valid():
            user = form.user
            request.session['recovery_user_id'] = user.id
            messages.success(request, 'Usuario encontrado. Por favor, introduce tu NIP de recuperación.')
            return redirect('recovery_verify')
        else:
            # Si el formulario no es válido, se vuelve a renderizar la misma página
            # con los errores del formulario. No se redirige.
            messages.error(request, 'No se encontró un usuario con ese nombre de usuario o correo.')
            return render(request, 'registration/recovery_request.html', {'form': form})
    else:
        form = RecoveryRequestForm()
    
    return render(request, 'registration/recovery_request.html', {'form': form})


def recovery_verify_view(request):
    """
    Vista para verificar el NIP de recuperación.
    """
    user_id = request.session.get('recovery_user_id')
    if not user_id:
        messages.error(request, 'Ha ocurrido un error en el proceso de recuperación. Por favor, vuelve a intentarlo.')
        return redirect('recovery_request')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Usuario no válido. Vuelve a empezar el proceso.')
        return redirect('recovery_request')
    
    if request.method == 'POST':
        form = RecoveryVerifyForm(request.POST)
        if form.is_valid():
            nip_ingresado = form.cleaned_data.get('nip')
            if nip_ingresado == user.recovery_nip:
                messages.success(request, 'NIP verificado. Ahora puedes cambiar tu contraseña.')
                return redirect('recovery_password_reset')
            else:
                messages.error(request, 'NIP incorrecto. Por favor, inténtalo de nuevo.')
                # Si el NIP es incorrecto, se vuelve a renderizar la misma página con el error.
                return render(request, 'registration/recovery_verify.html', {'form': form})
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
            # Si el formulario no es válido, se vuelve a renderizar la misma página con los errores.
            return render(request, 'registration/recovery_verify.html', {'form': form})
    else:
        form = RecoveryVerifyForm()
    
    return render(request, 'registration/recovery_verify.html', {'form': form})


def recovery_password_reset_view(request):
    """
    Vista para restablecer la contraseña después de verificar el NIP.
    """
    # Verifica que el ID de usuario está en la sesión
    user_id = request.session.get('recovery_user_id')
    if not user_id:
        messages.error(request, 'Ha ocurrido un error en el proceso. Por favor, vuelve a intentarlo.')
        return redirect('recovery_request')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Usuario no válido. Vuelve a empezar el proceso.')
        return redirect('recovery_request')

    if request.method == 'POST':
        form = RecoveryPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data.get('new_password')
            user.set_password(new_password)
            user.save()
            
            # Limpia la sesión y notifica al usuario
            del request.session['recovery_user_id']
            messages.success(request, 'Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión.')
            return redirect('signin') # Asumiendo que 'signin' es la URL de tu login
        else:
            messages.error(request, 'Hubo un error al cambiar la contraseña. Verifica los datos.')
    else:
        form = RecoveryPasswordResetForm()

    return render(request, 'registration/recovery_password_reset.html', {'form': form})



# Modificación en Pacientes/views.py

@login_required
def Crear_Pacientes_view(request):
    user = request.user
    is_doctor = user.user_type == "doctor"
    is_farmacia = user.user_type == "farmacia"

    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)

            if is_doctor:
                # Asignar el doctor responsable si el usuario es un doctor
                try:
                    paciente.doctor_responsable = user.doctor_profile
                except Doctor.DoesNotExist:
                    messages.error(request, "Tu perfil de doctor no está completo. No se puede crear el paciente.")
                    return redirect("lista_pacientes") # O una página de error

            elif is_farmacia:
                # Asignar el doctor asociado al perfil de farmacia
                try:
                    farmacia_profile = user.farmacia_profile
                    paciente.doctor_responsable = farmacia_profile.doctor
                except FarmaciaProfile.DoesNotExist:
                    messages.error(request, "Tu perfil de farmacia no está completo. No se puede crear el paciente.")
                    return redirect("lista_pacientes") # O una página de error

            paciente.save()
            messages.success(request, "Paciente creado exitosamente.")
            return redirect("lista_pacientes")
        else:
            messages.error(request, "Hubo un error al crear el paciente.")
    else:
        form = PacienteForm()

    context = {
        "form": form,
        "is_doctor": is_doctor,
        "is_farmacia": is_farmacia,
    }
    return render(request, "CrearPaciente.html", context)






@login_required
def Lista_Pacientes_view(request):
    # Lógica para pasar las variables del Navbar
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    try:
        doctor_profile = request.user.doctor_profile
        pacientes = Paciente.objects.filter(doctor_responsable=doctor_profile).order_by('apellido_paterno', 'apellido_materno', 'nombre')
    except Doctor.DoesNotExist:
        pacientes = Paciente.objects.none()

    context = {
        'pacientes': pacientes,
        'is_farmacia': is_farmacia, # <-- AGREGADO
        'is_doctora': is_doctora, # <-- AGREGADO
    }
    return render(request, 'Pacientes.html', context)




@login_required
def editar_paciente_view(request, pk):
    # Lógica para pasar las variables del Navbar
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    paciente = get_object_or_404(Paciente, pk=pk)

    if request.method == 'POST':
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Paciente {paciente.nombre} actualizado exitosamente.')
            return redirect('lista_pacientes')
        else:
            messages.error(request, 'Hubo un error al actualizar el paciente. Por favor, revisa los datos.')
    else:
        form = PacienteForm(instance=paciente)

    context = {
        'form': form,
        'paciente': paciente,
        'is_farmacia': is_farmacia, # <-- AGREGADO
        'is_doctora': is_doctora, # <-- AGREGADO
    }
    return render(request, 'EditarPaciente.html', context)

# 2. Vista para ELIMINAR Paciente
@login_required
def eliminar_paciente_view(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    if request.method == 'POST':
        # Solo permite la eliminación si la petición es POST (más seguro)
        paciente_nombre = paciente.nombre # Guarda el nombre antes de eliminar para el mensaje
        paciente.delete()
        messages.success(request, f'Paciente {paciente_nombre} eliminado exitosamente.')
        return redirect('lista_pacientes') # Redirige a la lista después de eliminar
    
    # Si la petición no es POST (ej. alguien intenta acceder directamente a la URL GET),
    # podríamos redirigir o mostrar un error. Por simplicidad, solo aceptamos POST.
    # Opcionalmente, podrías renderizar una página de confirmación aquí si no usas el confirm JS.
    messages.error(request, 'Acceso inválido. Solo se permite la eliminación vía POST.')
    return redirect('lista_pacientes')

# Tu vista de registros
@login_required
def registros_paciente_view(request, pk):
    # Lógica para pasar las variables del Navbar
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    # --- INICIO DE LA LÓGICA DE RESTRICCIÓN (AQUÍ ESTÁ LA CORRECCIÓN) ---
    if is_farmacia:
        messages.error(request, "No tienes permiso para ver los expedientes de los pacientes.")
        return redirect('lista_pacientes') # O a la URL de inicio del dashboard
    # --- FIN DE LA LÓGICA DE RESTRICCIÓN ---

    paciente = get_object_or_404(Paciente, pk=pk)
    
    context = {
        'paciente': paciente,
        'is_farmacia': is_farmacia, # <-- AGREGADO
        'is_doctora': is_doctora, # <-- AGREGADO
    }
    return render(request, 'Expediente.html', context)

##################################################################################################################
#################################################################################################################
########################MODIFICACIONES 




# Las nuevas vistas para las historias clínicas y orden médica
@login_required
def historia_clinica_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinica = paciente.PacienteHistoriaClinica.all() # ¡Esta es la forma correcta! # Obtiene todas las historias clínicas del paciente

    context = { 'paciente': paciente, 'historia_clinica': historia_clinica }
    return render(request, 'historia_clinica.html', context) # Sin 'Pacientes/' si está directamente en templates/

@login_required
def historia_clinica_paciente_me(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinicaME = paciente.PacienteHistoriaClinicaME.all() # ¡Esta es la forma correcta! # Obtiene todas las historias clínicas del paciente

    context = { 'paciente': paciente, 'historia_clinicaME': historia_clinicaME }
    return render(request, 'historia_clinica_me.html', context) # Sin 'Pacientes/' si está directamente en templates/
####################################################
@login_required
def eliminar_historial_clinico_view(request, historia_pk):
    # Obtener el registro de la historia clínica o mostrar 404
    historia_clinica = get_object_or_404(HistoriaClinica, pk=historia_pk)
    
    # Obtener el paciente asociado para redirigir correctamente
    paciente_pk = historia_clinica.paciente.pk

    if request.method == 'POST':
        # Eliminar el registro
        historia_clinica.delete()
        messages.success(request, f'Registro de historial clínico (ID: {historia_pk}) eliminado exitosamente.')
    
    # Redirigir de vuelta a la historia clínica del paciente
    return redirect('historia_clinica_paciente', pk=paciente_pk)
@login_required
def eliminar_historial_clinico_me(request, pk):
    historia = get_object_or_404(HistoriaClinicaMusculoEsqueletico, pk=pk)
    
    # Guarda el pk del paciente para redirigir
    paciente_pk = historia.paciente.pk

    if request.method == 'POST':
        historia.delete()
        messages.success(request, 'Registro de historial clínico eliminado exitosamente.')
        # Redirige de vuelta a la página del historial del paciente
        return redirect('historia_clinica_paciente_me', pk=paciente_pk)
    
    messages.error(request, 'Método no permitido.')
    return redirect('historia_clinica_paciente_me', pk=paciente_pk)


class CuestionarioHistoriaClinicaWizard(SessionWizardView):
    def get_template_names(self):
        print(f"[Wizard] Paso actual: {self.steps.current}")
        return [TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step=None):
        # Aquí puedes pasar datos adicionales a tus formularios si los necesitas
        print(f"[Wizard] get_form_kwargs para step: {step}")
        return super().get_form_kwargs(step)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        # Puedes añadir contexto extra aquí, por ejemplo el nombre del paso actual
        context['step_title'] = self.steps.current
        print(f"[Wizard] get_context_data para step: {self.steps.current}")
        print(f"[Wizard] Form errors: {form.errors if form else 'No form'}")    
        return context

    def get_form_list(self):
        form_list = super().get_form_list()

        paciente_id = self.kwargs.get('paciente_id')
        if paciente_id:
            try:
                paciente = Paciente.objects.get(id=paciente_id)
                if paciente.genero == 'Masculino' and 'ginecologico' in form_list: # <-- ¡La corrección es aquí!
                    del form_list['ginecologico']
                    print(f"[Wizard] Omitiendo formulario ginecologico para paciente masculino")
            except Paciente.DoesNotExist:
                pass
        
        print(f"[Wizard] Form list: {list(form_list.keys())}")
        return form_list
        
    def done(self, form_list, **kwargs):
        form_data = {}
        for idx, form in enumerate(form_list):
            print(f"[Wizard] Formulario {idx} ({form.__class__.__name__}) cleaned_data: {form.cleaned_data}")
            print(f"[Wizard] Formulario {idx} errors: {form.errors}")
            form_data.update(form.cleaned_data)

        paciente_id = self.kwargs.get('paciente_id')
        paciente_obj = Paciente.objects.get(id=paciente_id) # Obtenemos el objeto Paciente

        print(f"[Wizard] Creando HistoriaClinica para paciente {paciente_id}")
        HistoriaClinica.objects.create(
            paciente=paciente_obj,
            no_historia_clinica="HC-" + str(paciente_id), # Ejemplo
            **form_data
        )

        # Pasamos el objeto paciente al contexto
        print(f"[Wizard] Renderizando cuestionario_completado.html")
        return render(self.request, 'cuestionario_completado.html', {'paciente': paciente_obj})
    ###########################################################################
# Pacientes/views.py
@login_required
def Resultados_Historial_Clinico(request, pk, historia_pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinica = get_object_or_404(HistoriaClinica, pk=historia_pk, paciente=paciente)

    context = {'paciente': paciente, 'historia_clinica': historia_clinica}
    return render(request, 'Resultados_Historial_Clinico.html', context)
@login_required
def Resultados_Historial_ClinicoME(request, pk, historia_pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinicaME = get_object_or_404(HistoriaClinicaMusculoEsqueletico, pk=historia_pk, paciente=paciente)

    context = {'paciente': paciente, 'historia_clinicaME': historia_clinicaME}
    return render(request, 'Resultados_Historial_ClinicoME.html', context)

FORM = []
#cONTROL MUSCULO ESQUELÉTICO
class CuestionarioMusculoEsqueleticoWizard(SessionWizardView):
    """
    Vista de formulario multi-paso para Historia Clínica Músculo Esquelética.
    """
    def get_template_names(self):
        return [TEMPLATES_ME[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        # Obtenemos el objeto paciente para pasarlo al template
        paciente_id = self.kwargs.get('paciente_id')
        context['paciente'] = get_object_or_404(Paciente, id=paciente_id)
        
        # Título para cada paso en la plantilla
        step_titles = {
            'parte_1': 'Datos de la Consulta',
            'parte_2': 'Antecedentes y Hábitos',
            'examen_fisico': 'Examen Físico'
        }
        context['step_title'] = step_titles.get(self.steps.current, 'Cuestionario')
        
        return context

    def done(self, form_list, **kwargs):
        # Combina los datos de todos los formularios
        form_data = {}
        for form in form_list:
            form_data.update(form.cleaned_data)
        
        # Obtiene el paciente y crea la instancia del modelo
        paciente_id = self.kwargs.get('paciente_id')
        paciente_obj = Paciente.objects.get(id=paciente_id)

        # Crea el objeto de HistoriaClinicaMusculoEsqueletico con los datos combinados
        HistoriaClinicaMusculoEsqueletico.objects.create(
            paciente=paciente_obj,
            **form_data
        )

        return render(self.request, 'cuestionario_completadoME.html', {'paciente': paciente_obj})

@login_required
def historia_clinica_musculo_esqueletico_paciente(request):
    pass

@login_required
def HistorialMusculoEsqueleticoPDF(request, pk, historia_pk):
    # Asegurarse de que el historial pertenece al paciente
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinicaME = get_object_or_404(HistoriaClinicaMusculoEsqueletico, pk=historia_pk, paciente=paciente) 

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Historial_Musculo_Esqueletico_{historia_clinicaME.fecha_registro.strftime("%Y-%m-%d_%H-%M-%S")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=portrait(A4),
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2.0 * cm, rightMargin=2.0 * cm)
    elements = []

    # --- Definir los estilos de texto y colores ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloPrincipal', fontSize=14, fontName='Helvetica-Bold', spaceAfter=15, alignment=TA_CENTER, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name='Subtitulo', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10, alignment=TA_CENTER, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name='TituloSeccion', fontSize=11, fontName='Helvetica-Bold', spaceAfter=8, textColor=colors.HexColor("#0050A1"), backColor=colors.HexColor("#EBF5FF"), leading=14, borderPadding=5, borderRadius=3))
    styles.add(ParagraphStyle(name='Etiqueta', fontSize=10, fontName='Helvetica-Bold', leading=12, textColor=colors.HexColor("#333333")))
    styles.add(ParagraphStyle(name='Dato', fontSize=10, fontName='Helvetica', leading=12, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name='Lista', fontSize=10, fontName='Helvetica', leftIndent=12, leading=12, textColor=colors.HexColor("#666666")))
    
    # --- Función para agregar la marca de agua ---
    def add_watermark(canvas, doc):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            page_width, page_height = portrait(A4)
            img_width = 15 * cm
            img_height = 12 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.saveState()
            canvas.setFillAlpha(0.2)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()

    # Asignar la función de marca de agua
    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark

    # --- Contenido del PDF ---
    
    # 1. Logos y Título del Encabezado
    logo1_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo2_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'Uni.jpge')

    logo1 = Image(logo1_path, width=3 * cm, height=1.5 * cm) if os.path.exists(logo1_path) else Paragraph("", styles['Normal'])
    logo2 = Image(logo2_path, width=3 * cm, height=2.5 * cm) if os.path.exists(logo2_path) else Paragraph("", styles['Normal'])

    encabezado_data = [
        [logo1, Paragraph("<b>Dra. Jaqueline Vásquez Gómez<br/>Cédula Profesional: 11708282<br/>Prolongación Emiliano Zapata Sn. Bo. de la luz<br/>Santiago Cuautlalpan Edo. de Mex.</b>", styles['Subtitulo']), logo2]
    ]
    encabezado_table = Table(encabezado_data, colWidths=[3*cm, 10.5*cm, 3*cm])
    encabezado_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    elements.append(encabezado_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Título principal del documento
    elements.append(Paragraph("<b>RESULTADO DEL HISTORIAL CLÍNICO MÚSCULO ESQUELÉTICA</b>", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.5 * cm))

    # --- Función para crear secciones en recuadros ---
    def crear_seccion_recuadro(titulo, datos_dict):
        # Título de la sección
        elements.append(Paragraph(titulo, styles['TituloSeccion']))
        
        # Tabla para los datos dentro del recuadro
        table_data = []
        for etiqueta, dato in datos_dict.items():
            if isinstance(dato, list):
                if dato:
                    table_data.append([
                        Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                        ListFlowable([ListItem(Paragraph(item, styles['Dato']), bulletKind='bullet') for item in dato], bulletKind='bullet')
                    ])
                else:
                    table_data.append([
                        Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                        Paragraph("No especificado", styles['Dato'])
                    ])
            else:
                table_data.append([
                    Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                    Paragraph(f"{dato}", styles['Dato'])
                ])
        
        # Estilo de la tabla con color de fondo
        section_table = Table(table_data, colWidths=[6*cm, None])
        section_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F9F9F9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(section_table)
        elements.append(Spacer(1, 0.5 * cm))
        return elements

    # --- Secciones del PDF:, respetando el orden de tu HTML ---

    # 1. Información del Paciente
    datos_paciente = {
        "Nombre": f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno or ''}",
        "Fecha de nacimiento": f"{paciente.fecha_nacimiento}",
        "Género": f"{paciente.genero}",
        "Motivo de consulta": f"{historia_clinicaME.motivo_consulta}",
        "Comentarios": f"{historia_clinicaME.comentarios}",
        "Fecha de registro": f"{historia_clinicaME.fecha_registro}",
    }
    crear_seccion_recuadro("Información del Paciente", datos_paciente)

    # 2. Datos Generales y Vivienda
    datos_generales = {
        "Grado de instrucción": historia_clinicaME.GradoInstruccion,
        "Inmunizaciones o vacunas": historia_clinicaME.inmunizaciones_o_vacunas,
        "Baño diario": historia_clinicaME.baño_diario,
        "Aseo dental": historia_clinicaME.aseo_dental,
        "Lavado de manos antes de comer": historia_clinicaME.lavado_manos_antes_comer,
        "Lavado de manos después": historia_clinicaME.lavado_manos_despues,
        "Tamaño de vivienda": historia_clinicaME.tamanio_vivienda,
        "Tipo de vivienda": historia_clinicaME.tipo_vivienda,
        "Servicios con los que cuenta la vivienda": historia_clinicaME.servicio_vivienda,
    }
    crear_seccion_recuadro("Datos Generales y Vivienda", datos_generales)

    # 3. Hábitos y patologías (divididos en subsecciones)
    elements.append(Paragraph("Hábitos y Patologías", styles['TituloSeccion']))
    
    # Subsección: Antecedentes
    datos_antecedentes = {
        "Enfermedad actual": historia_clinicaME.enfermedad_actual,
        "Antecedentes familiares": historia_clinicaME.Antecedentes_familiares,
    }
    crear_seccion_recuadro("Antecedentes", datos_antecedentes)

    # Subsección: Hábitos tóxicos
    datos_habitos_toxicos = {
        "Hábitos tóxicos": historia_clinicaME.habitos_toxicos,
    }
    crear_seccion_recuadro("Hábitos tóxicos", datos_habitos_toxicos)

    # Subsección: Fisiológicos
    # Corregí el nombre del campo para 'Alimentación'
    datos_fisiologicos = {
        "Alimentación": historia_clinicaME.Allimentación,
        "Ingesta de agua": f"{historia_clinicaME.Ingesta_Agua} litros",
        "Cantidad de veces que orina": f"{historia_clinicaME.Cantidad_veces_Orina} veces",
        "Catarsis": historia_clinicaME.Catarsis,
        "Somnia": historia_clinicaME.Somnia,
    }
    crear_seccion_recuadro("Fisiológicos", datos_fisiologicos)
    
    # Subsección: Patológicos
    # Corregí el nombre del campo para 'Otro' y lo puse en singular
    datos_patologicos = {
        "Infancia": historia_clinicaME.Infancia,
        "Adulto": historia_clinicaME.Adulto,
        "Patologías": historia_clinicaME.Patologias,
        "Ha sido operado": historia_clinicaME.ha_sido_operado,
        "Fecha de operación": historia_clinicaME.fecha_operacion,
        "Traumatismo o fractura": historia_clinicaME.traumatismo_o_fractura,
        "Otros antecedentes": historia_clinicaME.Otro,
    }
    crear_seccion_recuadro("Patológicos", datos_patologicos)

    # 4. Sección "Examen Físico"
    datos_examen_fisico = {
        "Constitucional": historia_clinicaME.Constitucional,
        "Marcha": historia_clinicaME.Marcha,
        "Actitud": historia_clinicaME.Actitud,
        "Ubicacion": historia_clinicaME.Ubicacion,
        "Impresion general": historia_clinicaME.Impresion_general,
        
        "Frecuencia Cardiaca": historia_clinicaME.FC,
        "Tensión Arterial": historia_clinicaME.TA,
        "Frecuencia Respiratoria": historia_clinicaME.FR,
        "Temperatura Auxiliar": historia_clinicaME.T_Auxiliar,
        "Temperatura Rectal": historia_clinicaME.T_rectal,
        "Peso Habitual": historia_clinicaME.Peso_Habitual,
        "Peso Actual": historia_clinicaME.Peso_Actual,
        "Talla": historia_clinicaME.Talla,
        "Índice de Masa Corporal": historia_clinicaME.IMC,
        
        "Aspecto": historia_clinicaME.Aspecto,
        "Distribución pilosa": historia_clinicaME.Distribuición_pilosa,
        "Lesiones": historia_clinicaME.Lesiones,
        "Faneras": historia_clinicaME.Faneras,
        "Tejido celular subcutáneo": historia_clinicaME.Tejido_celular_subcutaneo,
        "Tejido celular": historia_clinicaME.Tejido_celular, # Este campo es una lista
    }
    crear_seccion_recuadro("Examen Físico", datos_examen_fisico)

    # --- Construimos el PDF final ---
    doc.build(elements)
    
    return response


@login_required
def HistorialClinicoPDF(request, pk, historia_pk):
    # Asegurarse de que el historial pertenece al paciente
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinica = get_object_or_404(HistoriaClinica, pk=historia_pk, paciente=paciente) 

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Historial_Clinico_{historia_clinica.fecha_registro.strftime("%Y-%m-%d_%H-%M-%S")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=portrait(A4),
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2.0 * cm, rightMargin=2.0 * cm)
    elements = []

    # --- Definir los estilos de texto y colores ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloPrincipal', fontSize=14, fontName='Helvetica-Bold', spaceAfter=15, alignment=TA_CENTER, textColor=colors.HexColor("#003366")))
    styles.add(ParagraphStyle(name='Subtitulo', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10, alignment=TA_CENTER, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name='TituloSeccion', fontSize=11, fontName='Helvetica-Bold', spaceAfter=8, textColor=colors.HexColor("#0050A1"), backColor=colors.HexColor("#EBF5FF"), leading=14, borderPadding=5, borderRadius=3))
    styles.add(ParagraphStyle(name='Etiqueta', fontSize=10, fontName='Helvetica-Bold', leading=10, textColor=colors.HexColor("#333333")))
    styles.add(ParagraphStyle(name='Dato', fontSize=10, fontName='Helvetica', leading=10, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name='Lista', fontSize=10, fontName='Helvetica', leftIndent=10, leading=12, textColor=colors.HexColor("#666666")))
    
    # --- Función para agregar la marca de agua ---
    def add_watermark(canvas, doc):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            page_width, page_height = portrait(A4)
            img_width = 15 * cm
            img_height = 12 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.saveState()
            canvas.setFillAlpha(0.2)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()

    # Asignar la función de marca de agua
    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark

    # --- Contenido del PDF ---
    
    # 1. Logos y Título del Encabezado
    logo1_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo2_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'Uni.jpge')

    logo1 = Image(logo1_path, width=3 * cm, height=1.5 * cm) if os.path.exists(logo1_path) else Paragraph("", styles['Normal'])
    logo2 = Image(logo2_path, width=3 * cm, height=2.5 * cm) if os.path.exists(logo2_path) else Paragraph("", styles['Normal'])

    encabezado_data = [
        [logo1, Paragraph("<b>Dra. Jaqueline Vásquez Gómez<br/>Cédula Profesional: 11708282<br/>Prolongación Emiliano Zapata Sn. Bo. de la luz<br/>Santiago Cuautlalpan Edo. de Mex.</b>", styles['Subtitulo']), logo2]
    ]
    encabezado_table = Table(encabezado_data, colWidths=[3*cm, 10.5*cm, 3*cm])
    encabezado_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    elements.append(encabezado_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Título principal del documento
    elements.append(Paragraph("<b>RESULTADO DEL HISTORIAL CLÍNICO</b>", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.5 * cm))

    # --- Función para crear secciones en recuadros ---
    def crear_seccion_recuadro(titulo, datos_dict):
        # Título de la sección
        elements.append(Paragraph(titulo, styles['TituloSeccion']))
        
        # Tabla para los datos dentro del recuadro
        table_data = []
        for etiqueta, dato in datos_dict.items():
            if isinstance(dato, list):
                if dato:
                    table_data.append([
                        Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                        ListFlowable([ListItem(Paragraph(item, styles['Dato']), bulletKind='bullet') for item in dato], bulletKind='bullet')
                    ])
                else:
                    table_data.append([
                        Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                        Paragraph("No especificado", styles['Dato'])
                    ])
            else:
                table_data.append([
                    Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                    Paragraph(f"{dato}", styles['Dato'])
                ])
        
        # Estilo de la tabla con color de fondo
        section_table = Table(table_data, colWidths=[6*cm, None])
        section_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F9F9F9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(section_table)
        elements.append(Spacer(1, 0.5 * cm))
        return elements

    # --- Secciones del PDF, respetando el orden de tu HTML ---
###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR
    # 1. Información del Paciente
    datos_paciente = {
        "Nombre": f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno or ''}",
        "Fecha de nacimiento": f"{paciente.fecha_nacimiento}",
        "Género": f"{paciente.genero}",
        "Motivo de consulta": f"{historia_clinica.motivo_consulta}",
        "Comentarios": f"{historia_clinica.comentarios}",
        "Fecha de registro": f"{historia_clinica.fecha_registro}",
    }
    crear_seccion_recuadro("Información del Paciente", datos_paciente)

    # 2. Datos Generales y Vivienda
    datos_generales = {
        "Grado de instrucción": historia_clinica.GradoInstruccion,
        "Inmunizaciones o vacunas": historia_clinica.inmunizaciones_o_vacunas,
        "Baño diario": historia_clinica.baño_diario,
        "Aseo dental": historia_clinica.aseo_dental,
        "Lavado de manos antes de comer": historia_clinica.lavado_manos_antes_comer,
        "Lavado de manos después": historia_clinica.lavado_manos_despues,
        "Tamaño de vivienda": historia_clinica.tamanio_vivienda,
        "Tipo de vivienda": historia_clinica.tipo_vivienda,
        "Servicios con los que cuenta la vivienda": historia_clinica.servicio_vivienda,
        "Enfermedad actual": historia_clinica.enfermedad_actual,
        "Antecedentes familiares": historia_clinica.Antecedentes_familiares,
    }
    crear_seccion_recuadro("Datos Generales y Vivienda", datos_generales)

    # 3. Hábitos tóxicos, fisiológicos y patológicos
    elements.append(Paragraph("Hábitos, Fisiológicos y Patológicos", styles['TituloSeccion']))
    
    # Subsección: Hábitos tóxicos
    datos_habitos_toxicos = {
        "Hábitos tóxicos": historia_clinica.habitos_toxicos,
    }
    crear_seccion_recuadro("Hábitos tóxicos", datos_habitos_toxicos)

    # Subsección: Fisiológicos
    datos_fisiologicos = {
        "Alimentación": historia_clinica.Allimentación,
        "Ingesta de agua": f"{historia_clinica.Ingesta_Agua} litros",
        "Cantidad de veces que orina": f"{historia_clinica.Cantidad_veces_Orina} veces",
        "Catarsis": historia_clinica.Catarsis,
        "Somnia": historia_clinica.Somnia,
    }
    crear_seccion_recuadro("Fisiológicos", datos_fisiologicos)
    
    # Subsección: Patológicos
    datos_patologicos = {
        "Infancia": historia_clinica.Infancia,
        "Adulto": historia_clinica.Adulto,
        "Patologías": historia_clinica.Patologias,
        "Ha sido operado": historia_clinica.ha_sido_operado,
        "Fecha de operación": historia_clinica.fecha_operacion,
        "Traumatismo o fractura": historia_clinica.traumatismo_o_fractura,
        "Otros antecedentes": historia_clinica.Otro,
    }
    crear_seccion_recuadro("Patológicos", datos_patologicos)
 # 4. Cuestionario Gineco-Obstetricos
    datos_ginecologicos = {
        "FUM (Fecha de última menstruación)": historia_clinica.fum,
        "FPP (Fecha probable de parto)": historia_clinica.fpp,
        "Edad gestacional": f"{historia_clinica.edad_gestacional} semanas",
        "Menarquia": f"{historia_clinica.menarquia} años",
        "Ritmo menstrual": historia_clinica.rm_rit_menstr,
        "IRS (Inicio de relaciones sexuales)": historia_clinica.irs,
        "Número de parejas": historia_clinica.no_de_parejas,
        "Flujo genital": historia_clinica.flujo_genital,
        "Gestas": historia_clinica.gestas,
        "Partos": historia_clinica.partos,
        "Cesáreas": historia_clinica.cesareas,
        "Abortos": historia_clinica.abortos,
        "Anticonceptivos": historia_clinica.anticonceptivos,
        "Tipo de anticonceptivos": historia_clinica.anticonceptivos_tipo,
        "Tiempo de uso": historia_clinica.anticonceptivos_tiempo,
        "Última toma de anticonceptivos": historia_clinica.anticonceptivos_ultima_toma,
        "Cirugía ginecológica": historia_clinica.cirugia_ginecologica,
        "Otros ginecológicos": historia_clinica.otros_ginecologicos,
    }
    crear_seccion_recuadro("Cuestionario Gineco-Obstetricos", datos_ginecologicos)
    elements.append(PageBreak())
    ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, SUBTITULO: INTERROGATORIO POR APARATOS Y SISTEMAS
    # 5. Cuestionario del Sistema Digestivo
    datos_digestivo = {
        "Halitosis": "Sí" if historia_clinica.digest_halitosis else "No",
        "Boca seca": "Sí" if historia_clinica.digest_boca_seca else "No",
        "Dificultad para masticar": "Sí" if historia_clinica.digest_masticacion else "No",
        "Disfagia (dificultad para tragar)": "Sí" if historia_clinica.digest_disfagia else "No",
        "Pirosis (acidez estomacal)": "Sí" if historia_clinica.digest_pirosis else "No",
        "Náuseas": "Sí" if historia_clinica.digest_nausea else "No",
        "Vómito o hematemesis (vómito con sangre)": "Sí" if historia_clinica.digest_vomito_hematemesis else "No",
        "Cólicos": "Sí" if historia_clinica.digest_colicos else "No",
        "Dolor abdominal": "Sí" if historia_clinica.digest_dolor_abdominal else "No",
        "Meteorismo (gases)": "Sí" if historia_clinica.digest_meteorismo else "No",
        "Flatulencias": "Sí" if historia_clinica.digest_flatulencias else "No",
        "Constipación (estreñimiento)": "Sí" if historia_clinica.digest_constipacion else "No",
        "Diarrea": "Sí" if historia_clinica.digest_diarrea else "No",
        "Rectorragias (sangrado rectal)": "Sí" if historia_clinica.digest_rectorragias else "No",
        "Melenas (heces negras)": "Sí" if historia_clinica.digest_melenas else "No",
        "Pujo": "Sí" if historia_clinica.digest_pujo else "No",
        "Tenesmo": "Sí" if historia_clinica.digest_tenesmo else "No",
        "Ictericia (piel amarillenta)": "Sí" if historia_clinica.digest_ictericia else "No",
        "Coluria (orina oscura)": "Sí" if historia_clinica.digest_coluria else "No",
        "Acolia (heces pálidas)": "Sí" if historia_clinica.digest_acolia else "No",
        "Prurito cutáneo (picazón en la piel)": "Sí" if historia_clinica.digest_prurito_cutaneo else "No",
        "Hemorragias": "Sí" if historia_clinica.digest_hemorragias else "No",
        "Prurito anal (picazón anal)": "Sí" if historia_clinica.digest_prurito_anal else "No",
        "Hemorroides": "Sí" if historia_clinica.digest_hemorroides else "No",
        #Comentarios_digestivo
        'Comentarios': historia_clinica.Comentarios_digestivo
    }
    crear_seccion_recuadro("Cuestionario del Sistema Digestivo", datos_digestivo)

    # 6. Cuestionario del Sistema Cardiovascular (Pulsos)
    elements.append(Paragraph("Cuestionario del Sistema Cardiovascular", styles['TituloSeccion']))
    elements.append(Paragraph("<b>Pulsos</b>", styles['Subtitulo']))
    
    pulso_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Derecho</b>", styles['Etiqueta']), Paragraph("<b>Izquierdo</b>", styles['Etiqueta'])],
        [Paragraph("<b>Pulso Carotídeo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_carotideo_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_carotideo_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Humeral</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_humeral_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_humeral_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Radial</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_radial_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_radial_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Femoral</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_femoral_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_femoral_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Poplíteo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_popliteo_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_popliteo_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Tibial Posterior</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_tibial_posterior_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_tibial_posterior_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pulso Pedio</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_pedio_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_pedio_izquierdo}", styles['Dato'])],
    ]
    
    pulso_table = Table(pulso_data, colWidths=[6*cm, None, None])
    pulso_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")), # Color de fondo del encabezado
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")), # Color del texto del encabezado
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pulso_table)
    elements.append(Spacer(1, 0.5 * cm)) 

    # 7. Cuestionario del Sistema Respiratorio
    datos_respiratorio = {
        "Tos": "Sí" if historia_clinica.resp_tos else "No",
        "Disnea (dificultad para respirar)": "Sí" if historia_clinica.resp_disnea else "No",
        "Dolor torácico": "Sí" if historia_clinica.resp_dolor_toracico else "No",
        "Hemoptisis (sangre al toser)": "Sí" if historia_clinica.resp_hemoptisis else "No",
        "Cianosis": "Sí" if historia_clinica.resp_cianosis else "No",
        "Vómica (expulsión de pus al toser)": "Sí" if historia_clinica.resp_vomica else "No",
        "Alteraciones de la voz": "Sí" if historia_clinica.resp_alteraciones_voz else "No",
    }
    crear_seccion_recuadro("Cuestionario del Sistema Respiratorio", datos_respiratorio)
    
    # 8. Cuestionario Genital y Urinario
    elements.append(Paragraph("Cuestionario Genital y Urinario", styles['TituloSeccion']))
    
    # Subsección: Genital
    datos_genital = {
        "Criptorquidea": "Sí" if historia_clinica.genital_criptorquidea else "No",
        "Fimosis": "Sí" if historia_clinica.genital_fimosis else "No",
        "Función sexual": "Sí" if historia_clinica.genital_funcion_sexual else "No",
        "Sangrado genital": "Sí" if historia_clinica.genital_sangrado_genital else "No",
        "Flujo o leucorrea": "Sí" if historia_clinica.genital_flujo_leucorrea else "No",
        "Dolor ginecológico": "Sí" if historia_clinica.genital_dolor_ginecologico else "No",
        "Prurito vulvar": "Sí" if historia_clinica.genital_prurito_vulvar else "No",
        #Comentarios_genital
        "Comentarios": historia_clinica.Comentarios_genital
    }
    crear_seccion_recuadro("Genital", datos_genital)
    
    # Subsección: Urinario  
    # Subsección: Urinario (cambios aplicados aquí)
    elements.append(Paragraph("Urinario", styles['TituloSeccion']))
    
    datos_alteraciones_miccion = {
        "Poliuria": "Sí" if historia_clinica.Poliuria else "No",
        "Anuria": "Sí" if historia_clinica.Anuria else "No",
        "Oliguria": "Sí" if historia_clinica.Oliguria else "No",
        "Nicturia": "Sí" if historia_clinica.Nicturia else "No",
        "Opsuria": "Sí" if historia_clinica.Opsuria else "No",
        "Disuria": "Sí" if historia_clinica.Disuria else "No",
        "Tenesmo vesical": "Sí" if historia_clinica.Tenesmo_vesical else "No",
        "Urgencia": "Sí" if historia_clinica.Urgencia else "No",
        "Chorro": "Sí" if historia_clinica.Chorro else "No",
        "Enuresis": "Sí" if historia_clinica.Enuresis else "No",
        "Incontinencia": "Sí" if historia_clinica.Incontinencia else "No",
        "Ninguna": "Sí" if historia_clinica.Ninguna else "No",
    }
    crear_seccion_recuadro("Alteraciones de la Micción", datos_alteraciones_miccion)
    
    datos_caracteristicas_orina = {
        "Volumen de la orina": historia_clinica.urin_volumen_orina,
        "Color de la orina": historia_clinica.urin_color_orina,
        "Olor de la orina": historia_clinica.urin_olor_orina,
        "Aspecto de la orina": historia_clinica.urin_aspecto_orina,
        "Dolor lumbar": "Sí" if historia_clinica.urin_dolor_lumbar else "No",
        "Edema palpebral superior": "Sí" if historia_clinica.urin_edema_palpebral_sup else "No",
        "Edema palpebral inferior": "Sí" if historia_clinica.urin_edema_palpebral_inf else "No",
        "Edema renal": "Sí" if historia_clinica.urin_edema_renal else "No",
        "Hipertensión arterial": "Sí" if historia_clinica.urin_hipertension_arterial else "No",
        "Datos clínicos de anemia": "Sí" if historia_clinica.urin_datos_clinicos_anemia else "No",
        "Comentarios": historia_clinica.Comentarios_urinario
    }
    crear_seccion_recuadro("Características de la Orina", datos_caracteristicas_orina)
    
    # 9. Cuestionario Endocrino y de Cuello
    elements.append(Paragraph("Cuestionario Endocrino y de Cuello", styles['TituloSeccion']))
    
    # Subsección: Hematológico
    # Subsección: Hematológico (corregida)
    datos_hematologico = {
        "Palidez": historia_clinica.Palidez,
        "Astenia": historia_clinica.Astenia,
        "Adinamia": historia_clinica.Adinamia,
        "Otros": historia_clinica.Otros,
        "Hemorragias": "Sí" if historia_clinica.hemato_hemorragias else "No",
        "Adenopatías": "Sí" if historia_clinica.hemato_adenopatias else "No",
        "Esplenomegalia": "Sí" if historia_clinica.hemato_esplenomegalia else "No",
        "Comentarios": historia_clinica.Comentarios_anemia,
 
    }
    crear_seccion_recuadro("Hematológico", datos_hematologico)
    
    # Subsección: Endocrino
    datos_endocrino = {
        "Bocio": "Sí" if historia_clinica.endocr_bocio else "No",
        "Letargia": "Sí" if historia_clinica.endocr_letargia else "No",
        "Bradipsiquia (lentitud de ideas)": "Sí" if historia_clinica.endocr_bradipsiquia_idia else "No",
        "Intolerancia al calor o frío": "Sí" if historia_clinica.endocr_intolerancia_calor_frio else "No",
        "Nerviosismo": "Sí" if historia_clinica.endocr_nerviosismo else "No",
        "Hiperquinesis (movimiento excesivo)": "Sí" if historia_clinica.endocr_hiperquinesis else "No",
        "Caracteres sexuales": "Sí" if historia_clinica.endocr_caracteres_sexuales else "No",
        "Galactorrea": "Sí" if historia_clinica.endocr_galactorrea else "No",
        "Amenorrea": "Sí" if historia_clinica.endocr_amenorrea else "No",
        "Ginecomastia": "Sí" if historia_clinica.endocr_ginecomastia else "No",
        "Obesidad": "Sí" if historia_clinica.endocr_obesidad else "No",
        "Ruborización": "Sí" if historia_clinica.endocr_ruborizacion else "No",
        "Comentarios": historia_clinica.Comentarios_endocrino
    }
    crear_seccion_recuadro("Endocrino", datos_endocrino)

    # 10. Exploración de Cuello
    elements.append(Paragraph("Exploración de Cuello", styles['TituloSeccion']))
    cuello_data = [
        [Paragraph("<b>Característica</b>", styles['Etiqueta']), Paragraph("<b>Hallazgos</b>", styles['Etiqueta'])],
        [Paragraph("<b>Tiroides</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.cuello_tiroides}", styles['Dato'])],
        [Paragraph("<b>Músculos</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.cuello_musculos}", styles['Dato'])],
        [Paragraph("<b>Ganglios Linfáticos</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.cuello_ganglios_linfaticos}", styles['Dato'])],
    ]
    cuello_table = Table(cuello_data, colWidths=[6*cm, None])
    cuello_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(cuello_table)
    elements.append(Spacer(1, 0.5 * cm))

    # --- NUEVAS SECCIONES ---
        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, SUBTITULO: EXPLORACIÓN FÍSICA: COLUMNA Y MIEMBROS SUPERIORES
    
    # 11. Exploración Física: Columna y Miembros Superiores
    elements.append(Paragraph("Exploración Física: Columna y Miembros Superiores", styles['TituloSeccion']))

    # Subsección: Columna Vertebral
    elements.append(Paragraph("<b>Columna Vertebral</b>", styles['Subtitulo']))
    columna_data = [
        [Paragraph("<b>Región</b>", styles['Etiqueta']), Paragraph("<b>Ascendente:</b>", styles['Etiqueta']), Paragraph("<b>Descendente:</b>", styles['Etiqueta']), Paragraph("<b>Observaciones:</b>", styles['Etiqueta'])],
        [Paragraph("<b>Cervical</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.ecv_cervical_asc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_cervical_desc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_cervical_obs}", styles['Dato'])],
        [Paragraph("<b>Dorsal</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.ecv_dorsal_asc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_dorsal_desc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_dorsal_obs}", styles['Dato'])],
        [Paragraph("<b>Lumbo Sacra</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.ecv_lumbosacra_asc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_lumbosacra_desc}", styles['Dato']), Paragraph(f"{historia_clinica.ecv_lumbosacra_obs}", styles['Dato'])],
    ]
    columna_table = Table(columna_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, None])
    columna_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(columna_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Miembros Superiores
    elements.append(Paragraph("<b>Miembros Superiores</b>", styles['Subtitulo']))
    miembros_superiores_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Hombros CS</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.mmss_hombros_cs_ad}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cs_ab}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cs_f}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cs_e}", styles['Dato'])],
        [Paragraph("<b>Hombros CV</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.mmss_hombros_cv_ad}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cv_ab}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cv_f}", styles['Dato']), Paragraph(f"{historia_clinica.mmss_hombros_cv_e}", styles['Dato'])],
    ]
    miembros_superiores_table = Table(miembros_superiores_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, None])
    miembros_superiores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(miembros_superiores_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación articular de MMSS Codo y Muñeca (agregada)
    elements.append(Paragraph("<b>Evaluación articular de MMSS Codo y Muñeca</b>", styles['Subtitulo']))
    articular_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Pronación (P)</b>", styles['Etiqueta']), Paragraph("<b>Supinación (S)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Codo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_codo_e}", styles['Dato']), Paragraph(f"{historia_clinica.art_codo_f}", styles['Dato']), Paragraph("", styles['Dato']), Paragraph("", styles['Dato'])],
        [Paragraph("<b>Muñeca</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_muneca_e}", styles['Dato']), Paragraph(f"{historia_clinica.art_muneca_f}", styles['Dato']), Paragraph(f"{historia_clinica.art_muneca_p}", styles['Dato']), Paragraph(f"{historia_clinica.art_muneca_s}", styles['Dato'])],
    ]
    articular_table = Table(articular_data, colWidths=[2.5*cm, 3*cm, 3*cm, 3*cm, None])
    articular_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(articular_table)
    elements.append(Spacer(1, 0.5 * cm))
    # Subsección: Evaluación articular de MMSS del pulgar
    # Agrupamos el título y la tabla para evitar la separación de página.
    # Subsección: Evaluación articular de MMSS del pulgar
    elements.append(Paragraph("<b>Evaluación articular de MMSS del pulgar</b>", styles['Subtitulo']))
    pulgar_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Pulgar</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_pulgar_ab}", styles['Dato']), Paragraph(f"{historia_clinica.art_pulgar_ad}", styles['Dato']), Paragraph(f"{historia_clinica.art_pulgar_e}", styles['Dato']), Paragraph(f"{historia_clinica.art_pulgar_f}", styles['Dato'])],
    ]
    pulgar_table = Table(pulgar_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, None])
    pulgar_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pulgar_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación articular de MMSS Dedos
    elements.append(Paragraph("<b>Evaluación articular de MMSS Dedos</b>", styles['Subtitulo']))
    dedos_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>IFP</b>", styles['Etiqueta'])],
        [Paragraph("<b>Dedos</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_dedos_f}", styles['Dato']), Paragraph(f"{historia_clinica.art_dedos_e}", styles['Dato']), Paragraph(f"{historia_clinica.art_dedos_ifp}", styles['Dato'])],
    ]
    dedos_table = Table(dedos_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, None])
    dedos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(dedos_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Nueva Sección: Exploración Física: Miembros Inferiores y Nariz
    elements.append(Paragraph("<b>Exploración Física: Miembros Inferiores y Nariz</b>", styles['TituloSeccion']))

    # Subsección: Articulaciones de Miembros Inferiores
    elements.append(Paragraph("<b>Articulaciones de Miembros Inferiores</b>", styles['Subtitulo']))
    cadera_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Cadera</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_cadera_ab}", styles['Dato']), Paragraph(f"{historia_clinica.art_cadera_ad}", styles['Dato']), Paragraph(f"{historia_clinica.art_cadera_f}", styles['Dato']), Paragraph(f"{historia_clinica.art_cadera_e}", styles['Dato'])],
    ]
    cadera_table = Table(cadera_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, None])
    cadera_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(cadera_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación articular del Tobillo
    elements.append(Paragraph("<b>Evaluación articular del Tobillo</b>", styles['Subtitulo']))
    tobillo_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Tobillo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_tobillo_f}", styles['Dato']), Paragraph(f"{historia_clinica.art_tobillo_e}", styles['Dato'])],
    ]
    tobillo_table = Table(tobillo_data, colWidths=[2.5*cm, 3*cm, None])
    tobillo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(tobillo_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación articular MMII Subastragalina
    elements.append(Paragraph("<b>Evaluación articular MMII Subastragalina</b>", styles['Subtitulo']))
    subastragalina_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Inversión (I)</b>", styles['Etiqueta']), Paragraph("<b>Eversión (EV)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Subastragalina</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.art_subastragalina_f}", styles['Dato']), Paragraph(f"{historia_clinica.art_subastragalina_ev}", styles['Dato'])],
    ]
    subastragalina_table = Table(subastragalina_data, colWidths=[2.5*cm, 3*cm, None])
    subastragalina_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(subastragalina_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Exploración de la cavidad nasal
    elements.append(Paragraph("<b>Exploración de la cavidad nasal</b>", styles['Subtitulo']))
    nasal_data = [
        [Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Mucosa</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.nasal_mucosa}", styles['Dato'])],
        [Paragraph("<b>Cornetes</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.nasal_cochas}", styles['Dato'])],
        [Paragraph("<b>Vascularización</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.nasal_vascularizacion}", styles['Dato'])],
    ]
    nasal_table = Table(nasal_data, colWidths=[4*cm, None])
    nasal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(nasal_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(PageBreak())
        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, SUBTITULO: EXPLORACIÓN FÍSICA: PULSOS Y CONCIENCIA
        # 12. Exploración Física: Pulsos y Conciencia
    elements.append(Paragraph("Exploración Física: Pulsos y Conciencia", styles['TituloSeccion']))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Pulsos
    pulso_data = [
        [Paragraph("<b>Tipo de pulso</b>", styles['Etiqueta']), Paragraph("<b>Derecho</b>", styles['Etiqueta']), Paragraph("<b>Izquierdo</b>", styles['Etiqueta'])],
        [Paragraph("<b>Carotídeo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_carotideo_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_carotideo_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Humeral</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_humeral_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_humeral_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Radial</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_radial_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_radial_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Femoral</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_femoral_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_femoral_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Poplíteo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_popliteo_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_popliteo_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Tibial Posterior</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_tibial_posterior_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_tibial_posterior_izquierdo}", styles['Dato'])],
        [Paragraph("<b>Pedio</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.me_pulso_pedio_derecho}", styles['Dato']), Paragraph(f"{historia_clinica.me_pulso_pedio_izquierdo}", styles['Dato'])],
    ]
    pulso_table = Table(pulso_data, colWidths=[6*cm, None, None])
    pulso_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pulso_table)
    elements.append(Spacer(1, 0.5 * cm))
    # Subsección: Otros
    datos_otros = {
        "Ascitis": "Sí" if historia_clinica.ascitis else "No",
        "Estado de Conciencia": historia_clinica.Estado_Conciencia,
    }
    crear_seccion_recuadro("Otros", datos_otros)
    elements.append(Spacer(1, 0.5 * cm))
    
        # 13. Cuestionario Glasgow y Visual
    elements.append(Paragraph("Cuestionario Glasgow y Visual", styles['TituloSeccion']))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Escala de Glasgow
    elements.append(Paragraph("<b>Escala de Glasgow</b>", styles['Subtitulo']))
    glasgow_data = [
        [Paragraph("<b>Prueba</b>", styles['Etiqueta']), Paragraph("<b>Respuesta</b>", styles['Etiqueta']), Paragraph("<b>Puntuación</b>", styles['Etiqueta'])],
        [Paragraph("<b>Apertura de Ojos</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.glasgow_apertura_ojos_respuesta}", styles['Dato']), Paragraph(f"{historia_clinica.glasgow_apertura_ojos_puntuacion}", styles['Dato'])],
        [Paragraph("<b>Respuesta Verbal</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.glasgow_respuesta_verbal_respuesta}", styles['Dato']), Paragraph(f"{historia_clinica.glasgow_respuesta_verbal_puntuacion}", styles['Dato'])],
        [Paragraph("<b>Respuesta Motora</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.glasgow_respuesta_motora_respuesta}", styles['Dato']), Paragraph(f"{historia_clinica.glasgow_respuesta_motora_puntuacion}", styles['Dato'])],
    ]
    glasgow_table = Table(glasgow_data, colWidths=[5*cm, 6*cm, None])
    glasgow_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(glasgow_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Reflejo Fotomotor
    elements.append(Paragraph("<b>Reflejo Fotomotor: (Reactividad Pupilar)</b>", styles['Subtitulo']))
    fotomotor_data = [
        [Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Según el tamaño</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.reflejo_fotomotor_tamano}", styles['Dato'])],
        [Paragraph("<b>Según relación entre ellas</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.reflejo_fotomotor_relaciones}", styles['Dato'])],
        [Paragraph("<b>Según respuesta a la luz</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.reflejo_fotomotor_respuestas_luz}", styles['Dato'])],
    ]
    fotomotor_table = Table(fotomotor_data, colWidths=[6*cm, None])
    fotomotor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(fotomotor_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Exploración de Pares Craneales
    elements.append(Paragraph("<b>Exploración de Pares Craneales</b>", styles['Subtitulo']))
    pares_craneales_data = [
        [Paragraph("<b>Par Craneal</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>III (Oculomotor)</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_iii_oculomotor}", styles['Dato'])],
        [Paragraph("<b>IV (Patético)</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_iv_patetico}", styles['Dato'])],
        [Paragraph("<b>VI (Motor Ocular Externo)</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_vi_motor_ocular_externo}", styles['Dato'])],
    ]
    pares_craneales_table = Table(pares_craneales_data, colWidths=[6*cm, None])
    pares_craneales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(pares_craneales_table)
    elements.append(Spacer(1, 0.5 * cm))

    # 14. Campos Visuales y Retina
    elements.append(Paragraph("Cuestionario Glasgow y Visual", styles['TituloSeccion']))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Campos Visuales (Pares Craneales)
    elements.append(Paragraph("<b>Campos Visuales</b>", styles['Subtitulo']))
    campos_visuales_data = [
        [Paragraph("<b>Par Craneal</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>III Oculomotor</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_iii_oculomotor_cv}", styles['Dato'])],
        [Paragraph("<b>IV Patético</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_iv_patetico_cv}", styles['Dato'])],
        [Paragraph("<b>VI Motor Ocular Externo</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.par_craneal_vi_motor_ocular_externo_cv}", styles['Dato'])],
    ]
    campos_visuales_table = Table(campos_visuales_data, colWidths=[6*cm, None])
    campos_visuales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(campos_visuales_table)
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación de la Retina
    elements.append(Paragraph("<b>Evaluación de la Retina</b>", styles['Subtitulo']))
    retina_data = [
        [Paragraph("<b>Aspecto de la Retina</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Relación Arterio-Venosa</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.retina_relacion_arterio_venosa}", styles['Dato'])],
        [Paragraph("<b>Mácula</b>", styles['Etiqueta']), Paragraph(f"{historia_clinica.retina_macula}", styles['Dato'])],
    ]
    retina_table = Table(retina_data, colWidths=[6*cm, None])
    retina_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(retina_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(PageBreak())

        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, SUBTITULO: EXPLORACIÓN FÍSICA FINAL

    # Subsección: Hallazgos en la Exploración Visual
# Subsección: Hallazgos en la Exploración Visual
    # Reflejos Osteo Tendinosos Profundos
    elements.append(Paragraph("<b>Reflejos Osteo Tendinosos Profundos</b>", styles['Subtitulo']))
    elements.append(Spacer(1, 0.5 * cm))

    # Lista de reflejos con sus nombres de campo en la base de datos
    reflejos_profundos = [
        ("Naso palpebral", historia_clinica.Naso_palpebral),
        ("Superciliar", historia_clinica.Superciliar),
        ("Maseterino", historia_clinica.Maseterino),
        ("Bicipital", historia_clinica.Bicipital),
        ("Estilo Radial", historia_clinica.Estilo_Radial),
        ("Tricipital", historia_clinica.Tricipital),
        ("Cúbito Pronador", historia_clinica.Cubito_Pronador),
        ("Medio Pubiano", historia_clinica.Medio_Pubiano),
        ("Rotuliano", historia_clinica.Rotuliano),
        
    ]

    # Encabezado de la tabla
    table_data_profundos = [
        [Paragraph("<b>Reflejo</b>", styles['Etiqueta']),
        Paragraph("<b>1</b>", styles['Etiqueta']),
        Paragraph("<b>2</b>", styles['Etiqueta']),
        Paragraph("<b>3</b>", styles['Etiqueta']),
        Paragraph("<b>4</b>", styles['Etiqueta'])
        ]
    ]

    # Rellenar la tabla
    for nombre_reflejo, valor_db in reflejos_profundos:
        fila_datos = [Paragraph(f"<b>{nombre_reflejo}</b>", styles['Etiqueta'])]
        for i in range(1, 5):
            if valor_db and str(i) in valor_db:
                fila_datos.append(Paragraph("X", styles['Dato']))
            else:
                fila_datos.append(Paragraph("", styles['Dato']))
        table_data_profundos.append(fila_datos)

    # Crear y estilizar la tabla
    reflejos_profundos_table = Table(table_data_profundos, colWidths=[6*cm, None, None, None, None])
    reflejos_profundos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(reflejos_profundos_table)
    elements.append(Spacer(1, 0.5 * cm))



    # Reflejos Superficiales o Mucocutáneos
    elements.append(Paragraph("<b>Reflejos Superficiales o Mucocutáneos</b>", styles['Subtitulo']))
    elements.append(Spacer(1, 0.5 * cm))

    reflejos_superficiales = [
        ("Córneo Palpebral", historia_clinica.Corneo_Palpebral),
        ("Conjuntivo Palpebral", historia_clinica.Conjuntivo_Palpebral),
        ("Palatino o Velo Palatino", historia_clinica.Palatino_o_Velo_Palatino),
        ("Faríngeo", historia_clinica.Faringeo),
        ("Tusígeno", historia_clinica.Tusigeno),
        ("Vómito", historia_clinica.Vomito),
        ("Respiratorio", historia_clinica.Respiratorio),
        ("Miccional", historia_clinica.Miccional),
        ("Defecatorio", historia_clinica.Defecatorio),
        ("Aquíleo", historia_clinica.Aquileo),
    ]

    superficiales_table_data = [
        [Paragraph("<b>Reflejo</b>", styles['Etiqueta']),
        Paragraph("<b>1</b>", styles['Etiqueta']),
        Paragraph("<b>2</b>", styles['Etiqueta']),
        Paragraph("<b>3</b>", styles['Etiqueta']),
        Paragraph("<b>4</b>", styles['Etiqueta'])
        ]
    ]

    for nombre_reflejo, valor_db in reflejos_superficiales:
        fila_datos = [Paragraph(f"<b>{nombre_reflejo}</b>", styles['Etiqueta'])]
        for i in range(1, 5):
            if valor_db and str(i) in valor_db:
                fila_datos.append(Paragraph("X", styles['Dato']))
            else:
                fila_datos.append(Paragraph("", styles['Dato']))
        superficiales_table_data.append(fila_datos)

    superficiales_table = Table(superficiales_table_data, colWidths=[6*cm, None, None, None, None])
    superficiales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(superficiales_table)
    elements.append(Spacer(1, 0.5 * cm))


    # Reflejos (Babinski, etc.)
    elements.append(Paragraph("<b>Reflejos</b>", styles['Subtitulo']))
    elements.append(Spacer(1, 0.5 * cm))

    reflejos_adicionales = [
        ("Babinski", historia_clinica.Babinski),
        ("Chaddock", historia_clinica.Chaddock),
        ("Oppenheim", historia_clinica.Oppenheim),
        ("Gordon", historia_clinica.Gordon),
        ("Kerning", historia_clinica.Kerning),
        ("Brudzinski", historia_clinica.Brudzinski),
    ]

    adicionales_table_data = [
        [Paragraph("<b>Reflejo</b>", styles['Etiqueta']),
        Paragraph("<b>1</b>", styles['Etiqueta']),
        Paragraph("<b>2</b>", styles['Etiqueta']),
        Paragraph("<b>3</b>", styles['Etiqueta']),
        Paragraph("<b>4</b>", styles['Etiqueta'])
        ]
    ]

    for nombre_reflejo, valor_db in reflejos_adicionales:
        fila_datos = [Paragraph(f"<b>{nombre_reflejo}</b>", styles['Etiqueta'])]
        for i in range(1, 5):
            if valor_db and str(i) in valor_db:
                fila_datos.append(Paragraph("X", styles['Dato']))
            else:
                fila_datos.append(Paragraph("", styles['Dato']))
        adicionales_table_data.append(fila_datos)

    adicionales_table = Table(adicionales_table_data, colWidths=[6*cm, None, None, None, None])
    adicionales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EBF5FF")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0050A1")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(adicionales_table)
    elements.append(Spacer(1, 0.5 * cm))

    # --- Construimos el PDF final ---
    doc.build(elements)
    
    return response

##################################################################################################################
#################################################################################################################
########################MODIFICACIONES 

@login_required
def orden_medica_paciente(request, pk):
    # Lógica para pasar las variables del Navbar
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()
        
    paciente = get_object_or_404(Paciente, pk=pk)
    context = { 
        'paciente': paciente,
        'is_farmacia': is_farmacia, # <-- AGREGADO
        'is_doctora': is_doctora, # <-- AGREGADO
    }
    return render(request, 'orden_medica.html', context)




# 1. Vista para la LISTA/CALENDARIO de la Agenda
@login_required 
def agenda_view(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if not is_doctora and not is_farmacia:
        return redirect('HomeSinInicio')
    
    year_str = request.GET.get('year')
    month_str = request.GET.get('month')

    if year_str and month_str:
        try:
            selected_year = int(year_str)
            selected_month = int(month_str)
            if not 1 <= selected_month <= 12:
                raise ValueError("Mes inválido")
            selected_date = date(selected_year, selected_month, 1)
        except (ValueError, TypeError):
            selected_date = date.today()
            selected_year = selected_date.year
            selected_month = selected_date.month
    else:
        selected_date = date.today()
        selected_year = selected_date.year
        selected_month = selected_date.month
    
    first_day_of_month = date(selected_year, selected_month, 1)
    last_day_of_month = date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

    # Utiliza la nueva función de ayuda para obtener el usuario del doctor
    doctor_user_obj = get_doctor_user(request.user)
    
    if doctor_user_obj:
        citas_mes = Cita.objects.filter(
            doctor=doctor_user_obj, # ¡Ahora filtra por el usuario correcto!
            fecha__range=[first_day_of_month, last_day_of_month]
        ).order_by('fecha', 'hora_inicio')
    else:
        # Si no se encuentra un doctor válido, no se muestran citas
        citas_mes = Cita.objects.none()
        messages.error(request, "No se encontró un perfil de doctor asociado.")


    cal = calendar.Calendar()
    month_calendar = cal.monthdatescalendar(selected_year, selected_month)

    calendar_days_with_citas = []
    for week in month_calendar:
        week_data = []
        for day_obj in week:
            citas_del_dia = citas_mes.filter(fecha=day_obj)
            
            week_data.append({
                'date': day_obj,
                'is_current_month': day_obj.month == selected_month,
                'is_today': day_obj == date.today(),
                'citas': citas_del_dia
            })
        calendar_days_with_citas.append(week_data)

    prev_month_date = first_day_of_month - timedelta(days=1)
    next_month_date = last_day_of_month + timedelta(days=1)

    context = {
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_name': first_day_of_month.strftime('%B'),
        'calendar_days_with_citas': calendar_days_with_citas,
        'today': date.today(),
        
        'prev_month_year': prev_month_date.year,
        'prev_month_month': prev_month_date.month,
        'next_month_year': next_month_date.year,
        'next_month_month': next_month_date.month,
        
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'agenda.html', context)

# 2. Vista para CREAR Citas
# Pacientes/views.py

@login_required
def crear_cita_view(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if not is_doctora and not is_farmacia:
        messages.error(request, "No tienes permiso para ver esta página.")
        return redirect('HomeSinInicio')
    
    # Obtener el CustomUser del doctor y su perfil de Doctor
    # Usamos las funciones de ayuda para unificar la lógica
    doctor_user_obj = get_doctor_user(request.user)
    doctor_profile_obj = get_doctor_profile(request.user)

    if not doctor_user_obj or not doctor_profile_obj:
        messages.error(request, "Tu perfil no está completo. No se puede agendar la cita.")
        return redirect('HomeSinInicio')
            
    if request.method == 'POST':
        form = CitaForm(request.POST)
        if form.is_valid():
            cita = form.save(commit=False)
            
            # Asignamos el CustomUser del doctor, independientemente de si es doctor o farmacia
            cita.doctor = doctor_user_obj
            
            cita.save()
            messages.success(request, 'Cita creada exitosamente.')
            return redirect('agenda')
        else:
            messages.error(request, 'Hubo un error al crear la cita. Por favor, revisa los datos.')
    else:
        form = CitaForm()
        # Filtra el queryset del campo 'paciente' para mostrar solo los pacientes del doctor
        # Esto asegura que la lista de pacientes se muestre correctamente
        form.fields['paciente'].queryset = Paciente.objects.filter(doctor_responsable=doctor_profile_obj).order_by('nombre')
    
    context = {
        'form': form,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'crear_cita.html', context)

# 3. Vista para EDITAR Citas
@login_required
def editar_cita_view(request, pk):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if not is_doctora and not is_farmacia:
        messages.error(request, "No tienes permiso para ver esta página.")
        return redirect('HomeSinInicio')

    doctor_user_obj = get_doctor_user(request.user)
    if not doctor_user_obj:
        messages.error(request, "No se encontró un perfil de doctor asociado.")
        return redirect('agenda')

    cita = get_object_or_404(Cita, pk=pk, doctor=doctor_user_obj)

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cita actualizada exitosamente.')
            return redirect('agenda')
        else:
            messages.error(request, 'Hubo un error al actualizar la cita. Por favor, revisa los datos.')
    else:
        # Aquí, inicializamos el formulario con la instancia de la cita
        form = CitaForm(instance=cita)

        # Y aquí, asignamos explícitamente el valor inicial del campo de fecha.
        # El widget DateInput necesita la fecha en formato 'YYYY-MM-DD'.
        form.fields['fecha'].initial = cita.fecha.isoformat() if cita.fecha else None
        
        # También puedes hacerlo con los campos de tiempo para asegurarte
        form.fields['hora_inicio'].initial = cita.hora_inicio.strftime('%H:%M') if cita.hora_inicio else None
        form.fields['hora_fin'].initial = cita.hora_fin.strftime('%H:%M') if cita.hora_fin else None

        # Filtra el queryset del campo 'paciente'
        doctor_profile_obj = get_doctor_profile(request.user)
        if doctor_profile_obj:
            form.fields['paciente'].queryset = Paciente.objects.filter(doctor_responsable=doctor_profile_obj).order_by('nombre')
        else:
            form.fields['paciente'].queryset = Paciente.objects.none()

    context = {
        'form': form,
        'cita': cita,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'editar_cita.html', context)


# 4. Vista para ELIMINAR Citas
@login_required
def eliminar_cita_view(request, pk):
    # Obtener la cita por su PK (Primary Key) o devolver un 404 si no existe
    cita = get_object_or_404(Cita, pk=pk)

    # Opcional pero muy RECOMENDADO: Asegurarse de que solo el doctor asignado a la cita pueda eliminarla
    # O que el usuario tenga un permiso específico para eliminar.
    if cita.doctor != request.user:
        messages.error(request, 'No tienes permiso para eliminar esta cita.')
        return redirect('agenda') # Redirige a la agenda si no tiene permiso

    # La eliminación siempre debe ser a través de una solicitud POST por seguridad.
    # Evita que se eliminen recursos accidentalmente con una simple petición GET.
    if request.method == 'POST':
        cita.delete() # Elimina la cita de la base de datos
        messages.success(request, 'Cita eliminada exitosamente.')
        return redirect('agenda') # Redirige de vuelta a la vista de la agenda
    
    # Si la solicitud es GET (por ejemplo, si el usuario navega directamente a la URL de eliminar)
    # Puedes renderizar una página de confirmación si lo prefieres, o simplemente redirigir.
    # La solución recomendada es usar el confirm de JavaScript en el botón, como se muestra en la plantilla.
    # Si llegas aquí con GET y no quieres una página de confirmación separada:
    messages.error(request, 'Acceso inválido. La eliminación de citas solo se permite a través de una solicitud POST.')
    return redirect('agenda')





#Vistas para formatos de consentimiento
@login_required
def consentimiento_create(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    
    # Lógica para determinar el grupo del usuario y pasar a la plantilla
    is_farmacia = False
    is_doctora = False

    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    if request.method == 'POST':
        form = ConsentimientoInformadoForm(request.POST)
        if form.is_valid():
            consentimiento = form.save(commit=False)
            consentimiento.paciente = paciente
            consentimiento.save()
            # Redirigimos al detalle del nuevo consentimiento
            return redirect('consentimiento_detail', pk=consentimiento.pk)
    else:
        # Llenamos el formulario con la información del paciente
        initial_data = {
            'nombre': f'{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno}',
        }
        form = ConsentimientoInformadoForm(initial=initial_data)
    
    context = {
        'form': form,
        'paciente': paciente,
        'is_farmacia': is_farmacia,  # Pasamos la variable a la plantilla
        'is_doctora': is_doctora,    # Pasamos la variable a la plantilla
    }
    
    return render(request, 'consentimientos/consentimiento_form.html', context)


# VISTA PARA LISTAR LOS CONSENTIMIENTOS DE UN PACIENTE
@login_required
def consentimiento_list_by_paciente(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    # Asume que el modelo es ConsentimientoInformado, basándome en tu código anterior
    consentimientos = ConsentimientoInformado.objects.filter(paciente=paciente).order_by('-fecha')

    # Lógica para determinar el grupo del usuario y pasar a la plantilla
    is_farmacia = False
    is_doctora = False

    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    context = {
        'consentimientos': consentimientos,
        'paciente': paciente,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    
    return render(request, 'consentimientos/consentimiento_list.html', context)




# VISTA PARA VER LOS DETALLES DE UN CONSENTIMIENTO
@login_required
def consentimiento_detail(request, pk):
    # Cambiamos el modelo de referencia
    consentimiento = get_object_or_404(ConsentimientoInformado, pk=pk)

    # Lógica para determinar el grupo del usuario y pasar a la plantilla
    is_farmacia = False
    is_doctora = False

    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()

    context = {
        'consentimiento': consentimiento,
        'is_farmacia': is_farmacia,  # Pasamos la variable a la plantilla
        'is_doctora': is_doctora,    # Pasamos la variable a la plantilla
    }
    
    return render(request, 'consentimientos/consentimiento_detail.html', context)


# VISTA PARA ELIMINAR UN CONSENTIMIENTO
@login_required
@require_POST
def eliminar_consentimiento(request, pk):
    # Cambiamos el modelo de referencia
    consentimiento = get_object_or_404(ConsentimientoInformado, pk=pk)
    paciente_pk = consentimiento.paciente.pk
    consentimiento.delete()
    messages.success(request, "Consentimiento eliminado exitosamente.")
    return redirect('consentimiento_list_by_paciente', paciente_pk=paciente_pk)


@login_required
def imprimir_consentimiento_pdf(request, pk):
    # Asegúrate de que estás obteniendo el modelo correcto
    consentimiento = get_object_or_404(ConsentimientoInformado, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="nota_expediente_{consentimiento.nombre}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=portrait(A4),
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            leftMargin=2.0 * cm, rightMargin=2.0 * cm)
    elements = []

    # Definimos los estilos de texto con colores
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontSize=14, fontName='Helvetica-Bold', spaceAfter=15, alignment=TA_CENTER, textColor=colors.HexColor("#0128a5")))
    styles.add(ParagraphStyle(name='Subtitulo', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10, alignment=TA_CENTER, textColor=colors.HexColor("#7f0ceb")))
    styles.add(ParagraphStyle(name='Direccion', fontSize=9, fontName='Helvetica', spaceAfter=5, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Telefono', fontSize=9, fontName='Helvetica', alignment=TA_LEFT))
    
    normal_style = styles['Normal']
    bold_style = styles['Normal']
    bold_style.fontName = 'Helvetica-Bold'
    
    # --- Función para agregar la marca de agua ---
    def add_watermark(canvas, doc):
        logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png') # Ajusta la ruta si es diferente
        if os.path.exists(logo_cit_path):
            img = ImageReader(logo_cit_path)
            page_width, page_height = portrait(A4)
            img_width = 12 * cm
            img_height = 10 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.saveState()
            canvas.setFillAlpha(0.2) # Ajusta la transparencia (0.0 - 1.0)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()

    # Asignamos la función de marca de agua al documento
    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark

    # --- Contenido del PDF ---

    # 1. Logos y Título del Encabezado
    logo1_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo2_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'Uni.jpge')

    logo1 = Image(logo1_path, width=6 * cm, height=2.5 * cm) if os.path.exists(logo1_path) else Paragraph("", normal_style)
    logo2 = Image(logo2_path, width=3 * cm, height=2.5 * cm) if os.path.exists(logo2_path) else Paragraph("", normal_style)

    encabezado_data = [
        [logo1, Paragraph("<b>Dra. Jaqueline Vásquez Gómez<br/>Cédula Profesional: 11708282<br/>Prolongación Emiliano Zapata Sn. Bo. de la luz Santiago Cuautlalpan Tepotzotlan Edo. de Mex.</b>", styles['Subtitulo']), logo2]
    ]
    encabezado_table = Table(encabezado_data, colWidths=[7*cm, None, 0.5*cm])
    encabezado_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(encabezado_table)
    elements.append(Spacer(1, 0.5 * cm))

    # 2. Nota de Expediente Clínico
    elements.append(Paragraph("<b>CONSENTIMIENTO INFORMADO</b>", styles['Titulo']))

    # 3. Información del Paciente (dividida en dos tablas)
    nombre_data = [
        [
            Paragraph(f"<b>Nombre:</b> {consentimiento.nombre}", normal_style)
        ]
    ]
    nombre_table = Table(nombre_data, colWidths=[None])
    nombre_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
    ]))
    elements.append(nombre_table)

    # Tabla para Fecha y Edad
    fecha_edad_data = [
        [
            Paragraph(f"<b>Fecha:</b> {consentimiento.fecha.strftime('%d/%m/%Y')}", normal_style),
            Spacer(1, 0),
            Paragraph(f"<b>Edad:</b> {consentimiento.edad}", normal_style),
        ]
    ]
    fecha_edad_table = Table(fecha_edad_data, colWidths=[6.5*cm, 0.5*cm, 6.5*cm])
    fecha_edad_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('LINEBELOW', (2, 0), (2, 0), 1, colors.black),
    ]))
    elements.append(fecha_edad_table)

    # Tabla para las Medidas
    medidas_data = [
        [
            Paragraph(f"<b>Temp:</b> {consentimiento.temp}", normal_style),
            Spacer(1, 0),
            Paragraph(f"<b>Peso:</b> {consentimiento.peso}", normal_style),
            Spacer(1, 0),
            Paragraph(f"<b>Talla:</b> {consentimiento.talla}", normal_style),
            Spacer(1, 0),
            Paragraph(f"<b>T/A:</b> {consentimiento.ta}", normal_style),
        ]
    ]
    medidas_table = Table(medidas_data, colWidths=[4*cm, 0.5*cm, 4*cm, 0.5*cm, 4*cm, 0.5*cm, 4*cm])
    medidas_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('LINEBELOW', (2, 0), (2, 0), 1, colors.black),
        ('LINEBELOW', (4, 0), (4, 0), 1, colors.black),
        ('LINEBELOW', (6, 0), (6, 0), 1, colors.black),
    ]))
    elements.append(medidas_table)
    elements.append(Spacer(1, 1 * cm))

    # 4. Sección de Rp.
    elements.append(Paragraph("<b>Rp.</b>", bold_style))
    rp_texto = consentimiento.rp.replace('\n', '<br/>')
    elements.append(Paragraph(rp_texto, normal_style))
    
    # 5. Agregamos un Spacer flexible para empujar el contenido al final
    elements.append(Spacer(1, 1, doc.height))





    # Construimos el PDF
    doc.build(elements)

    return response






@login_required
@require_POST
def eliminar_consentimiento(request, pk):
    consentimiento = get_object_or_404(ConsentimientoInformado, pk=pk)
    paciente_pk = consentimiento.paciente.pk
    consentimiento.delete()
    messages.success(request, "Consentimiento eliminado exitosamente.")
    return redirect('consentimiento_list_by_paciente', paciente_pk=paciente_pk)






# Vistas para Historia Clínica General (Ajuste de rutas de plantillas)
@login_required
def historia_clinica_list(request):
    is_farmacia = False
    is_doctora = False
    
    if request.user.is_authenticated:
        is_farmacia = request.user.groups.filter(name='Farmacia').exists()
        is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if not is_doctora and not is_farmacia:
        return redirect('HomeSinInicio')
        
    historias = HistoriaClinica.objects.all()
    paciente_id = request.GET.get('paciente')
    if paciente_id:
        historias = historias.filter(paciente__pk=paciente_id)
        
    context = {
        'historias': historias,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'historia_clinica_list.html', context)


@login_required
def historia_clinica_detail(request, pk):
    historia = get_object_or_404(HistoriaClinica, pk=pk)
    return render(request, 'historia_clinica_detail.html', {'historia': historia}) # Ruta de plantilla ajustada

@login_required
def historia_clinica_pdf(request, pk):
    historia = get_object_or_404(HistoriaClinica, pk=pk)
    template_path = 'historia_clinica_pdf_template.html' # Ruta de plantilla ajustada
    context = {'historia': historia}
    response = HttpResponse(content_type='application/pdf')
    # Ajusta el nombre del archivo PDF
    response['Content-Disposition'] = f'attachment; filename="historia_clinica_{historia.paciente.nombre}_{historia.paciente.apellido_paterno}.pdf"'
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(
        html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

@login_required
def orden_medica_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    # Aquí puedes listar órdenes médicas existentes o dar un enlace para crear una nueva
    return render(request, 'orden_medica_selector.html', {'paciente': paciente}) # Ajusta la ruta de plantilla




# Vista para crear una nueva receta
@login_required
def crear_receta_view(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    if request.method == 'POST':
        form = RecetaForm(request.POST)
        if form.is_valid():
            receta = form.save(commit=False)
            receta.paciente = paciente
            receta.medico = request.user

            # --- LÓGICA AGREGADA PARA GUARDAR LOS NUEVOS CAMPOS ---
            receta.peso = request.POST.get('peso')
            receta.talla = request.POST.get('talla')
            receta.edad = request.POST.get('edad')
            receta.ta = request.POST.get('ta')
            receta.fc = request.POST.get('fc')
            receta.sat_o2 = request.POST.get('sat_o2')

            receta.save()
            # --- FIN DE LA LÓGICA AGREGADA ---

            messages.success(request, 'Receta creada exitosamente.')
            return redirect('detalle_receta', pk=receta.pk)
    else:
        form = RecetaForm()

    context = {
        'form': form,
        'paciente': paciente
    }
    return render(request, 'crear_receta.html', context)

# Vista para la lista de recetas de un paciente
@login_required
def lista_recetas_view(request, paciente_pk):
    # Lógica para determinar el grupo del usuario y pasar a la plantilla
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    
    context = {
        'paciente': paciente,
        'is_farmacia': is_farmacia,  # Agregado para el navbar
        'is_doctora': is_doctora,    # Agregado para el navbar
    }

    # Si es un doctor, obtenemos las recetas. Si es farmacia, el queryset de recetas estará vacío
    if is_doctora:
        recetas = Receta.objects.filter(paciente=paciente).order_by('-fecha')
        context['recetas'] = recetas

    return render(request, 'lista_recetas.html', context)

# Vista para el detalle de una receta
@login_required
def detalle_receta_view(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    # --- CAMBIO AQUÍ: LA RUTA DEL TEMPLATE ---
    return render(request, 'detalle_receta.html', {'receta': receta})





@login_required
def imprimir_receta_pdf(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    paciente = receta.paciente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receta_{paciente.nombre}.pdf"'

    # Función para dibujar la marca de agua
    def add_watermark(canvas, doc):
        uni_logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'uniByN.jpeg')
        if os.path.exists(uni_logo_path):
            img = ImageReader(uni_logo_path)
            # Dibuja la imagen en el centro de la página
            page_width, page_height = landscape(A4)
            img_width, img_height = 8*cm, 8*cm # Tamaño de la imagen de marca de agua
            
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            
            canvas.saveState()
            canvas.setFillGray(0.2, 0.2)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, mask='auto')
            canvas.restoreState()

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark
    elements = []
    
    # 1. Definición de estilos en un diccionario.
    custom_styles = {
        'Title': ParagraphStyle(name='Title', fontSize=18, spaceAfter=20, alignment=1, textColor=colors.HexColor('#021b6dff')),
        'Titulo2':ParagraphStyle(name='Titulo2',fontSize=14,spaceAfter=20,alignment=1,textColor=colors.HexColor('#021b6dff')),
        'Heading3': ParagraphStyle(name='Heading3', fontSize=12, spaceAfter=10, textColor=colors.HexColor('#021b6dff')),
        'Normal': ParagraphStyle(name='Normal', fontSize=10, spaceAfter=5, leading=14),
    }

    # Definimos los estilos de la tabla para los datos del paciente
    paciente_table_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
    ])

    # 2. Creamos el contenido de la receta en una función reutilizable
    def create_receta_content():
        content_elements = []
        
                # Encabezado (logo y título) usando una tabla para un posicionamiento preciso
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        uni_logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'uni.jpeg')
        
        logo = None
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2.5*cm, height=2.5*cm)
        
        uni_logo = None
        if os.path.exists(uni_logo_path):
            uni_logo = Image(uni_logo_path, width=2.5*cm, height=2.5*cm)
        
        # Creamos una lista con los elementos de la tabla.
        header_data = [
            [uni_logo, Paragraph("<b>Dra. Jaqueline Vásquez Gómez</b>", custom_styles['Title']), logo]
        ]
        
        # Creamos la tabla y definimos sus estilos. ¡Aquí está el cambio!
        header_table = Table(header_data, colWidths=[3*cm, None, 3*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'), # Alinea el logo de UNI a la izquierda
            ('ALIGN', (1,0), (1,0), 'CENTER'), # Alinea el nombre al centro
            ('ALIGN', (2,0), (2,0), 'RIGHT'), # Alinea el logo a la derecha
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        content_elements.append(header_table)
        content_elements.append(Paragraph("Universidad Evangélica Nicaragüense", custom_styles['Titulo2']))
        content_elements.append(Paragraph("Ced. Profesional: 11708282", custom_styles['Titulo2']))
        content_elements.append(Spacer(1, 1*cm))

        
# --- INICIO DEL CÓDIGO CORREGIDO PARA LA LÍNEA ---
        line_width = 10 * cm  # Ancho deseado de la línea (10 cm)
        page_width = landscape(A4)[0]
        
        # El punto de inicio X se calcula para centrar el elemento en la página
        start_x = (page_width - line_width) / 2
        
        # Se crea el objeto Drawing con el ancho de la línea deseado
        d = Drawing(line_width, 1)
        # La línea se dibuja dentro del Drawing, de 0 a su ancho total
        d.add(Line(0, 0, line_width, 0, strokeWidth=2, strokeColor=colors.black))
        
        # Se crea una tabla para centrar el Drawing en la página
        line_table = Table([[d]], colWidths=[None])
        line_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (0,0), 'CENTER'),
        ]))
        
        content_elements.append(line_table)
        content_elements.append(Spacer(1, 0.5*cm))
        # --- FIN DEL CÓDIGO CORREGIDO ---
        
        # Tabla de datos del paciente
        paciente_data = [
            [Paragraph(f'<b>NOMBRE COMPLETO:</b> {paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno}', custom_styles['Normal']),
             Paragraph(f'<b>EDAD:</b> {receta.edad} años', custom_styles['Normal'])],
            [Paragraph(f'<b>FECHA DE NACIMIENTO:</b> {paciente.fecha_nacimiento.strftime("%d/%m/%Y")}', custom_styles['Normal']),
             Paragraph(f'<b>ESTATURA:</b> {receta.talla} cm', custom_styles['Normal'])],
            [Paragraph(f'<b>DOMICILIO:</b> {paciente.direccion or "N/A"}', custom_styles['Normal']),
             Paragraph(f'<b>PESO:</b> {receta.peso} kg', custom_styles['Normal'])],
        ]
        paciente_table = Table(paciente_data, colWidths=[10*cm, 8*cm])
        paciente_table.setStyle(paciente_table_style)
        content_elements.append(paciente_table)
        content_elements.append(Spacer(1, 0.5*cm))

        # Sección de Diagnóstico
        content_elements.append(Paragraph("<b>Diagnóstico</b>", custom_styles['Heading3']))
        content_elements.append(Paragraph(receta.diagnostico, custom_styles['Normal']))
        content_elements.append(Spacer(1, 0.5*cm))
        
        # Sección de Prescripción
        content_elements.append(Paragraph("<b>Prescripción</b>", custom_styles['Heading3']))
        content_elements.append(Paragraph(f' {receta.medicamento}', custom_styles['Normal']))
        content_elements.append(Paragraph(f' {receta.indicaciones}', custom_styles['Normal']))
        content_elements.append(Spacer(1, 2*cm))
        
        # --- INICIO DEL CÓDIGO MODIFICADO PARA BAJAR LA FIRMA ---
        # Añade un espacio flexible que se expande para empujar la firma hacia abajo
        content_elements.append(Spacer(1, 1, 'flexible'))

        # Firma
        firma_data = [
            [Paragraph('<b>Nombre del consultorio:</b> Centro Integral Terapeutico<br/><b>Teléfono:</b> 55 13 09 81 45<br/><b>Domicilio:</b> Prolongación Emiliano Zapata Sn.Bo. de la Luz Santiago Cuautlalpan', custom_styles['Normal']),
             Paragraph('__________________________<br/><b>Firma de la Doctora</b>', custom_styles['Normal'])]
        ]
        
        firma_table = Table(firma_data, colWidths=[None, None])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        
        content_elements.append(firma_table)

        return content_elements

    # 3. Se añade el contenido al documento final
    elements.extend(create_receta_content())
     # Creación de una línea horizontal gruesa
    d = Drawing(landscape(A4)[0], 1)
    d.add(Line(0, 0, landscape(A4)[0] - 3*cm, 0, strokeWidth=2, strokeColor=colors.black)) # Ajusta el strokeWidth para el grosor
    elements.append(d)
    elements.append(Spacer(1, 1*cm))
    # --- FIN DEL CÓDIGO MODIFICADO ---

    # Construye el PDF y lo envía
    doc.build(elements)

    return response




@login_required
def eliminar_receta(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    
    # Nota: Ya no es necesario guardar el PK del paciente, ya que no vamos a redirigir a su expediente.
    
    if request.method == 'POST':
        receta.delete()
        messages.success(request, 'La receta ha sido eliminada exitosamente.')
        
        # CAMBIO AQUÍ: Redirige a la URL de la lista de todos los pacientes
        return redirect('lista_pacientes')
    
    # Si la solicitud no es POST, por ejemplo GET, redirige de vuelta
    return redirect('lista_pacientes')