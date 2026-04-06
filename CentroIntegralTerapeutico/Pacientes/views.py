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
#from formtools.wizard.views import c
from formtools.wizard.views import SessionWizardView
from django.views.decorators.http import require_POST # Importa este decorador
from django.db import IntegrityError


# views.py
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

from .models import (
    Paciente,
    ConsentimientoInformado,
    HistoriaClinica
)

from .forms import *




#VIEWS REPORTLAB


from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, ListFlowable,  ListItem
import os
from django.contrib.auth.decorators import login_required
from django.conf import settings


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, portrait, landscape, A5
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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY



FORMS = [
    ("Historia Clínica", HistoriaClinicaUnificadaForm),
    ("Interrogatorio por Aparatos y Sistemas", HistoriaClinicaSegundaHoja),
    ("Exploración", ExploracionCompletaForm),
    ("Exploración 3", CuestionarioExploracionGlasgow),
    ("Exploración 5", CuestionarioExploracionFinalForm),
]
TEMPLATES = {
    "Historia Clínica": "cuestionario/historia_clinica_unificada.html",
    "Interrogatorio por Aparatos y Sistemas": "cuestionario/HistoriaClinicaPagina2.html",
    "Exploración": "cuestionario/HistoriaClinicaPagina3.html",
    "Exploración 3": "cuestionario/HistoriaClinicaPagina4.html",
    "Exploración 4": "cuestionario/HC_Glasgow.html",
    "Exploración 5": "cuestionario/HC_ExploracionFinal.html",
}


FORMS_ME = [
    ("parte_1", HistoriaClinicaMusculoEsqueleticoCompletoForm),
]

TEMPLATES_ME = {
    "parte_1": "cuestionario/HCME_HistoriaClinica1.html",
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

from Inventario.models import CorteDeCaja

@login_required
def dashboard_farmacia(request):
    # Verifica si el usuario pertenece al grupo 'Farmacia'
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    corte_activo = CorteDeCaja.objects.filter(usuario=request.user, is_open=True).first()


    if not is_farmacia:
        messages.warning(request, "No tienes permiso para acceder a este área de Farmacia.")
        return redirect('HomeSinInicio') # Redirige a un lugar seguro si no tiene permiso

    context = {
        'is_farmacia': is_farmacia,
        'corte_activo': corte_activo,

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
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)

            if is_doctora:
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
            messages.error(request, "Hubo un error al crear el paciente, favor de revisar los campos.")
    else:
        form = PacienteForm()

    context = {
        "form": form,
        "is_doctora": is_doctora,
        "is_farmacia": is_farmacia,
    }
    return render(request, "CrearPaciente.html", context)






@login_required
def Lista_Pacientes_view(request):
    # Lógica para pasar las variables del Navbar
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    pacientes = Paciente.objects.none()  # Por defecto vacío

    if is_doctora:
        try:
            doctor_profile = request.user.doctor_profile
            pacientes = Paciente.objects.filter(doctor_responsable=doctor_profile).order_by('apellido_paterno', 'apellido_materno', 'nombre')
        except Doctor.DoesNotExist:
            pacientes = Paciente.objects.none()
    elif is_farmacia:
        # Mostrar todos los pacientes para Farmacia
        pacientes = Paciente.objects.all().order_by('apellido_paterno', 'apellido_materno', 'nombre')

    context = {
        'pacientes': pacientes,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'Pacientes.html', context)




# Modificación en Pacientes/views.py

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
            # Obtén los datos limpios del formulario, pero no los guardes aún
            paciente_editado = form.save(commit=False)

            # --- NUEVA LÓGICA AGREGADA ---
            # Si el campo de fecha de nacimiento en el formulario está vacío,
            # lo asignamos al valor del paciente original.
            if not request.POST.get('fecha_nacimiento'):
                paciente_editado.fecha_nacimiento = paciente.fecha_nacimiento
            # --- FIN DE LA NUEVA LÓGICA ---

            paciente_editado.save()
            messages.success(request, f'Paciente {paciente.nombre} actualizado exitosamente.')
            return redirect('lista_pacientes')
        else:
            messages.error(request, 'Hubo un error al actualizar el paciente. Por favor, revisa los datos.')
    else:
        form = PacienteForm(instance=paciente)

    context = {
        'form': form,
        'paciente': paciente,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
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
    historia_clinicaME = paciente.historiales_musculoesqueleticos.all() # ¡Esta es la forma correcta! # Obtiene todas las historias clínicas del paciente

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

        paciente_id = self.kwargs.get('paciente_id')
        if paciente_id:
            context['paciente'] = get_object_or_404(Paciente, pk=paciente_id)
        # Puedes añadir contexto extra aquí, por ejemplo el nombre del paso actual
        context['step_title'] = self.steps.current
        print(f"[Wizard] get_context_data para step: {self.steps.current}")
        print(f"[Wizard] Form errors: {form.errors if form else 'No form'}")

        context['current_form'] = form # Esto es clave, aunque ya está en 'form'
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

COLOR_VERDE_OSCURO = colors.HexColor("#1a4a39")
COLOR_VERDE_PRINCIPAL = colors.HexColor("#44916f")
COLOR_VERDE_ENCABEZADO = colors.HexColor("#cdded7")
COLOR_FONDO_CLARO = colors.HexColor("#f8fcf8")
COLOR_FONDO_DATO = colors.HexColor("#f4f9f2")
COLOR_BORDE = colors.HexColor("#c0c0c0")
COLOR_LABEL = colors.HexColor("#333333")

# Función auxiliar para manejar respuestas nulas o vacías
def safe_str(value):
    if value is None or str(value).strip() in ["", "N/A", "None", "[]"]:
        return "—"
    return str(value)

@login_required
def HistorialMusculoEsqueleticoPDF(request, pk, historia_pk):
    # 1. Obtener datos
    # Asegúrate de importar tus modelos Paciente y HistoriaClinicaMusculoEsqueletico
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinicaME = get_object_or_404(HistoriaClinicaMusculoEsqueletico, pk=historia_pk, paciente=paciente)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Historial_Musculo_Esqueletico_{historia_clinicaME.fecha_registro.strftime("%Y-%m-%d")}.pdf"'

    # Usamos A5 con orientación portrait, como el original
    DOC_WIDTH, DOC_HEIGHT = portrait(A5)
    doc = SimpleDocTemplate(response, pagesize=A5,
                            topMargin=0.7 * cm, bottomMargin=0.7 * cm,
                            leftMargin=1.0 * cm, rightMargin=1.0 * cm)
    elements = []
    CONTENT_WIDTH = DOC_WIDTH - (2 * 1.0 * cm)

    # --- DEFINICIÓN DE ESTILOS Y FUNCIONES AUXILIARES ---
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(name='TituloPrincipal', fontSize=10, fontName='Times-Bold', spaceAfter=2, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO))
    styles.add(ParagraphStyle(name='TituloSeccion', fontSize=10, fontName='Times-Bold', spaceBefore=6, spaceAfter=2,
                              textColor=colors.white,
                              backColor=COLOR_VERDE_PRINCIPAL,
                              borderPadding=3,
                              borderColor=COLOR_VERDE_OSCURO,
                              borderWidth=1,
                              borderRadius=3))

    styles.add(ParagraphStyle(name='Etiqueta', fontSize=9.5, fontName='Times-Bold', textColor=COLOR_LABEL, leading=12))
    styles.add(ParagraphStyle(name='Dato', fontSize=9.5, fontName='Times-Roman', textColor=colors.black, leading=11, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='DatoCompacto', fontSize=9.5, fontName='Times-Roman', textColor=colors.black, leading=9.5, alignment=TA_JUSTIFY))


    def format_list(data_list):
        # Función para formatear ArrayFields con checks (como en el original)
        if not data_list or not isinstance(data_list, list) or all(safe_str(item) == "—" for item in data_list):
            return Paragraph("—", styles['Dato'])

        color_check = COLOR_VERDE_PRINCIPAL.hexval()
        items = [f'<font face="Times-Roman" size="9.5" color="{color_check}">\u2713</font> <font face="Times-Roman" color="{colors.black.hexval()}">{safe_str(item)}</font>' for item in data_list if safe_str(item) != "—"]

        return Paragraph("<br/>".join(items), styles['DatoCompacto'])


    def crear_seccion_recuadro(titulo, datos_dict):
        # Función para crear secciones en dos columnas con diseño de recuadro
        elements.append(Paragraph(titulo, styles['TituloSeccion']))

        table_data = []
        for etiqueta, dato in datos_dict.items():
            if isinstance(dato, list):
                formato_dato = format_list(dato)
            else:
                formato_dato = Paragraph(f"{safe_str(dato)}", styles['Dato'])

            table_data.append([
                Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                formato_dato
            ])

        section_table = Table(table_data, colWidths=[4.5*cm, None])
        section_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLOR_FONDO_DATO),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('INNERGRID', (0,0), (-1,-1), 0.25, COLOR_BORDE),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(section_table)
        elements.append(Spacer(1, 0.3 * cm))
        return elements

    # Función para agregar la marca de agua (Copia del original)
    def add_watermark(canvas, doc):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            page_width, page_height = doc.pagesize
            img_width = 8 * cm
            img_height = 8 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.saveState()
            canvas.setFillAlpha(0.08)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()

    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark


    # --- 2. HEADER PROFESIONAL (Copia del original) ---
    logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_cit = Image(logo_cit_path, width= 2 * cm, height=2 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])

    header_data = [
        [logo_cit,
         Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA MUSCULOESQUELÉTICA",
                   ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))


    # --- 3. DATOS DE IDENTIFICACIÓN Y MOTIVO DE CONSULTA (Copia del original) ---
# --- 3. DATOS DE IDENTIFICACIÓN Y MOTIVO DE CONSULTA (ACTUALIZADO CON CAMPOS DE PACIENTE) ---
    elements.append(Paragraph("DATOS DE IDENTIFICACIÓN Y MOTIVO DE CONSULTA", styles['TituloSeccion']))

    # Nota: Usamos paciente.campo directamente, envuelto en safe_str
    datos_id_data = [
        # Fila 1: Nombre Completo, Género, Edad
        [Paragraph("<b>Nombre Completo:</b>", styles['Etiqueta']),
         Paragraph(f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno or ''} ({paciente.genero}, {paciente.edad} años)", styles['Dato'])],

        # Fila 2: Fecha Nacimiento, Estado Civil, Ocupación
        [Paragraph("<b>Datos Personales:</b>", styles['Etiqueta']),
         Paragraph(f"<b>F. Nac.:</b> {safe_str(paciente.fecha_nacimiento)}; <b>Edo. Civil:</b> {safe_str(paciente.Estado_Civil)}; <b>Ocupación:</b> {safe_str(paciente.Ocupacion)}", styles['DatoCompacto'])],

        # Fila 3: Religión, Pasatiempo, Deporte (NUEVA FILA)
        [Paragraph("<b>Hábitos:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Religión:</b> {safe_str(paciente.Religion)}; <b>Pasatiempo:</b> {safe_str(paciente.Pasatiempo)}; <b>Deporte:</b> {safe_str(paciente.Deporte_que_practica)}", styles['DatoCompacto'])],

        # Fila 4: Residencia, Nacionalidad, No. Historia (Modificado)
        # Nota: La dirección del paciente se moverá a la fila 5 para separar el No. de Historia
        [Paragraph("<b>Registro:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Nacionalidad:</b> {safe_str(paciente.Nacionalidad)}; <b>F. Reg.:</b> {safe_str(paciente.fecha_registro.strftime('%d %b %Y %H:%M'))}; <b>N° Hist.:</b> {safe_str(historia_clinicaME.no_historia_clinica)}", styles['DatoCompacto'])],

        # Fila 5: Direcciones (NUEVA FILA)
        [Paragraph("<b>Residencia:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Actual:</b> {safe_str(paciente.direccion)}; <b>Anterior:</b> {safe_str(paciente.Residencia_Anterior)}", styles['DatoCompacto'])],

        # Fila 6: Motivo Consulta
        [Paragraph("<b>Motivo Consulta:</b>", styles['Etiqueta']),
         Paragraph(safe_str(historia_clinicaME.motivo_consulta), styles['Dato'])],

        # Fila 7: Enfermedad Actual
        [Paragraph("<b>Enfermedad Actual:</b>", styles['Etiqueta']),
         Paragraph(safe_str(historia_clinicaME.enfermedad_actual), styles['Dato'])],
    ]

    datos_id_table = Table(datos_id_data, colWidths=[4.0*cm, None], hAlign='LEFT')
    datos_id_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(datos_id_table)
    elements.append(Spacer(1, 0.5 * cm))


    # --- 4. ANTECEDENTES (Copia del original, con corrección de ArrayFields) ---

    elements.append(Paragraph("ANTECEDENTES HEREDOFAMILIARES / PERSONALES", styles['TituloSeccion']))

    antecedentes_table_data = [
        # A. Heredofamiliares
        [Paragraph("<b>A. HEREDOFAMILIARES:</b>", styles['Etiqueta']), format_list(historia_clinicaME.Antecedentes_familiares)],

        # B. Hábitos Tóxicos
        [Paragraph("<b>B. HÁBITOS TÓXICOS:</b>", styles['Etiqueta']), format_list(historia_clinicaME.habitos_toxicos)],

        # C. Higiene y Vivienda
        [Paragraph("<b>C. HIGIENE/VIVIENDA:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Baño:</b> {safe_str(historia_clinicaME.baño_diario)}; <b>Dental:</b> {safe_str(historia_clinicaME.aseo_dental)}"
                   f"<br/><b>Viv. Tipo:</b> {safe_str(historia_clinicaME.tipo_vivienda)}; <b>Tamaño:</b> {safe_str(historia_clinicaME.tamanio_vivienda)}", styles['DatoCompacto'])],

        # D. Fisiológicos (CORREGIDO: Usamos .join() para Alimentación)
        [Paragraph("<b>D. FISIOLÓGICOS:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Alimentación:</b> {', '.join([safe_str(item) for item in historia_clinicaME.Allimentación]) if historia_clinicaME.Allimentación else '—'}; <b>Agua:</b> {safe_str(historia_clinicaME.Ingesta_Agua)} L"
                   f"<br/><b>Catarsis:</b> {safe_str(historia_clinicaME.Catarsis)}; <b>Somnia:</b> {safe_str(historia_clinicaME.Somnia)}", styles['DatoCompacto'])],

        # E. Patológicos (Infancia/Adulto)
        [Paragraph("<b>E. PATOLÓGICOS:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Infancia:</b> {safe_str(historia_clinicaME.Infancia)}; <b>Adulto:</b> {safe_str(historia_clinicaME.Adulto)}", styles['Dato'])],

        # F. Patologías Comunes
        [Paragraph("<b>F. PATOLOGÍAS COMUNES:</b>", styles['Etiqueta']), format_list(historia_clinicaME.Patologias)],

        # G. Quirúrgicos/Trauma
        [Paragraph("<b>G. QUIÚRGICOS / TRAUMA:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Operado:</b> {safe_str(historia_clinicaME.ha_sido_operado)} <b>Fecha:</b> {safe_str(historia_clinicaME.fecha_operacion)}"
                   f"<br/><b>Trauma:</b> {safe_str(historia_clinicaME.traumatismo_o_fractura)}; <b>Otro:</b> {safe_str(historia_clinicaME.Otro)}", styles['DatoCompacto'])],
    ]

    antecedentes_table = Table(antecedentes_table_data, colWidths=[4.0*cm, None], hAlign='LEFT')
    antecedentes_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(antecedentes_table)
    elements.append(Spacer(1, 0.3 * cm))


    # --- 5. EXAMEN FÍSICO (Estructurado por filas) ---
    elements.append(Paragraph("EXAMEN FÍSICO", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # A. Inspección General (usando crear_seccion_recuadro)
    datos_inspeccion = {
        "Constitucional": historia_clinicaME.Constitucional,
        "Marcha": historia_clinicaME.Marcha,
        "Actitud": historia_clinicaME.Actitud,
        "Ubicación": historia_clinicaME.Ubicacion,
        "Impresión General": historia_clinicaME.Impresion_general,
    }
    crear_seccion_recuadro("A. INSPECCIÓN GENERAL", datos_inspeccion)


    # B. Signos Vitales y Antropometría (Tabla de 3 columnas - Mantenido)


    GRADOS_C = "\u00b0C"

    signos_antropo_data = [
        [Paragraph("<b>FC:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.FC)} <font size='8'>lpm</font>", styles['Dato']),
         Paragraph("<b>TA:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.TA)} <font size='8'>mmHg</font>", styles['Dato']),
         Paragraph("<b>FR:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.FR)} <font size='8'>rpm</font>", styles['Dato'])],

        [Paragraph("<b>T. Aux.:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.T_Auxiliar)} <font size='8'>{GRADOS_C}</font>", styles['Dato']),
         Paragraph("<b>T. Rectal:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.T_rectal)} <font size='8'>{GRADOS_C}</font>", styles['Dato']),
         Paragraph("<b>Talla:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.Talla)} <font size='8'>m</font>", styles['Dato'])],

        [Paragraph("<b>Peso Hab.:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.Peso_Habitual)} <font size='8'>kg</font>", styles['Dato']),
         Paragraph("<b>Peso Act.:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinicaME.Peso_Actual)} <font size='8'>kg</font>", styles['Dato']),
         Paragraph("<b>IMC:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinicaME.IMC), styles['Dato'])],
    ]

    signos_antropo_table = Table(signos_antropo_data, colWidths=[2.0*cm, 2.5*cm, 2.0*cm, 2.5*cm, 2.0*cm, 2.0*cm], hAlign='LEFT')

    signos_antropo_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (2, 0), (2, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (4, 0), (4, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BACKGROUND', (3, 0), (3, -1), colors.white),
        ('BACKGROUND', (5, 0), (5, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(signos_antropo_table)
    elements.append(Spacer(1, 0.3 * cm))


    # C. Piel, Faneras y Tejido Celular (usando crear_seccion_recuadro)
    datos_piel_tejido = {
        "Aspecto": historia_clinicaME.Aspecto,
        "Distribución Pilosa": historia_clinicaME.Distribuición_pilosa,
        "Lesiones": historia_clinicaME.Lesiones,
        "Faneras": historia_clinicaME.Faneras,
        "Tejido Cel. Subcutáneo": historia_clinicaME.Tejido_celular_subcutaneo,
        # ArrayField que necesita format_list
        "Tejido Cel. (Otros)": historia_clinicaME.Tejido_celular,
    }
    crear_seccion_recuadro("C. PIEL, FANERAS Y TEJIDO CELULAR", datos_piel_tejido)


    # --- 6. Campo Comentarios Finales (Copia del original) ---
    elements.append(Paragraph("COMENTARIOS ADICIONALES", styles['TituloSeccion']))
    elements.append(Paragraph(safe_str(historia_clinicaME.comentarios), styles['Dato']))
    elements.append(Spacer(1, 0.3 * cm))

    # --- Construimos el PDF final ---
    doc.build(elements)

    return response


COLOR_VERDE_OSCURO = colors.HexColor("#1a4a39")
COLOR_VERDE_PRINCIPAL = colors.HexColor("#44916f")
COLOR_VERDE_ENCABEZADO = colors.HexColor("#cdded7")
COLOR_FONDO_CLARO = colors.HexColor("#f8fcf8")
COLOR_FONDO_DATO = colors.HexColor("#f4f9f2")
COLOR_BORDE = colors.HexColor("#c0c0c0")
COLOR_LABEL = colors.HexColor("#333333")

# Función auxiliar para manejar respuestas nulas o vacías
def safe_str(value):
    if value is None or str(value).strip() in ["", "N/A", "None"]:
        return "—"
    return str(value)

@login_required
def HistorialClinicoPDF(request, pk, historia_pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    historia_clinica = get_object_or_404(HistoriaClinica, pk=historia_pk, paciente=paciente)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Historial_Clinico_{historia_clinica.fecha_registro.strftime("%Y-%m-%d")}.pdf"'

    DOC_WIDTH, DOC_HEIGHT = portrait(A5)
    doc = SimpleDocTemplate(response, pagesize=A5,
                             topMargin=0.7 * cm, bottomMargin=0.7 * cm,
                             leftMargin=1.0 * cm, rightMargin=1.0 * cm)
    elements = []

    # --- DEFINICIÓN DE ESTILOS Y FUNCIONES AUXILIARES ---
    styles = getSampleStyleSheet()

    # [MEJORA 1: TITULO PRINCIPAL MÁS COMPLETO Y CONTRASTE MEJORADO EN EL TITULO DE SECCION]
    styles.add(ParagraphStyle(name='TituloPrincipal', fontSize=10, fontName='Times-Bold', spaceAfter=2, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO))
    styles.add(ParagraphStyle(name='TituloSeccion', fontSize=10, fontName='Times-Bold', spaceBefore=6, spaceAfter=2, # Reducido spaceBefore
                             textColor=colors.white, # Cambiado a BLANCO para mayor contraste
                             backColor=COLOR_VERDE_PRINCIPAL, # Usamos el verde principal para el fondo del título
                             borderPadding=3,
                             borderColor=COLOR_VERDE_OSCURO, # El borde puede ser más oscuro
                             borderWidth=1,
                             borderRadius=3))

    styles.add(ParagraphStyle(name='Etiqueta', fontSize=9.5, fontName='Times-Bold', textColor=COLOR_LABEL, leading=12))
    styles.add(ParagraphStyle(name='Dato', fontSize=9.5, fontName='Times-Roman', textColor=colors.black, leading=11, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='DatoCompacto', fontSize=9.5, fontName='Times-Roman', textColor=colors.black, leading=9.5, alignment=TA_JUSTIFY))


    def format_list(data_list):
        if not data_list:
            return Paragraph("—", styles['Dato'])

        color_check = COLOR_VERDE_PRINCIPAL.hexval()
        items = [f'<font face="Times-Roman" size="9.5" color="{color_check}">\u2713</font> <font face="Times-Roman" color="{colors.black.hexval()}">{item}</font>' for item in data_list if item]

        return Paragraph("<br/>".join(items), styles['DatoCompacto'])


    def crear_seccion_recuadro(titulo, datos_dict):
             elements.append(Paragraph(titulo, styles['TituloSeccion']))

             table_data = []
             for etiqueta, dato in datos_dict.items():
                 if isinstance(dato, list):
                     formato_dato = format_list(dato)
                 else:
                     formato_dato = Paragraph(f"{dato}", styles['Dato'])

                 table_data.append([
                     Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                     formato_dato
                 ])

             section_table = Table(table_data, colWidths=[4.5*cm, None])
             section_table.setStyle(TableStyle([
                 ('BACKGROUND', (0, 0), (0, -1), COLOR_FONDO_DATO),
                 ('BACKGROUND', (1, 0), (1, -1), colors.white),
                 ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                 ('VALIGN', (0,0), (-1,-1), 'TOP'),
                 ('LEFTPADDING', (0,0), (-1,-1), 5),
                 ('INNERGRID', (0,0), (-1,-1), 0.25, COLOR_BORDE),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                 ('TOPPADDING', (0, 0), (-1, -1), 2),
             ]))
             elements.append(section_table)
             elements.append(Spacer(1, 0.3 * cm))
             return elements


    def add_watermark(canvas, doc):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            page_width, page_height = doc.pagesize
            img_width = 8 * cm
            img_height = 8 * cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.saveState()
            canvas.setFillAlpha(0.08)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()

    doc.onFirstPage = add_watermark
    doc.onLaterPages = add_watermark
    CONTENT_WIDTH = DOC_WIDTH - (2 * 1.0 * cm)


    # --- HEADER PROFESIONAL (Nombre de la Clínica Añadido) ---
    logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_cit = Image(logo_cit_path, width= 2 * cm, height=2 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])

    header_data = [
        [logo_cit,
         Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA",
                   ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    # Se ajusta la tabla para centrar el nombre de la clínica y la etiqueta de Historia Clínica
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO), # Línea más fina y oscura
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))


    # --- 1. DATOS DE IDENTIFICACIÓN Y MOTIVO DE CONSULTA (Separadores // Eliminados) ---
    elements.append(Paragraph("DATOS DE IDENTIFICACIÓN Y MOTIVO DE CONSULTA", styles['TituloSeccion']))

    datos_id_data = [
        [Paragraph("<b>Nombre Completo:</b>", styles['Etiqueta']),
         Paragraph(f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno or ''} ({paciente.genero}, {paciente.edad} años)", styles['Dato'])],

        # [MEJORA 2: Se reemplaza '//' por '; ' y etiquetas en negrita]
        [Paragraph("<b>Fecha Nacimiento:</b>", styles['Etiqueta']),
         Paragraph(f"{safe_str(paciente.fecha_nacimiento)}; <b>Edo. Civil:</b> {safe_str(paciente.Estado_Civil)}; <b>Ocupación:</b> {safe_str(paciente.Ocupacion)}", styles['DatoCompacto'])],

        # [MEJORA 2: Se reemplaza '//' por '; ' y etiquetas en negrita]
        [Paragraph("<b>Residencia:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Direccción:</b>{safe_str(paciente.direccion)}; <b>Nacionalidad:</b> {safe_str(paciente.Nacionalidad)}; <b>N°:</b> {safe_str(historia_clinica.no_historia_clinica)}", styles['DatoCompacto'])],

        [Paragraph("<b>Motivo Consulta:</b>", styles['Etiqueta']),
         Paragraph(safe_str(historia_clinica.motivo_consulta), styles['Dato'])],

        [Paragraph("<b>Enfermedad Actual:</b>", styles['Etiqueta']),
         Paragraph(safe_str(historia_clinica.enfermedad_actual), styles['Dato'])],
    ]

    datos_id_table = Table(datos_id_data, colWidths=[4.0*cm, None], hAlign='LEFT')
    datos_id_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(datos_id_table)
    elements.append(Spacer(1, 0.5 * cm))


    # --- 2. ANTECEDENTES (Separadores // Eliminados) ---

    elements.append(Paragraph("ANTECEDENTES HEREDOFAMILIARES / PERSONALES", styles['TituloSeccion']))

    antecedentes_table_data = [
        # A. Heredofamiliares
        [Paragraph("<b>A. HEREDOFAMILIARES:</b>", styles['Etiqueta']), format_list(historia_clinica.Antecedentes_familiares)],

        # B. Hábitos Tóxicos
        [Paragraph("<b>B. HÁBITOS TÓXICOS:</b>", styles['Etiqueta']), format_list(historia_clinica.habitos_toxicos)],

        # C. Higiene y Vivienda (Reemplazo de '//' por '; ' y '<br/>')
        [Paragraph("<b>C. HIGIENE/VIVIENDA:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Baño:</b> {safe_str(historia_clinica.baño_diario)}; <b>Dental:</b> {safe_str(historia_clinica.aseo_dental)}"
                   f"<br/><b>Viv. Tipo:</b> {safe_str(historia_clinica.tipo_vivienda)}; <b>Tamaño:</b> {safe_str(historia_clinica.tamanio_vivienda)}", styles['DatoCompacto'])],

        # D. Fisiológicos (Reemplazo de '//' por '; ' y '<br/>')
        [Paragraph("<b>D. FISIOLÓGICOS:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Alimentación:</b> {safe_str(historia_clinica.Allimentación)}; <b>Agua:</b> {safe_str(historia_clinica.Ingesta_Agua)} L"
                   f"<br/><b>Catarsis:</b> {safe_str(historia_clinica.Catarsis)}; <b>Somnia:</b> {safe_str(historia_clinica.Somnia)}", styles['DatoCompacto'])],

        # E. Patológicos (Infancia/Adulto)
        [Paragraph("<b>E. PATOLÓGICOS:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Infancia:</b> {safe_str(historia_clinica.Infancia)}; <b>Adulto:</b> {safe_str(historia_clinica.Adulto)}", styles['Dato'])],

        # F. Patologías Comunes
        [Paragraph("<b>F. PATOLOGÍAS COMUNES:</b>", styles['Etiqueta']), format_list(historia_clinica.Patologias)],

        # G. Quirúrgicos/Trauma (Reemplazo de '//' por '; ' y '<br/>')
        [Paragraph("<b>G. QUIÚRGICOS / TRAUMA:</b>", styles['Etiqueta']),
         Paragraph(f"<b>Operado:</b> {'Sí' if historia_clinica.ha_sido_operado else 'No'} <b>Fecha:</b> {safe_str(historia_clinica.fecha_operacion)}"
                   f"<br/><b>Trauma:</b> {safe_str(historia_clinica.traumatismo_o_fractura)}", styles['DatoCompacto'])],
    ]

    antecedentes_table = Table(antecedentes_table_data, colWidths=[4.0*cm, None], hAlign='LEFT')
    antecedentes_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(antecedentes_table)
    elements.append(Spacer(1, 0.3 * cm))

    # --- 3. ANTECEDENTES GINECO-OBSTÉTRICOS (Separadores // Eliminados) ---

    if paciente.genero in ['Femenino', 'femenino']:
        elements.append(Paragraph("3. GINECO-OBSTÉTRICOS", styles['TituloSeccion']))

        ginecologicos_data = [
            # Fila 1: Fechas y Menarquia
            [Paragraph("<b>FUM:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.fum), styles['Dato']),
             Paragraph("<b>FPP:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.fpp), styles['Dato']),
             Paragraph("<b>Menarquia:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.menarquia), styles['Dato'])],

            # Fila 2: Gestas y Ritmo (Reemplazo de '//' por ' / ')
            [Paragraph("<b>G/P/C/A:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinica.gestas)} / {safe_str(historia_clinica.partos)} / {safe_str(historia_clinica.cesareas)} / {safe_str(historia_clinica.abortos)}", styles['Dato']),
             Paragraph("<b>Ritmo Menstrual:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.rm_rit_menstr), styles['Dato']),
             Paragraph("<b>IRS/Parejas:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinica.irs)} / {safe_str(historia_clinica.no_de_parejas)}", styles['Dato'])],

            # Fila 3: Anticonceptivos (Reemplazo de '//' por ' / ')
            [Paragraph("<b>Anticonceptivos:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.anticonceptivos), styles['Dato']),
             Paragraph("<b>Tipo/Tiempo:</b>", styles['Etiqueta']), Paragraph(f"{safe_str(historia_clinica.anticonceptivos_tipo)} / {safe_str(historia_clinica.anticonceptivos_tiempo)}", styles['Dato']),
             Paragraph("<b>Cirugía:</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.cirugia_ginecologica), styles['Dato'])],
        ]

        ginecologicos_table = Table(ginecologicos_data, colWidths=[1.8*cm, 2.5*cm, 1.8*cm, 2.5*cm, 1.8*cm, 2.4*cm], hAlign='LEFT')
        ginecologicos_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
            ('BACKGROUND', (0, 0), (0, -1), COLOR_VERDE_ENCABEZADO),
            ('BACKGROUND', (2, 0), (2, -1), COLOR_VERDE_ENCABEZADO),
            ('BACKGROUND', (4, 0), (4, -1), COLOR_VERDE_ENCABEZADO),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('BACKGROUND', (3, 0), (3, -1), colors.white),
            ('BACKGROUND', (5, 0), (5, -1), colors.white),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(ginecologicos_table)
        elements.append(Spacer(1, 0.3 * cm))

    # --- Campo Comentarios Finales ---
    elements.append(Paragraph("COMENTARIOS ADICIONALES", styles['TituloSeccion']))
    elements.append(Paragraph(safe_str(historia_clinica.comentarios), styles['Dato']))
    elements.append(Spacer(1, 0.3 * cm))

    # doc.build(elements) # Esto debe estar al final de la función HistorialClinicoPDF

    ############################
    ######################
    ###########
    ###3
    ##

    def crear_seccion_recuadro(titulo, datos_dict):
        # Firma: 2 ARGUMENTOS (Titulo, Diccionario de Datos)

        # 1. Título
        elements.append(Paragraph(titulo, styles['TituloSeccion']))

        table_data = []

        # 2. Llenar la tabla con Etiqueta (columna 1) y Valor (columna 2)
        for etiqueta, dato in datos_dict.items():
            if isinstance(dato, list):
                # Si el dato es una lista (ej. Antecedentes), se usa una función de formato de lista
                formato_dato = format_list(dato)
            else:
                # Si es texto (incluyendo el campo de Comentarios/Hallazgos que agregamos)
                formato_dato = Paragraph(f"{dato}", styles['Dato'])

            table_data.append([
                Paragraph(f"<b>{etiqueta}:</b>", styles['Etiqueta']),
                formato_dato
            ])

        # 3. Crear y aplicar estilos a la tabla
        section_table = Table(table_data, colWidths=[4.5*cm, None])
        section_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), COLOR_FONDO_DATO),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('INNERGRID', (0,0), (-1,-1), 0.25, COLOR_BORDE),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))

        elements.append(section_table)
        elements.append(Spacer(1, 0.3 * cm))
        return elements


    def crear_seccion_aparato(titulo, datos_sintomas, comentario_valor):
        # Firma: 3 ARGUMENTOS (Titulo, Diccionario de Síntomas, Valor del Comentario)

        # 1. Preparar lista de SÍNTOMAS seleccionados (Formato Checkmark Verde)
        sintomas_seleccionados = [
            label for label, valor in datos_sintomas.items() if valor == "Sí"
        ]

        if not sintomas_seleccionados:
            sintomas_list_para = Paragraph("— Ningún síntoma reportado. —", styles['DatoCompacto'])
        else:
            # Usa la función format_list para aplicar checkmarks
            sintomas_list_para = format_list(sintomas_seleccionados)

        # 2. Preparar COMENTARIOS
        comentarios_para = Paragraph(safe_str(comentario_valor), styles['DatoCompacto'])

        # 3. Datos de la tabla (Sintomas | Comentarios)
        table_data = [
            [
                Paragraph("<b>Síntomas Reportados:</b>", styles['Etiqueta']),
                Paragraph("<b>Comentarios / Hallazgos:</b>", styles['Etiqueta'])
            ],
            [
                sintomas_list_para,
                comentarios_para
            ]
        ]

        # 4. Título de la Sección
        elements.append(Paragraph(titulo, styles['TituloSeccion']))

        # 5. Tabla Combinada (Dos columnas: Síntomas y Comentarios)
        section_table = Table(table_data, colWidths=[6.5*cm, None])
        section_table.setStyle(TableStyle([
            # Encabezado (Etiquetas)
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_LABEL),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),

            # Celdas de Datos
            ('BACKGROUND', (0, 1), (0, 1), colors.white),
            ('BACKGROUND', (1, 1), (1, 1), colors.white),

            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),

            # Bordes para el recuadro
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ]))

        elements.append(section_table)
        elements.append(Spacer(1, 0.2 * cm))
        return elements

    #
    ######33
    ############3
    ###################
    ###########################3


# --- INICIO DE LA SEGUNDA PÁGINA DEL PDF (Variables corregidas) ---

# ... (Sección de Header y Título Principal se mantiene igual) ...

    elements.append(PageBreak())

    # Repetir el Header (Asumiendo que no se usan PageTemplates)
    logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_cit = Image(logo_cit_path, width=2* cm, height=2 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])
    header_data = [
        [logo_cit,
         Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA",
                   ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph("INTERROGATORIO POR APARATOS Y SISTEMAS", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # 5. Cuestionario del Sistema Digestivo (Variables correctas)
    datos_digestivo = {
        "Halitosis": "Sí" if historia_clinica.digest_halitosis else "No",
        "Boca seca": "Sí" if historia_clinica.digest_boca_seca else "No",
        "Dificultad para masticar": "Sí" if historia_clinica.digest_masticacion else "No",
        "Disfagia (dificultad para tragar)": "Sí" if historia_clinica.digest_disfagia else "No",
        "Pirosis (acidez estomacal)": "Sí" if historia_clinica.digest_pirosis else "No",
        "Náuseas": "Sí" if historia_clinica.digest_nausea else "No",
        "Vómito o hematemesis": "Sí" if historia_clinica.digest_vomito_hematemesis else "No",
        "Cólicos": "Sí" if historia_clinica.digest_colicos else "No",
        "Dolor abdominal": "Sí" if historia_clinica.digest_dolor_abdominal else "No",
        "Meteorismo (gases)": "Sí" if historia_clinica.digest_meteorismo else "No",
        "Flatulencias": "Sí" if historia_clinica.digest_flatulencias else "No",
        "Constipación (estreñimiento)": "Sí" if historia_clinica.digest_constipacion else "No",
        "Diarrea": "Sí" if historia_clinica.digest_diarrea else "No",
        "Rectorragias": "Sí" if historia_clinica.digest_rectorragias else "No",
        "Melenas": "Sí" if historia_clinica.digest_melenas else "No",
        "Pujo": "Sí" if historia_clinica.digest_pujo else "No",
        "Tenesmo": "Sí" if historia_clinica.digest_tenesmo else "No",
        "Ictericia": "Sí" if historia_clinica.digest_ictericia else "No",
        "Coluria": "Sí" if historia_clinica.digest_coluria else "No",
        "Acolia": "Sí" if historia_clinica.digest_acolia else "No",
        "Prurito cutáneo": "Sí" if historia_clinica.digest_prurito_cutaneo else "No",
        "Hemorragias": "Sí" if historia_clinica.digest_hemorragias else "No",
        "Prurito anal": "Sí" if historia_clinica.digest_prurito_anal else "No",
        "Hemorroides": "Sí" if historia_clinica.digest_hemorroides else "No",
    }
    crear_seccion_aparato("APARATO DIGESTIVO", datos_digestivo, historia_clinica.Comentarios_digestivo)


    # [AJUSTE DE VARIABLES PULSOS]: me_pulso_xxx_derecho cambia a pulso_xxx


    # [AJUSTE DE VARIABLES CARDIO]: Los síntomas cardiovasculares ahora usan los nombres del modelo.
    datos_cardiovascular = {
        "Tos seca": "Sí" if historia_clinica.cardio_tos_seca else "No",
        "Tos espasmodica": "Sí" if historia_clinica.cardio_tos_espasmodica else "No",
        "Hemoptisis": "Sí" if historia_clinica.cardio_hemoptisis else "No",
        "Dolor precordial": "Sí" if historia_clinica.cardio_dolor_precordial else "No",
        "Palpitaciones": "Sí" if historia_clinica.cardio_palpitaciones else "No",
        "Cianosis": "Sí" if historia_clinica.cardio_cianosis else "No",
        "Edema": "Sí" if historia_clinica.cardio_edema else "No",
        "Acúfenos": "Sí" if historia_clinica.cardio_acufenos else "No",
        "Fosfenos": "Sí" if historia_clinica.cardio_fosfenos else "No",
        "Síncope": "Sí" if historia_clinica.cardio_sincope else "No",
        "Lipotimia": "Sí" if historia_clinica.cardio_lipotimia else "No",
        "Cefaleas": "Sí" if historia_clinica.cardio_cefaleas else "No",
    }
    crear_seccion_aparato("APARATO CARDIOVASCULAR", datos_cardiovascular, historia_clinica.Comentarios_cardio)


    # 7. Cuestionario del Sistema Respiratorio (Variables correctas)
    datos_respiratorio = {
        "Tos": "Sí" if historia_clinica.resp_tos else "No",
        "Disnea (dificultad para respirar)": "Sí" if historia_clinica.resp_disnea else "No",
        "Dolor torácico": "Sí" if historia_clinica.resp_dolor_toracico else "No",
        "Hemoptisis (sangre al toser)": "Sí" if historia_clinica.resp_hemoptisis else "No",
        "Cianosis": "Sí" if historia_clinica.resp_cianosis else "No",
        "Vómica (expulsión de pus al toser)": "Sí" if historia_clinica.resp_vomica else "No",
        "Alteraciones de la voz": "Sí" if historia_clinica.resp_alteraciones_voz else "No",
    }
    crear_seccion_aparato("APARATO RESPIRATORIO", datos_respiratorio, historia_clinica.Comentarios_respiratorio)


    # 8. Aparato Genital
    datos_genital = {
        "Criptorquidea": "Sí" if historia_clinica.genital_criptorquidea else "No",
        "Fimosis": "Sí" if historia_clinica.genital_fimosis else "No",
        "Función sexual": "Sí" if historia_clinica.genital_funcion_sexual else "No",
        "Sangrado genital": "Sí" if historia_clinica.genital_sangrado_genital else "No",
        "Flujo o leucorrea": "Sí" if historia_clinica.genital_flujo_leucorrea else "No",
        "Dolor ginecológico": "Sí" if historia_clinica.genital_dolor_ginecologico else "No",
        "Prurito vulvar": "Sí" if historia_clinica.genital_prurito_vulvar else "No",
    }
    crear_seccion_aparato("APARATO GENITAL", datos_genital, historia_clinica.Comentarios_genital)


    # Aparato Urinario

    # Alteraciones de la Micción (Solo checkboxes)
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
    crear_seccion_aparato("APARATO URINARIO: Alteraciones de la Micción", datos_alteraciones_miccion, historia_clinica.Comentarios_urinario)

    # Características de la Orina y Síntomas Asociados (Usando crear_seccion_recuadro original)
    datos_caracteristicas_orina = {
        "Características de Orina (Vol/Color/Olor/Asp.)": (
        f"<b>Vol:</b> {safe_str(historia_clinica.urin_volumen_orina)} ; "
        f"<b>Color:</b> {safe_str(historia_clinica.urin_color_orina)}; "
        f"<b>Olor:</b> {safe_str(historia_clinica.urin_olor_orina)}; "
        f"<b>Aspecto:</b> {safe_str(historia_clinica.urin_aspecto_orina)}"
    ),
        "Dolor lumbar": "Sí" if historia_clinica.urin_dolor_lumbar else "No",
        "Edema Palpebral Sup/Inf": "Sí" if historia_clinica.urin_edema_palpebral_sup or historia_clinica.urin_edema_palpebral_inf else "No",
        "Edema renal": "Sí" if historia_clinica.urin_edema_renal else "No",
        "Hipertensión arterial": "Sí" if historia_clinica.urin_hipertension_arterial else "No",
        "Datos clínicos de anemia": "Sí" if historia_clinica.urin_datos_clinicos_anemia else "No",
    }
    crear_seccion_recuadro("APARATO URINARIO: Características y Síntomas", datos_caracteristicas_orina)


    # 9. Aparato Hematológico
    # [AJUSTE DE VARIABLES HEMATO]: Las variables Palidez, Astenia, Adinamia, Otros son checkboxes.
    datos_hematologico = {
        "Palidez": "Sí" if historia_clinica.Palidez else "No",
        "Astenia": "Sí" if historia_clinica.Astenia else "No",
        "Adinamia": "Sí" if historia_clinica.Adinamia else "No",
        "Otros (Especifique)": safe_str(historia_clinica.Otros), # Este campo es de texto libre
        "Hemorragias": "Sí" if historia_clinica.hemato_hemorragias else "No",
        "Adenopatías": "Sí" if historia_clinica.hemato_adenopatias else "No",
        "Esplenomegalia": "Sí" if historia_clinica.hemato_esplenomegalia else "No",
    }
    # Como hay un campo de texto libre ('Otros') que no es Sí/No, usamos la función original crear_seccion_recuadro
    crear_seccion_aparato("APARATO HEMATOLÓGICO", datos_hematologico, historia_clinica.Comentarios_anemia)


    # Subsección: Endocrino
    datos_endocrino = {
        "Bocio": "Sí" if historia_clinica.endocr_bocio else "No",
        "Letargia": "Sí" if historia_clinica.endocr_letargia else "No",
        "Bradipsiquia (lentitud de ideas)": "Sí" if historia_clinica.endocr_bradipsiquia_idia else "No",
        "Intolerancia al calor o frío": "Sí" if historia_clinica.endocr_intolerancia_calor_frio else "No",
        "Nerviosismo": "Sí" if historia_clinica.endocr_nerviosismo else "No",
        "Hiperquinesis": "Sí" if historia_clinica.endocr_hiperquinesis else "No",
        "Caracteres sexuales": "Sí" if historia_clinica.endocr_caracteres_sexuales else "No",
        "Galactorrea": "Sí" if historia_clinica.endocr_galactorrea else "No",
        "Amenorrea": "Sí" if historia_clinica.endocr_amenorrea else "No",
        "Ginecomastia": "Sí" if historia_clinica.endocr_ginecomastia else "No",
        "Obesidad": "Sí" if historia_clinica.endocr_obesidad else "No",
        "Ruborización": "Sí" if historia_clinica.endocr_ruborizacion else "No",
    }
    crear_seccion_aparato("APARATO ENDOCRINO", datos_endocrino, historia_clinica.Comentarios_endocrino)

    # 10. Exploración de Cuello (Variables correctas)
    elements.append(Paragraph("EXPLORACIÓN DE CUELLO", styles['TituloSeccion']))
    # [AJUSTE DE ESTILO]: Manteniendo los colores verdes
    cuello_data = [
        [Paragraph("<b>Característica</b>", styles['Etiqueta']), Paragraph("<b>Hallazgos</b>", styles['Etiqueta'])],
        [Paragraph("<b>Tiroides</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.cuello_tiroides), styles['DatoCompacto'])],
        [Paragraph("<b>Músculos</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.cuello_musculos), styles['DatoCompacto'])],
        [Paragraph("<b>Ganglios Linfáticos</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.cuello_ganglios_linfaticos), styles['DatoCompacto'])],
    ]
    cuello_table = Table(cuello_data, colWidths=[3.5*cm, None])
    cuello_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Alineación izquierda para las etiquetas
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # Alineación centrada para los datos
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(cuello_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(PageBreak())

    # --- FIN DEL DOCUMENTO ---
    # doc.build(elements)



    # --- NUEVAS SECCIONES ---
        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, TituloSeccion: EXPLORACIÓN FÍSICA: COLUMNA Y MIEMBROS SUPERIORES

    # 11. Exploración Física: Columna y Miembros Superiores
 # --- INICIO DE LA NUEVA PÁGINA: APLICACIÓN DEL ENCABEZADO Y MARCA DE AGUA ---

# 1. Aplicación del Encabezado (Logo y Título)
# ----------------------------------------------------------------------
# Elementos de inicio
# ----------------------------------------------------------------------
    logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_cit = Image(logo_cit_path, width=2 * cm, height=2 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])

    header_data = [
        [logo_cit,
        Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA",
                    ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))

    # 2. Título principal de la sección
    elements.append(Paragraph("EXPLORACIÓN FÍSICA: COLUMNA Y MIEMBROS SUPERIORES", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # --- 3. CONTENIDO DE LAS TABLAS ADAPTADAS (INCLUIDO EN LA RESPUESTA ANTERIOR) ---

    # 1. Exploración Física: Columna Vertebral
    # INICIO KeepTogether
    columna_block = []
    columna_block.append(Paragraph("COLUMNA VERTEBRAL", styles['TituloSeccion']))
    columna_data = [
        [Paragraph("<b>Región</b>", styles['Etiqueta']), Paragraph("<b>Ascendente</b>", styles['Etiqueta']), Paragraph("<b>Descendente</b>", styles['Etiqueta']), Paragraph("<b>Observaciones</b>", styles['Etiqueta'])],
        [Paragraph("<b>Cervical</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.ecv_cervical_asc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_cervical_desc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_cervical_obs), styles['DatoCompacto'])],
        [Paragraph("<b>Dorsal</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.ecv_dorsal_asc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_dorsal_desc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_dorsal_obs), styles['DatoCompacto'])],
        [Paragraph("<b>Lumbo Sacra</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.ecv_lumbosacra_asc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_lumbosacra_desc), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.ecv_lumbosacra_obs), styles['DatoCompacto'])],
    ]
    columna_table = Table(columna_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, CONTENT_WIDTH - 7.5*cm])
    columna_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    columna_block.append(columna_table)
    columna_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(columna_block))
    # FIN KeepTogether


    # 2. Exploración Física: Miembros Superiores (Hombros)
    # INICIO KeepTogether
    miembros_superiores_block = []
    miembros_superiores_block.append(Paragraph("MIEMBROS SUPERIORES (Hombros)", styles['TituloSeccion']))
    miembros_superiores_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Hombros CS</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.mmss_hombros_cs_ad), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cs_ab), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cs_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cs_e), styles['DatoCompacto'])],
        [Paragraph("<b>Hombros CV</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.mmss_hombros_cv_ad), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cv_ab), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cv_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.mmss_hombros_cv_e), styles['DatoCompacto'])],
    ]
    col_width_ms = CONTENT_WIDTH / 5 # Reutilizando el cálculo de ancho
    miembros_superiores_table = Table(miembros_superiores_data, colWidths=[col_width_ms, col_width_ms, col_width_ms, col_width_ms, col_width_ms])
    miembros_superiores_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    miembros_superiores_block.append(miembros_superiores_table)
    miembros_superiores_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(miembros_superiores_block))
    # FIN KeepTogether


    # 3. Evaluación articular de MMSS Codo y Muñeca
    # INICIO KeepTogether
    articular_block = []
    articular_block.append(Paragraph("EVALUACIÓN ARTICULAR MMSS (Codo y Muñeca)", styles['TituloSeccion']))
    articular_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Pronación (P)</b>", styles['Etiqueta']), Paragraph("<b>Supinación (S)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Codo</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_codo_e), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_codo_f), styles['DatoCompacto']), Paragraph("-", styles['DatoCompacto']), Paragraph("-", styles['DatoCompacto'])],
        [Paragraph("<b>Muñeca</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_muneca_e), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_muneca_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_muneca_p), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_muneca_s), styles['DatoCompacto'])],
    ]
    articular_table = Table(articular_data, colWidths=[col_width_ms, col_width_ms, col_width_ms, col_width_ms, col_width_ms])
    articular_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    articular_block.append(articular_table)
    articular_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(articular_block))
    # FIN KeepTogether


    # 4. Evaluación articular de MMSS del pulgar
    # INICIO KeepTogether
    pulgar_block = []
    pulgar_block.append(Paragraph("EVALUACIÓN ARTICULAR MMSS (Pulgar)", styles['TituloSeccion']))
    pulgar_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Pulgar</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_pulgar_ab), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_pulgar_ad), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_pulgar_e), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_pulgar_f), styles['DatoCompacto'])],
    ]
    pulgar_table = Table(pulgar_data, colWidths=[col_width_ms, col_width_ms, col_width_ms, col_width_ms, col_width_ms])
    pulgar_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    pulgar_block.append(pulgar_table)
    pulgar_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(pulgar_block))
    # FIN KeepTogether


    # 5. Evaluación articular de MMSS Dedos
    # INICIO KeepTogether
    dedos_block = []
    dedos_block.append(Paragraph("EVALUACIÓN ARTICULAR MMSS (Dedos)", styles['TituloSeccion']))
    dedos_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta']), Paragraph("<b>IFP</b>", styles['Etiqueta'])],
        [Paragraph("<b>Dedos</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_dedos_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_dedos_e), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_dedos_ifp), styles['DatoCompacto'])],
    ]
    col_width_dedos = CONTENT_WIDTH / 4 # Reutilizando el cálculo de ancho
    dedos_table = Table(dedos_data, colWidths=[col_width_dedos, col_width_dedos, col_width_dedos, col_width_dedos])
    dedos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    dedos_block.append(dedos_table)
    dedos_block.append(Spacer(1, 0.5 * cm))
    elements.append(KeepTogether(dedos_block))
    # FIN KeepTogether


    # --- SECCIÓN: Exploración Física: Miembros Inferiores y Nariz ---
    elements.append(Paragraph("EXPLORACIÓN FÍSICA: MIEMBROS INFERIORES Y NARIZ", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # 6. Articulaciones de Miembros Inferiores (Cadera)
    # INICIO KeepTogether
    cadera_block = []
    cadera_block.append(Paragraph("ARTICULACIONES DE MIEMBROS INFERIORES (Cadera)", styles['TituloSeccion']))
    cadera_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Abducción (AB)</b>", styles['Etiqueta']), Paragraph("<b>Aducción (AD)</b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Cadera</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_cadera_ab), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_cadera_ad), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_cadera_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_cadera_e), styles['DatoCompacto'])],
    ]
    cadera_table = Table(cadera_data, colWidths=[col_width_ms, col_width_ms, col_width_ms, col_width_ms, col_width_ms])
    cadera_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    cadera_block.append(cadera_table)
    cadera_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(cadera_block))
    # FIN KeepTogether

    # 7. Evaluación articular del Tobillo
    # INICIO KeepTogether
    tobillo_block = []
    tobillo_block.append(Paragraph("EVALUACIÓN ARTICULAR MMII (Tobillo)", styles['TituloSeccion']))
    tobillo_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Flexión (F)</b>", styles['Etiqueta']), Paragraph("<b>Extensión (E)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Tobillo</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_tobillo_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_tobillo_e), styles['DatoCompacto'])],
    ]
    col_width_tobillo = CONTENT_WIDTH / 3 # Reutilizando el cálculo de ancho
    tobillo_table = Table(tobillo_data, colWidths=[col_width_tobillo, col_width_tobillo, col_width_tobillo])
    tobillo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    tobillo_block.append(tobillo_table)
    tobillo_block.append(Spacer(1, 0.3 * cm))
    elements.append(KeepTogether(tobillo_block))
    # FIN KeepTogether

    # 8. Evaluación articular MMII Subastragalina
    # INICIO KeepTogether
    subastragalina_block = []
    subastragalina_block.append(Paragraph("EVALUACIÓN ARTICULAR MMII (Subastragalina)", styles['TituloSeccion']))
    subastragalina_data = [
        [Paragraph("<b></b>", styles['Etiqueta']), Paragraph("<b>Inversión (I)</b>", styles['Etiqueta']), Paragraph("<b>Eversión (EV)</b>", styles['Etiqueta'])],
        [Paragraph("<b>Subastragalina</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.art_subastragalina_f), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.art_subastragalina_ev), styles['DatoCompacto'])],
    ]
    subastragalina_table = Table(subastragalina_data, colWidths=[col_width_tobillo, col_width_tobillo, col_width_tobillo])
    subastragalina_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    subastragalina_block.append(subastragalina_table)
    subastragalina_block.append(Spacer(1, 0.5 * cm))
    elements.append(KeepTogether(subastragalina_block))
    # FIN KeepTogether

    # 9. Exploración de la cavidad nasal
    # INICIO KeepTogether
    nasal_block = []
    nasal_block.append(Paragraph("EXPLORACIÓN DE LA CAVIDAD NASAL", styles['TituloSeccion']))
    nasal_data = [
        [Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Mucosa</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.nasal_mucosa), styles['DatoCompacto'])],
        [Paragraph("<b>Cornetes</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.nasal_cochas), styles['DatoCompacto'])],
        [Paragraph("<b>Vascularización</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.nasal_vascularizacion), styles['DatoCompacto'])],
    ]
    nasal_table = Table(nasal_data, colWidths=[4.0*cm, CONTENT_WIDTH - 4.0*cm])
    nasal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    nasal_block.append(nasal_table)
    nasal_block.append(Spacer(1, 0.5 * cm))
    elements.append(KeepTogether(nasal_block))
    # FIN KeepTogether

    elements.append(PageBreak())




        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, TituloSeccion: EXPLORACIÓN FÍSICA: PULSOS Y CONCIENCIA
        # 12. Exploración Física: Pulsos y Conciencia
    logo_cit = Image(logo_cit_path, width=1.5 * cm, height=1.5 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])

    header_data = [
        [logo_cit,
        Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA",
                ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Título principal de la sección
    elements.append(Paragraph("Exploración Física: Pulsos, Conciencia y Neurológico", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # ------------------------------------------------------------------
    # SECCIÓN: PULSOS
    # ------------------------------------------------------------------
    pulso_data = [
        [Paragraph("<b>Tipo de pulso</b>", styles['Etiqueta']), Paragraph("<b>Derecho</b>", styles['Etiqueta']), Paragraph("<b>Izquierdo</b>", styles['Etiqueta'])],
        [Paragraph("<b>Carotídeo</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_carotideo_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_carotideo_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Humeral</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_humeral_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_humeral_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Radial</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_radial_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_radial_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Femoral</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_femoral_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_femoral_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Poplíteo</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_popliteo_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_popliteo_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Tibial Posterior</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_tibial_posterior_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_tibial_posterior_izquierdo), styles['DatoCompacto'])],
        [Paragraph("<b>Pedio</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.me_pulso_pedio_derecho), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.me_pulso_pedio_izquierdo), styles['DatoCompacto'])],
    ]
    # Calculamos colWidths basado en el CONTENT_WIDTH
    col_ancho_pulso = (CONTENT_WIDTH - 6 * cm) / 2
    pulso_table = Table(pulso_data, colWidths=[6 * cm, col_ancho_pulso, col_ancho_pulso])
    pulso_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Título de la tabla en VERDE OSCURO
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Primera columna a la izquierda
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'), # Columnas de datos al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO), # Fondo de etiquetas en columna 1
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Agrupamos el título y la tabla para KeepTogether
    pulso_block = [
        Paragraph("Exploración Física: Pulsos y Conciencia", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        pulso_table
    ]
    elements.append(KeepTogether(pulso_block))
    elements.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # SECCIÓN: OTROS DATOS (Ascitis y Conciencia)
    # ------------------------------------------------------------------
    datos_otros = {
        "Ascitis": safe_str("Sí" if historia_clinica.ascitis else "No"),
        "Estado de Conciencia": safe_str(historia_clinica.Estado_Conciencia),
    }

    # La función crear_seccion_recuadro (que asumo que tienes definida) debe ser reemplazada
    # por una tabla para asegurar la consistencia del estilo:

    # Transformar diccionario a lista de listas para la tabla
    otros_data = [[Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])]]
    for key, value in datos_otros.items():
        otros_data.append([Paragraph(f"<b>{key}</b>", styles['Etiqueta']), Paragraph(value, styles['DatoCompacto'])])

    otros_table = Table(otros_data, colWidths=[4.0 * cm, CONTENT_WIDTH - 4.0 * cm])
    otros_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Título de la tabla en VERDE OSCURO
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # Columna de datos al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO), # Fondo de etiquetas en columna 1
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    otros_block = [
        Paragraph("Otros (Ascitis y Conciencia)", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        otros_table
    ]
    elements.append(KeepTogether(otros_block))
    elements.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # SECCIÓN: Cuestionario Glasgow y Visual
    # ------------------------------------------------------------------
    elements.append(Paragraph("Cuestionario Glasgow y Visual", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # Subsección: Escala de Glasgow
    glasgow_data = [
        [Paragraph("<b>Prueba</b>", styles['Etiqueta']), Paragraph("<b>Respuesta</b>", styles['Etiqueta']), Paragraph("<b>Puntuación</b>", styles['Etiqueta'])],
        [Paragraph("<b>Apertura de Ojos</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.glasgow_apertura_ojos_respuesta), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.glasgow_apertura_ojos_puntuacion), styles['DatoCompacto'])],
        [Paragraph("<b>Respuesta Verbal</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.glasgow_respuesta_verbal_respuesta), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.glasgow_respuesta_verbal_puntuacion), styles['DatoCompacto'])],
        [Paragraph("<b>Respuesta Motora</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.glasgow_respuesta_motora_respuesta), styles['DatoCompacto']), Paragraph(safe_str(historia_clinica.glasgow_respuesta_motora_puntuacion), styles['DatoCompacto'])],
    ]
    col_ancho_glasgow_prueba = 5 * cm
    col_ancho_glasgow_datos = (CONTENT_WIDTH - col_ancho_glasgow_prueba) / 2
    glasgow_table = Table(glasgow_data, colWidths=[col_ancho_glasgow_prueba, col_ancho_glasgow_datos, col_ancho_glasgow_datos])
    glasgow_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Título de la tabla en VERDE OSCURO
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Primera columna a la izquierda
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'), # Columnas de datos al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO), # Fondo de etiquetas en columna 1
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    glasgow_block = [
        Paragraph("Escala de Glasgow", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        glasgow_table
    ]
    elements.append(KeepTogether(glasgow_block))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Reflejo Fotomotor
    fotomotor_data = [
        [Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Según el tamaño</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.reflejo_fotomotor_tamano), styles['DatoCompacto'])],
        [Paragraph("<b>Según relación entre ellas</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.reflejo_fotomotor_relaciones), styles['DatoCompacto'])],
        [Paragraph("<b>Según respuesta a la luz</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.reflejo_fotomotor_respuestas_luz), styles['DatoCompacto'])],
    ]
    fotomotor_table = Table(fotomotor_data, colWidths=[6 * cm, CONTENT_WIDTH - 6 * cm])
    fotomotor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    fotomotor_block = [
        Paragraph("Reflejo Fotomotor: (Reactividad Pupilar)", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        fotomotor_table
    ]
    elements.append(KeepTogether(fotomotor_block))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Exploración de Pares Craneales (Oculomotores)
    pares_craneales_data = [
        [Paragraph("<b>Par Craneal</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>III (Oculomotor)</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_iii_oculomotor), styles['DatoCompacto'])],
        [Paragraph("<b>IV (Patético)</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_iv_patetico), styles['DatoCompacto'])],
        [Paragraph("<b>VI (Motor Ocular Externo)</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_vi_motor_ocular_externo), styles['DatoCompacto'])],
    ]
    pares_craneales_table = Table(pares_craneales_data, colWidths=[6 * cm, CONTENT_WIDTH - 6 * cm])
    pares_craneales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    pares_craneales_block = [
        Paragraph("Exploración de Pares Craneales (Oculomotores)", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        pares_craneales_table
    ]
    elements.append(KeepTogether(pares_craneales_block))
    elements.append(Spacer(1, 0.5 * cm))


    # ------------------------------------------------------------------
    # SECCIÓN: Campos Visuales y Retina
    # ------------------------------------------------------------------
    # El título principal se repite en tu código, lo mantengo:
    elements.append(Paragraph("Cuestionario Glasgow y Visual", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # Subsección: Campos Visuales
    campos_visuales_data = [
        [Paragraph("<b>Par Craneal</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>III Oculomotor</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_iii_oculomotor_cv), styles['DatoCompacto'])],
        [Paragraph("<b>IV Patético</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_iv_patetico_cv), styles['DatoCompacto'])],
        [Paragraph("<b>VI Motor Ocular Externo</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.par_craneal_vi_motor_ocular_externo_cv), styles['DatoCompacto'])],
    ]
    campos_visuales_table = Table(campos_visuales_data, colWidths=[6 * cm, CONTENT_WIDTH - 6 * cm])
    campos_visuales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    campos_visuales_block = [
        Paragraph("Campos Visuales", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        campos_visuales_table
    ]
    elements.append(KeepTogether(campos_visuales_block))
    elements.append(Spacer(1, 0.5 * cm))

    # Subsección: Evaluación de la Retina
    retina_data = [
        [Paragraph("<b>Aspecto de la Retina</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Relación Arterio-Venosa</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.retina_relacion_arterio_venosa), styles['DatoCompacto'])],
        [Paragraph("<b>Mácula</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.retina_macula), styles['DatoCompacto'])],
    ]
    retina_table = Table(retina_data, colWidths=[6 * cm, CONTENT_WIDTH - 6 * cm])
    retina_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    retina_block = [
        Paragraph("Evaluación de la Retina", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        retina_table
    ]
    elements.append(KeepTogether(retina_block))
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(PageBreak())

        ###PALBRA CLAVE DE DIVICIÓN: GATO DIVISOR, TituloSeccion: EXPLORACIÓN FÍSICA FINAL

    # Subsección: Hallazgos en la Exploración Visual
# Subsección: Hallazgos en la Exploración Visual
    # Reflejos Osteo Tendinosos Profundos

# --- INICIO DE LA ÚLTIMA PÁGINA: ENCABEZADO Y MARCA DE AGUA ---

# 1. Aplicación del Encabezado (Logo y Título)
    logo_cit = Image(logo_cit_path, width=2 * cm, height=2 * cm) if os.path.exists(logo_cit_path) else Paragraph("", styles['Normal'])

    header_data = [
        [logo_cit,
        Paragraph("<b>CENTRO INTEGRAL TERAPÉUTICO</b><br/>HISTORIA CLÍNICA",
                ParagraphStyle(name='HeaderDetail', fontSize=10, fontName='Times-Roman', spaceAfter=0, alignment=TA_CENTER, textColor=COLOR_VERDE_OSCURO, leading=12))]
    ]
    header_table = Table(header_data, colWidths=[2.0 * cm, CONTENT_WIDTH - 2.0 * cm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, -1), 1, COLOR_VERDE_OSCURO),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))

    # Título principal de la sección
    elements.append(Paragraph("Exploración Física", styles['TituloPrincipal']))
    elements.append(Spacer(1, 0.2 * cm))

    # ------------------------------------------------------------------
    # 1. Exploración Auditiva (Convertida de HTML)
    # ------------------------------------------------------------------
    auditivos_data = [
        [Paragraph("<b>Aspecto</b>", styles['Etiqueta']), Paragraph("<b>Descripción</b>", styles['Etiqueta'])],
        [Paragraph("<b>Conducta Auditiva</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.Conducta_auditiva), styles['DatoCompacto'])],
        [Paragraph("<b>Membrana Timpánica</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.Membrana_timpatica), styles['DatoCompacto'])],
        [Paragraph("<b>Conducción Ósea</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.conduccion_osea), styles['DatoCompacto'])],
        [Paragraph("<b>Conducción Área</b>", styles['Etiqueta']), Paragraph(safe_str(historia_clinica.conduccion_area), styles['DatoCompacto'])],
    ]

    auditivos_table = Table(auditivos_data, colWidths=[6.0 * cm, CONTENT_WIDTH - 6.0 * cm])
    auditivos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Aplicando estilo consistente
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'), # Columna de datos al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Aplicamos KeepTogether
    auditivos_block = [
        Paragraph("Hallazgos Auditivos", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        auditivos_table
    ]
    elements.append(KeepTogether(auditivos_block))
    elements.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # 2. Reflejos Osteo Tendinosos Profundos
    # ------------------------------------------------------------------

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
            if valor_db and safe_str(str(i)) in safe_str(valor_db):
                fila_datos.append(Paragraph("X", styles['DatoCompacto']))
            else:
                fila_datos.append(Paragraph("", styles['DatoCompacto']))
        table_data_profundos.append(fila_datos)

    # Crear y estilizar la tabla
    col_ancho_reflejo = 6.0 * cm
    col_ancho_valor = (CONTENT_WIDTH - col_ancho_reflejo) / 4
    reflejos_profundos_table = Table(table_data_profundos, colWidths=[col_ancho_reflejo, col_ancho_valor, col_ancho_valor, col_ancho_valor, col_ancho_valor])
    reflejos_profundos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Aplicando estilo consistente
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Reflejo a la izquierda
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'), # Valores al centro
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Aplicamos KeepTogether
    profundos_block = [
        Paragraph("Reflejos Osteo Tendinosos Profundos", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        reflejos_profundos_table
    ]
    elements.append(KeepTogether(profundos_block))
    elements.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # 3. Reflejos Superficiales o Mucocutáneos
    # ------------------------------------------------------------------
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
            if valor_db and safe_str(str(i)) in safe_str(valor_db):
                fila_datos.append(Paragraph("X", styles['DatoCompacto']))
            else:
                fila_datos.append(Paragraph("", styles['DatoCompacto']))
        superficiales_table_data.append(fila_datos)

    superficiales_table = Table(superficiales_table_data, colWidths=[col_ancho_reflejo, col_ancho_valor, col_ancho_valor, col_ancho_valor, col_ancho_valor])
    superficiales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Aplicando estilo consistente
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Aplicamos KeepTogether
    superficiales_block = [
        Paragraph("Reflejos Superficiales o Mucocutáneos", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        superficiales_table
    ]
    elements.append(KeepTogether(superficiales_block))
    elements.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # 4. Reflejos Adicionales (Babinski, etc.)
    # ------------------------------------------------------------------
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
            if valor_db and safe_str(str(i)) in safe_str(valor_db):
                fila_datos.append(Paragraph("X", styles['DatoCompacto']))
            else:
                fila_datos.append(Paragraph("", styles['DatoCompacto']))
        adicionales_table_data.append(fila_datos)

    adicionales_table = Table(adicionales_table_data, colWidths=[col_ancho_reflejo, col_ancho_valor, col_ancho_valor, col_ancho_valor, col_ancho_valor])
    adicionales_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE_ENCABEZADO), # Aplicando estilo consistente
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, COLOR_BORDE),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDE),
        ('BACKGROUND', (0, 1), (0, -1), COLOR_FONDO_DATO),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Aplicamos KeepTogether
    adicionales_block = [
        Paragraph("Reflejos Adicionales (Babinski, etc.)", styles['TituloSeccion']),
        Spacer(1, 0.1 * cm),
        adicionales_table
    ]
    elements.append(KeepTogether(adicionales_block))
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
# 1. Vista para la LISTA/CALENDARIO de la Agenda
@login_required
def agenda_view(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if not is_doctora and not is_farmacia:
        messages.error(request, "No tienes permiso para ver esta página.")
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

    doctor_user_obj = get_doctor_user(request.user)

    if doctor_user_obj:
        # Obtener todas las citas del mes
        citas_mes = Cita.objects.filter(
            doctor=doctor_user_obj,
            fecha__range=[first_day_of_month, last_day_of_month]
        ).order_by('fecha', 'hora_inicio')
    else:
        messages.error(request, "No se encontró un perfil de doctor asociado.")
        return redirect('HomeSinInicio')

    # Separar las citas en dos categorías
    # Se corrige el nombre del campo de 'motivo_cita' a 'motivo'
    citas_suero = citas_mes.filter(motivo='Suero')
    citas_generales = citas_mes.exclude(motivo='Suero')

    cal = calendar.Calendar()
    month_calendar = cal.monthdatescalendar(selected_year, selected_month)

    calendar_days_with_counts = []
    for week in month_calendar:
        week_data = []
        for day_obj in week:
            count_suero = citas_suero.filter(fecha=day_obj).count()
            count_generales = citas_generales.filter(fecha=day_obj).count()

            week_data.append({
                'date': day_obj,
                'is_current_month': day_obj.month == selected_month,
                'is_today': day_obj == date.today(),
                'count_suero': count_suero,
                'count_generales': count_generales,
                'citas_del_dia_suero': citas_suero.filter(fecha=day_obj),
                'citas_del_dia_generales': citas_generales.filter(fecha=day_obj),
            })
        calendar_days_with_counts.append(week_data)

    prev_month_date = first_day_of_month - timedelta(days=1)
    next_month_date = last_day_of_month + timedelta(days=1)

    context = {
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_name': first_day_of_month.strftime('%B'),
        'calendar_days_with_citas': calendar_days_with_counts,
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
@login_required
def crear_cita_view(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if not is_doctora and not is_farmacia:
        messages.error(request, "No tienes permiso para ver esta página.")
        return redirect('HomeSinInicio')

    doctor_user_obj = get_doctor_user(request.user)
    doctor_profile_obj = get_doctor_profile(request.user)

    if not doctor_user_obj or not doctor_profile_obj:
        messages.error(request, "Tu perfil no está completo. No se puede agendar la cita.")
        return redirect('HomeSinInicio')

    if request.method == 'POST':
        form = CitaForm(request.POST)
        if form.is_valid():
            cita = form.save(commit=False)
            cita.doctor = doctor_user_obj
            cita.save()
            messages.success(request, 'Cita creada exitosamente.')
            return redirect('agenda')
        else:
            messages.error(request, 'Hubo un error al crear la cita. Por favor, revisa los datos.')
    else:
        form = CitaForm()
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
    # Verificación de grupos
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if not is_doctora and not is_farmacia:
        messages.error(request, "No tienes permiso para ver esta página.")
        return redirect('HomeSinInicio')

    doctor_user_obj = get_doctor_user(request.user)
    if not doctor_user_obj:
        messages.error(request, "No se encontró un perfil de doctor asociado.")
        return redirect('agenda')

    # Obtener cita
    cita = get_object_or_404(Cita, pk=pk, doctor=doctor_user_obj)

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)

        if form.is_valid():
            cita_editada = form.save(commit=False)

            # Si alguno de los campos de fecha u hora está vacío, conserva los valores originales
            if not request.POST.get('fecha'):
                cita_editada.fecha = cita.fecha
            if not request.POST.get('hora_inicio'):
                cita_editada.hora_inicio = cita.hora_inicio
            if not request.POST.get('hora_fin'):
                cita_editada.hora_fin = cita.hora_fin

            cita_editada.save()
            messages.success(request, 'Cita actualizada exitosamente.')
            return redirect('agenda')
        else:
            messages.error(request, 'Hubo un error al actualizar la cita. Por favor, revisa los datos.')
    else:
        form = CitaForm(instance=cita)

        # Prellenar correctamente las fechas y horas
        if cita.fecha:
            form.fields['fecha'].initial = cita.fecha.strftime('%Y-%m-%d')
        if cita.hora_inicio:
            form.fields['hora_inicio'].initial = cita.hora_inicio.strftime('%H:%M')
        if cita.hora_fin:
            form.fields['hora_fin'].initial = cita.hora_fin.strftime('%H:%M')

        # Filtrar pacientes según doctora responsable
        doctor_profile_obj = get_doctor_profile(request.user)
        if doctor_profile_obj:
            form.fields['paciente'].queryset = Paciente.objects.filter(
                doctor_responsable=doctor_profile_obj
            ).order_by('nombre')
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
    cita = get_object_or_404(Cita, pk=pk)

    # --- NUEVA VERIFICACIÓN DE PERMISOS ---
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()

    # Si el usuario NO es ni Doctora NI Farmacia, le negamos el permiso.
    if not (is_doctora or is_farmacia):
        messages.error(request, 'No tienes los permisos necesarios para eliminar esta cita.')
        return redirect('agenda')

    # Si es Doctora o Farmacia, el código continúa y permite la eliminación.
    if request.method == 'POST':
        cita.delete()
        messages.success(request, 'Cita eliminada exitosamente.')
        return redirect('agenda')

    # Mensaje por si se intenta acceder por GET
    messages.error(request, 'Acción no permitida.')
    return redirect('agenda')





@login_required
def consentimiento_create(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)

    # Lógica para determinar el grupo del usuario
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if request.method == 'POST':
        # Pasa la instancia del paciente al formulario POST
        form = ConsentimientoInformadoForm(request.POST, paciente_instance=paciente)
        if form.is_valid():
            consentimiento = form.save(commit=False)
            consentimiento.paciente = paciente  # Asigna el objeto Paciente
            consentimiento.save()
            return redirect('consentimiento_detail', pk=consentimiento.pk)
    else:
        # Pasa la instancia del paciente al formulario GET
        form = ConsentimientoInformadoForm(paciente_instance=paciente)

    context = {
        'form': form,
        'paciente': paciente,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
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

    doc = SimpleDocTemplate(response, pagesize=portrait(letter),
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
            page_width, page_height = portrait(letter)
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




# ... (importaciones y decorador @login_required)


@login_required
def imprimir_receta_pdf(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    paciente = receta.paciente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receta_{paciente.nombre}.pdf"'

    # 1. ESTILOS UNIFICADOS EN UN SOLO LUGAR
    styles = {
        'HeaderName': ParagraphStyle(name='HeaderName', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#18b1a3'), alignment=1),
        'HeaderCedula': ParagraphStyle(name='HeaderCedula', fontName='Helvetica', fontSize=12, textColor=colors.HexColor("#18b1a3"), alignment=2),
        'PatientLabel': ParagraphStyle(name='PatientLabel', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#18b1a3'), leading=9),
        'PatientData': ParagraphStyle(name='PatientData', fontName='Helvetica', fontSize=8, textColor=colors.black, leading=9),
        'SectionTitle': ParagraphStyle(name='SectionTitle', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#18b1a3'), spaceAfter=3),
        'Normal': ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, spaceAfter=6, leading=10),
        'FooterText': ParagraphStyle(name='FooterText', fontName='Helvetica-Bold', fontSize=12, textColor=colors.white, leading=12),
        'FooterTextTight': ParagraphStyle(name='FooterTextTight', fontName='Helvetica-Bold', fontSize=12, textColor=colors.white, leading=9),
    }

    # 2. LA FUNCIÓN AHORA ACEPTA 'styles' COMO PARÁMETRO
    def draw_background_and_footer(canvas, doc, styles_dict):
        # -- Marca de agua --
        canvas.saveState()
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = ImageReader(logo_path)
            page_width, page_height = doc.width + doc.leftMargin + doc.rightMargin, doc.height + doc.topMargin + doc.bottomMargin
            img_width, img_height = 15*cm, 12*cm
            x = (page_width - img_width) / 2
            y = (page_height - img_height) / 2
            canvas.setFillGray(0.3, 0.3)
            canvas.drawImage(img, x, y, width=img_width, height=img_height, mask='auto')
        canvas.restoreState()

        # -- Rectángulo del pie de página --
        footer_height = 1.8 * cm
        page_width_full = doc.width + doc.leftMargin + doc.rightMargin
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#18b1a3'))
        canvas.rect(0, 0, page_width_full, footer_height, fill=1, stroke=0)
        canvas.restoreState()

        # -- Tabla del pie de página (usando 'styles_dict') --
        icon_size = 0.4 * cm
        phone_icon_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'phone_icon.png')
        location_icon_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'location_icon.png')

        phone_icon = Image(phone_icon_path, width=icon_size, height=icon_size) if os.path.exists(phone_icon_path) else Spacer(0, 0)
        location_icon = Image(location_icon_path, width=icon_size, height=icon_size) if os.path.exists(location_icon_path) else Spacer(0, 0)

        phone_numbers_text = '55 1309 8145<br/>55 2231 5535'
        footer_col1_data = [[phone_icon, Paragraph(phone_numbers_text, styles_dict['FooterTextTight'])]]
        footer_col1_table = Table(footer_col1_data, colWidths=[0.6*cm, None])
        footer_col1_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

        footer_col2_data = [[location_icon, Paragraph('Prolongación Emiliano Zapata sin número barrio la luz, Santiago Cuautlalpan Tepotzotlan Estado de México ', styles_dict['FooterText'])]]
        footer_col2_table = Table(footer_col2_data, colWidths=[0.6*cm, None])
        footer_col2_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))

        available_width = doc.width
        footer_table = Table([[footer_col1_table, footer_col2_table]], colWidths=[available_width * 0.45, available_width * 0.55])
        footer_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5)]))

        table_width, table_height = footer_table.wrapOn(canvas, available_width, footer_height)
        y_position = (footer_height - table_height) / 2
        footer_table.drawOn(canvas, doc.leftMargin, y_position)

    # --- Creación del Documento ---
    doc = SimpleDocTemplate(response, pagesize=landscape(A5), topMargin=0.2*cm, bottomMargin=2*cm, leftMargin=0.2*cm, rightMargin=0.2*cm)

    # 3. SE USA LAMBDA PARA PASAR LOS ESTILOS A LA FUNCIÓN
    doc.onFirstPage = lambda canvas, doc: draw_background_and_footer(canvas, doc, styles)
    doc.onLaterPages = lambda canvas, doc: draw_background_and_footer(canvas, doc, styles)

    elements = []

    # --- Construcción del Contenido Principal ---
    # (Ya no se redefine 'styles' aquí)

    # 1. Encabezado
    logo_cit_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_uni_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'Uni.png')
    logo_size = 2 * cm

    logo_cit = Image(logo_cit_path, width=logo_size, height=logo_size) if os.path.exists(logo_cit_path) else Spacer(0, 0)
    logo_uni = Image(logo_uni_path, width=logo_size, height=logo_size) if os.path.exists(logo_uni_path) else Spacer(0, 0)

    header_name = Paragraph("Dra. Jaqueline Vázquez Gómez", styles['HeaderName'])
    header_cedula = Paragraph("CÉDULA PROFESIONAL: 11708282", styles['HeaderCedula'])

    header_data = [[logo_cit, header_name, header_cedula, logo_uni]]
    header_table = Table(header_data, colWidths=[logo_size, 10.8*cm, 6.6*cm, logo_size])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ecebeb")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'), ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # 2. Información del Paciente
    fecha_receta = receta.fecha.strftime("%d/%m/%Y") if receta.fecha else "N/A"
    patient_info_data = [
        [Paragraph('PACIENTE:', styles['PatientLabel']), Paragraph(f'{paciente.nombre} {paciente.apellido_paterno}', styles['PatientData']), Paragraph('FECHA:', styles['PatientLabel']), Paragraph(fecha_receta, styles['PatientData'])],
        [Paragraph('PESO:', styles['PatientLabel']), Paragraph(f'{receta.peso or "N/A"} kg', styles['PatientData']), '', ''],
        [Paragraph('TALLA:', styles['PatientLabel']), Paragraph(f'{receta.talla or "N/A"} cm', styles['PatientData']), '', ''],
        [Paragraph('T/A:', styles['PatientLabel']), Paragraph(f'{receta.ta or "N/A"}', styles['PatientData']), '', ''],
        [Paragraph('FC:', styles['PatientLabel']), Paragraph(f'{receta.fc or "N/A"}', styles['PatientData']), '', ''],
        [Paragraph('SAT. O2:', styles['PatientLabel']), Paragraph(f'{receta.sat_o2 or "N/A"}', styles['PatientData']), '', ''],
    ]
    patient_table = Table(patient_info_data, colWidths=[1.8*cm, 14*cm, 1.2*cm, 3*cm])
    patient_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 0.1*cm))

    # 3. Diagnóstico
    diagnostico_con_saltos = receta.diagnostico.replace('\n', '<br/>')
    elements.append(Paragraph(diagnostico_con_saltos, styles['Normal']))
    elements.append(Spacer(1, 4.2*cm))

    # 4. Texto "Previa Cita"
    elements.append(Spacer(1, 1, 'flexible'))
    elements.append(Paragraph("Previa Cita", styles['SectionTitle']))

    # --- Generación del PDF ---
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

@login_required
@require_POST
def actualizar_asistencia_simple(request, pk):
    """
    Actualiza el estado de asistencia de una cita (S/N/P) usando un formulario POST.
    """
    cita = get_object_or_404(Cita, pk=pk)

    # El valor del campo 'status' viene del botón o input (ej: 'S' o 'N')
    nuevo_estado = request.POST.get('status')

    if nuevo_estado in ['S', 'N']:
        # Lógica de Toggle: Si el estado actual es igual al nuevo, lo reseteamos a Pendiente.
        if cita.asistencia == nuevo_estado:
            cita.asistencia = 'P'
            messages.info(request, f"Asistencia de {cita.paciente.nombre} reseteada a Pendiente.")
        else:
            cita.asistencia = nuevo_estado
            messages.success(request, f"Asistencia de {cita.paciente.nombre} marcada como {cita.get_asistencia_display()}.")
    else:
        messages.error(request, "Estado de asistencia no válido.")

    cita.save()

    # Redirige de vuelta a la página de la agenda
    return redirect('agenda')


# --- AÑADE ESTAS NUEVAS VISTAS PARA EL CONSENTIMIENTO LEGAL ---

@login_required
def consentimiento_real_list(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    consentimientos = ConsentimientoInformadoReal.objects.filter(paciente=paciente).order_by('-fecha_creacion')
    context = {
        'paciente': paciente,
        'consentimientos': consentimientos,
    }
    # Apunta a una nueva plantilla que crearemos en el siguiente paso
    return render(request, 'consentimientos_reales/list.html', context)

@login_required
def consentimiento_real_create(request, paciente_pk):
    paciente = get_object_or_404(Paciente, pk=paciente_pk)
    if request.method == 'POST':
        form = ConsentimientoInformadoRealForm(request.POST)
        if form.is_valid():
            consentimiento = form.save(commit=False)
            consentimiento.paciente = paciente
            consentimiento.medico_responsable = request.user
            consentimiento.save()
            messages.success(request, 'Consentimiento Legal guardado exitosamente.')
            return redirect('consentimiento_real_list', paciente_pk=paciente.pk)
    else:
        form = ConsentimientoInformadoRealForm()

    context = {'form': form, 'paciente': paciente}
    return render(request, 'consentimientos_reales/form.html', context)

# Vista de detalle (puedes completarla más adelante)
@login_required
def consentimiento_real_detail(request, pk):
    consentimiento = get_object_or_404(ConsentimientoInformadoReal, pk=pk)
    context = {'consentimiento': consentimiento}
    return render(request, 'consentimientos_reales/detail.html', context)

# Vista de eliminar (puedes completarla más adelante)
@login_required
@require_POST
def consentimiento_real_delete(request, pk):
    consentimiento = get_object_or_404(ConsentimientoInformadoReal, pk=pk)
    paciente_pk = consentimiento.paciente.pk
    consentimiento.delete()
    messages.success(request, "Consentimiento Legal eliminado exitosamente.")
    return redirect('consentimiento_real_list', paciente_pk=paciente_pk)






from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER


@login_required
def imprimir_consentimiento_real_pdf(request, pk):
    consentimiento = get_object_or_404(ConsentimientoInformadoReal, pk=pk)
    paciente = consentimiento.paciente

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="consentimiento_{paciente.pk}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    # --- ESTILOS CON ESPACIADO CORREGIDO ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Titulo', fontName='Helvetica-Bold', fontSize=14, alignment=TA_CENTER, spaceAfter=1*cm))
    styles.add(ParagraphStyle(name='Cuerpo', fontName='Helvetica', fontSize=12, alignment=TA_JUSTIFY, spaceAfter=0.2*cm, leading=14))
    styles.add(ParagraphStyle(name='Rellenar', fontName='Helvetica', fontSize=12, leading=16))
    styles.add(ParagraphStyle(name='CampoFirma', fontName='Helvetica', fontSize=10, alignment=TA_CENTER))

    story = []

    # --- PÁGINA 1 ---
    story.append(Paragraph("CONSENTIMIENTO INFORMATIVO DE TRATAMIENTO", styles['Titulo']))

    story.append(Paragraph(
        "La ley general de salud en su reglamento en materia de prestación de servicios de "
        "atención medica en los artículos 80 y 81, requiere que el medico solicite a su paciente "
        "por escrito de la cirugía y / o tratamiento (s) en el que serán sometidos.",
        styles['Cuerpo']
    ))

    paciente_nombre_completo = f"{paciente.nombre} {paciente.apellido_paterno} {paciente.apellido_materno or ''}"
    story.append(Paragraph(
        f"Yo <b><u>&nbsp;{paciente_nombre_completo}&nbsp;</u></b> "
        f"en mi derecho autorizo a el (los) Medico (s). <b><u>&nbsp;{consentimiento.nombre_medico_autorizado}&nbsp;</u></b> "
        f"a realizar los tratamientos que a continuación se detallan "
        f"<b><u>&nbsp;{consentimiento.tratamiento or 'N/A'}&nbsp;</u></b> "
        f"Que se realizará(n) el día. <b><u>&nbsp;{consentimiento.fecha_procedimiento.strftime('%d / %m / %Y')}&nbsp;</u></b>",
        styles['Rellenar']
    ))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Ademas autorizo el equipo medico a realizar cualquier otro procedimiento que a su juicio sea en mi beneficio.", styles['Cuerpo']))
    story.append(Paragraph("El o los tratamientos descritos me han sido completamente explicados, así como los alcances, diagnósticos y pronósticos terapéuticos. Estoy enterado (a) de los métodos alternativos, sus ventajas y desventajas de cada uno de ellos.", styles['Cuerpo']))
    story.append(Paragraph("He sido además advertido, que aunque se esperan buenos resultados fruto de la preparación profesional del medico, la posibilidad y naturaleza de probables complicaciones no pueden ser anticipadas y por lo tanto no puede haber una garantía de que estas no se presentaran, ya que todos los organismos reaccionan de forma diferente.", styles['Cuerpo']))
    story.append(Paragraph("He tenido la oportunidad de hacer peguntas diferentes al tratamiento que me han de practicar y estas me han sido contestadas a mi entera satisfacción por lo que no me queda duda al respecto. Se ha valorado el riesgo beneficio del tratamiento y deseo someterme a el (ellos) de forma voluntaria.", styles['Cuerpo']))
    story.append(Paragraph("También estoy enterado (a) de los riesgos inherentes a todo procedimiento de este tipo de tratamiento (s) que aunque poco frecuente puede presentarse, como son: infecciones, reacciones alérgicas, cicatrices patológicos, entre otras.", styles['Cuerpo']))

    story.append(Paragraph("<b>Mi historia clínica básica es:</b>", styles['Cuerpo']))
    story.append(Paragraph("He recibido algún tratamiento similar a Cirugías Estéticas, Implante Facial y / o mesoterapia Homeopática, Alopática y / o terapia celular y/u otro importante de informar al medico:", styles['Cuerpo']))
    story.append(Spacer(1, 0.5*cm))

    checkbox_data = [[Paragraph("Si [ &nbsp; ]", styles['Cuerpo']), Paragraph("No [ &nbsp; ]", styles['Cuerpo'])]]
    if consentimiento.tuvo_tratamiento_similar:
        checkbox_data[0][0] = Paragraph("Si [ <b>X</b> ]", styles['Cuerpo'])
    else:
        checkbox_data[0][1] = Paragraph("No [ <b>X</b> ]", styles['Cuerpo'])
    story.append(Table(checkbox_data, colWidths=[2*cm, 2*cm]))

    story.append(Paragraph(f"Cual: <b><u>&nbsp;{consentimiento.cual_tratamiento or ''}&nbsp;</u></b>", styles['Rellenar']))
    story.append(Paragraph(f"Hace Cuanto tiempo: <b><u>&nbsp;{consentimiento.hace_cuanto_tiempo or ''}&nbsp;</u></b>", styles['Rellenar']))
    story.append(Paragraph(f"El nombre del medico que me atendió fue: <b><u>&nbsp;{consentimiento.nombre_medico_autorizado or ''}&nbsp;</u></b>", styles['Rellenar']))
    story.append(Paragraph(f"El nombre del producto que me aplico fue: <b><u>&nbsp;{consentimiento.nombre_producto_aplico or ''}&nbsp;</u></b>", styles['Rellenar']))

    # --- PÁGINA 2 ---
    story.append(PageBreak())

    story.append(Paragraph(f"Soy alérgico al medicamento: <b><u>&nbsp;{consentimiento.alergia_medicamento or 'Ninguno'}&nbsp;</u></b>", styles['Rellenar']))

    checkbox_hepatico = [[Paragraph("Sufro de insuficiencia hepática:", styles['Cuerpo']), Paragraph("Si [ &nbsp; ]", styles['Cuerpo']), Paragraph("No [ &nbsp; ]", styles['Cuerpo'])]]
    if consentimiento.insuficiencia_hepatica:
        checkbox_hepatico[0][1] = Paragraph("Si [ <b>X</b> ]", styles['Cuerpo'])
    else:
        checkbox_hepatico[0][2] = Paragraph("No [ <b>X</b> ]", styles['Cuerpo'])
    story.append(Table(checkbox_hepatico, colWidths=[6*cm, 2*cm, 2*cm]))

    checkbox_renal = [[Paragraph("Sufro de insuficiencia renal:", styles['Cuerpo']), Paragraph("Si [ &nbsp; ]", styles['Cuerpo']), Paragraph("No [ &nbsp; ]", styles['Cuerpo'])]]
    if consentimiento.insuficiencia_renal:
        checkbox_renal[0][1] = Paragraph("Si [ <b>X</b> ]", styles['Cuerpo'])
    else:
        checkbox_renal[0][2] = Paragraph("No [ <b>X</b> ]", styles['Cuerpo'])
    story.append(Table(checkbox_renal, colWidths=[6*cm, 2*cm, 2*cm]))

    story.append(Paragraph(f"En caso de emergencia llamar a: <b><u>&nbsp;{consentimiento.emergencia_llamar_a or ''}&nbsp;</u></b> Teléfono: <b><u>&nbsp;{consentimiento.emergencia_telefono or ''}&nbsp;</u></b>", styles['Rellenar']))
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph(
        "Bajo protesta de decir la verdad, declaro que lo aquí informado con mi puño y letra es "
        "absolutamente cierto, que no oculto información que pudiera ser importante para el "
        "diagnostico del medico que no hay vicio oculta en mi aceptación al tratamiento y que "
        "estoy conciente de los beneficios y riesgos que de su aceptación resulte.",
        styles['Cuerpo']
    ))

    story.append(Spacer(1, 2.5*cm)) # Espacio antes de la firma

    # Se define un estilo 'CuerpoIzquierda' para evitar que el texto de la firma se justifique
    styles.add(ParagraphStyle(name='FirmaNormal', parent=styles['Cuerpo'], alignment=TA_LEFT))

    firma_data = [
        # Fila 0: Etiquetas "Firma" y "Testigo"
        [Paragraph("Firma:", styles['FirmaNormal']), '', Paragraph("Nombre y Firma del Testigo:", styles['FirmaNormal']), ''],

        # Fila 1: Una fila vacía donde dibujaremos las líneas de firma
        ['', '', '', ''],

        # Fila 2: El nombre del testigo, alineado debajo de su línea
        ['', '', Paragraph(f"<b>{consentimiento.nombre_testigo or ''}</b>", styles['CampoFirma']), ''],

        # Fila 3: Un espacio vertical para separar la fecha
        [Spacer(1, 1*cm), '', '', ''],

        # Fila 4: La fecha
        [Paragraph(f"Fecha: <b>{consentimiento.fecha_creacion.strftime('%d / %m / %Y')}</b>", styles['FirmaNormal']), '', '', '']
    ]

    firma_table = Table(firma_data, colWidths=[2*cm, 5*cm, 5.5*cm, 4.5*cm])

    firma_table.setStyle(TableStyle([
        # Alineación vertical de todas las celdas
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Dibujar la línea para la firma del PACIENTE (en la fila 1, columna 1)
        ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),

        # Dibujar la línea para la firma del TESTIGO (en la fila 1, columna 3)
        ('LINEBELOW', (3, 0), (3, 0), 1, colors.black),

        # Centrar el nombre del testigo DEBAJO de su línea
        ('ALIGN', (2, 2), (3, 2), 'CENTER'),
        ('SPAN', (2, 2), (3, 2)), # Unir las celdas para que el centrado funcione bien

        # Hacer que la fecha ocupe todo el ancho para que no se parta
        ('SPAN', (0, 4), (-1, 4)),
    ]))

    story.append(firma_table)

    # Ya no necesitamos añadir la fecha por separado
    # ELIMINAR: story.append(Paragraph(f"Fecha: ...", styles['Rellenar']))

    # Construir y enviar el PDF
    doc.build(story)

    return response