from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm,UserChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.postgres.forms import SimpleArrayField
from .models import HistoriaClinicaMusculoEsqueletico
from django.forms.widgets import CheckboxSelectMultiple

# forms.py
from django import forms
from .models import *
from datetime import date

class MyForm(forms.Form):
    my_array_field = forms.MultipleChoiceField(required=False)

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # Definimos los campos personalizados del modelo CustomUser
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        label="Tipo de Usuario",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    recovery_nip = forms.CharField(
        max_length=4,
        label="NIP de Recuperación",
        help_text="Introduce un NIP de 4 dígitos para recuperar tu cuenta.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIP de 4 dígitos'})
    )

    # Campos de contraseña actualizados a password1 y password2
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text="Introduce la misma contraseña de nuevo, para su verificación.",
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Definimos todos los campos que queremos que aparezcan en el formulario
        fields = ('username', 'first_name', 'last_name', 'email', 'user_type', 'recovery_nip')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las dos contraseñas no coinciden.")

        validate_password(password2, self.instance)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.user_type = self.cleaned_data.get('user_type')
        user.recovery_nip = self.cleaned_data.get('recovery_nip')
        if commit:
            user.save()
        return user




class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'



class LoginForm(AuthenticationForm):
    """
    Formulario de inicio de sesión personalizado.
    Extiende el AuthenticationForm de Django para permitir personalización
    sin reescribir la lógica de autenticación.
    """
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }
        ),
        label="Usuario"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Contraseña'
            }
        ),
        label="Contraseña"
    )
    # ¡Importante! LoginForm NO DEBE tener una clase Meta que apunte a un modelo.


# Pacientes/forms.py

from django import forms
from .models import CustomUser, Doctor, FarmaciaProfile

class FarmaciaRegistrationForm(forms.ModelForm):
    """
    Formulario de registro para Farmacia.
    """
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        required=True,
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text="Introduce la misma contraseña de nuevo, para su verificación.",
    )

    recovery_nip = forms.CharField(
        max_length=4,
        label="NIP de Recuperación",
        help_text="Introduce un NIP de 4 dígitos para recuperar tu cuenta.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIP de 4 dígitos'})
    )

    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.all(),
        label="Doctor Asociado",
        required=True,  # <-- AÑADE ESTO
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="-- Seleccione un doctor --",
    )

    class Meta:
        model = CustomUser
        # Aquí está la corrección: 'user_type' no debe ir en los campos de un formulario
        # que lo asigna automáticamente.
        fields = ('username', 'first_name', 'last_name', 'email', 'recovery_nip')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Este campo no debería estar en el modelo, se maneja de forma oculta en la vista
        # Lo ocultamos del formulario
        self.fields['user_type'] = forms.CharField(
            widget=forms.HiddenInput(),
            initial='farmacia',
            required=False,
        )

        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password1')
        confirm_password = cleaned_data.get('password2')
        if password and confirm_password and password != confirm_password:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data

    def save(self, commit=True):
        # La lógica de guardado la manejaremos en la vista
        user = super(FarmaciaRegistrationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.user_type = 'farmacia' # Asignamos el user_type aquí
        if commit:
            user.save()
        return user

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'nombre',
            'apellido_paterno',
            'apellido_materno',
            'fecha_nacimiento',
            'genero',
            'telefono',
            'email',
            'direccion',
            # CAMPOS NUEVOS (DEBEN COINCIDIR EXACTAMENTE CON models.py):
            'Ocupacion',
            'Estado_Civil',
            'Nacionalidad',
            'Residencia_Anterior',
            'Religion',
            'Deporte_que_practica',
            'Pasatiempo',
        ]

        widgets = {
            # Widgets ORIGINALES:
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s) del paciente'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno (Opcional)'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5512345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección completa'}),

            # WIDGETS para CAMPOS NUEVOS (Select para choices, TextInput para el resto):
            'Ocupacion': forms.TextInput(attrs={'class': 'form-control'}),
            'Residencia_Anterior': forms.TextInput(attrs={'class': 'form-control'}), # Usando TextInput
            'Religion': forms.TextInput(attrs={'class': 'form-control'}), # Usando TextInput
            'Deporte_que_practica': forms.TextInput(attrs={'class': 'form-control'}), # Usando TextInput
            'Pasatiempo': forms.TextInput(attrs={'class': 'form-control'}), # Usando TextInput
            'Estado_Civil': forms.Select(attrs={'class': 'form-select'}), # Usando Select (tiene choices)
            'Nacionalidad': forms.Select(attrs={'class': 'form-select'}), # Usando Select (tiene choices)
        }

        labels = {
            # LABELS ORIGINALES:
            'nombre': 'Nombre(s)',
            'apellido_paterno': 'Apellido Paterno',
            'apellido_materno': 'Apellido Materno',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'genero': 'Género',
            'telefono': 'Teléfono',
            'email': 'Email',
            'direccion': 'Dirección',

            # LABELS NUEVOS:
            'Ocupacion': 'Ocupación',
            'Estado_Civil': 'Estado Civil',
            'Nacionalidad': 'Nacionalidad',
            'Residencia_Anterior': 'Residencia Anterior',
            'Religion': 'Religión',
            'Deporte_que_practica': 'Deporte que Practica',
            'Pasatiempo': 'Pasatiempo',
        }

    # Aceptar formato del input tipo date
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_nacimiento'].input_formats = ['%Y-%m-%d']







class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['paciente', 'fecha', 'hora_inicio', 'hora_fin', 'motivo', 'notas', 'estado']
        widgets = {
            'fecha': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'hora_inicio': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'},
                format='%H:%M'
            ),
            'hora_fin': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'},
                format='%H:%M'
            ),
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'paciente': 'Paciente',
            'fecha': 'Fecha de la Cita',
            'hora_inicio': 'Hora de Inicio',
            'hora_fin': 'Hora de Fin',
            'motivo': 'Motivo de la Cita',
            'notas': 'Notas Adicionales',
            'estado': 'Estado de la Cita',
        }

    def __init__(self, *args, **kwargs):
        pacientes = kwargs.pop('pacientes', None)
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = pacientes if pacientes is not None else Paciente.objects.none()

        # Si estamos editando una cita existente, prellenar las fechas y horas correctamente
        if self.instance and self.instance.pk:
            if self.instance.fecha:
                self.fields['fecha'].initial = self.instance.fecha.strftime('%Y-%m-%d')
            if self.instance.hora_inicio:
                self.fields['hora_inicio'].initial = self.instance.hora_inicio.strftime('%H:%M')
            if self.instance.hora_fin:
                self.fields['hora_fin'].initial = self.instance.hora_fin.strftime('%H:%M')







class CitaFormAgenda(CitaForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        menu = [opcion for opcion in Cita.MOTIVO_CHOICES if opcion[0] not in Cita.MOTIVO_OCULTOS_MENU]
        motivo_actual = self.instance.motivo if self.instance and self.instance.pk else None
        if motivo_actual and motivo_actual in Cita.MOTIVO_OCULTOS_MENU:
            extra = [opcion for opcion in Cita.MOTIVO_CHOICES if opcion[0] == motivo_actual]
            menu = extra + menu
        self.fields['motivo'].choices = menu


class ConsentimientoInformadoRealForm(forms.ModelForm):
    class Meta:
        model = ConsentimientoInformadoReal
        # Los campos a excluir (los que se llenan automáticamente) son correctos.
        exclude = ['paciente', 'medico_responsable', 'fecha_creacion']

        # Esta lista de widgets ahora coincide exactamente con los campos de tu modelo.
        widgets = {
            'tratamiento': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_procedimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tuvo_tratamiento_similar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cual_tratamiento': forms.TextInput(attrs={'class': 'form-control'}),
            'hace_cuanto_tiempo': forms.TextInput(attrs={'class': 'form-control'}),

            # CORREGIDO: Usando el nombre correcto de tu modelo
            'nombre_medico_atendio': forms.TextInput(attrs={'class': 'form-control'}),

            # CORREGIDO: Usando el nombre correcto de tu modelo
            'nombre_producto_aplico': forms.TextInput(attrs={'class': 'form-control'}),

            'reaccion_duro': forms.TextInput(attrs={'class': 'form-control'}),
            'alergia_medicamento': forms.TextInput(attrs={'class': 'form-control'}),
            'insuficiencia_hepatica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insuficiencia_renal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'emergencia_llamar_a': forms.TextInput(attrs={'class': 'form-control'}),
            'emergencia_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'identificacion_oficial': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_testigo': forms.TextInput(attrs={'class': 'form-control'}),
            'domicilio': forms.TextInput(attrs={'class': 'form-control'}),
        }







#Formulario Consentimiento

class ConsentimientoInformadoForm(forms.ModelForm):
    # Campo para mostrar el nombre del paciente, de solo lectura
    # Esto evitará que se renderice el campo de selección.
    nombre_paciente = forms.CharField(
        label='Nombre del Paciente',
        required=False,
        disabled=True
    )

    class Meta:
        model = ConsentimientoInformado
        # Aquí defines los campos que el usuario debe llenar.
        # Excluye 'paciente' para evitar que Django lo renderice como un Select.
        fields = ['nombre_paciente', 'fecha', 'edad', 'temp', 'peso', 'talla', 'ta', 'rp']

        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'my-input my-date-input'}),
            'edad': forms.NumberInput(attrs={'class': 'my-input'}),
            'temp': forms.TextInput(attrs={'class': 'my-input'}),
            'peso': forms.TextInput(attrs={'class': 'my-input'}),
            'talla': forms.TextInput(attrs={'class': 'my-input'}),
            'ta': forms.TextInput(attrs={'class': 'my-input'}),
            'rp': forms.Textarea(attrs={'class': 'my-textarea', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        # La vista pasará la instancia del paciente usando la palabra clave `paciente_instance`
        paciente_instance = kwargs.pop('paciente_instance', None)
        super().__init__(*args, **kwargs)

        if paciente_instance:
            # Completa el campo de solo lectura con el nombre completo
            nombre_completo = f'{paciente_instance.nombre} {paciente_instance.apellido_paterno}'
            if paciente_instance.apellido_materno:
                nombre_completo += f' {paciente_instance.apellido_materno}'

            self.initial['nombre_paciente'] = nombre_completo


class CheckboxCardSelectMultiple(CheckboxSelectMultiple):
    template_name = 'forms/widgets/checkbox_card_multiple.html'
# ----------------------------------------------------------------------------------
# FORMULARIO UNIFICADO: HistoriaClinicaUnificadaForm
# Combina los campos de Parte1, Parte2 y Ginecológico en un solo ModelForm.
# ----------------------------------------------------------------------------------
class HistoriaClinicaUnificadaForm(forms.ModelForm):



    # Sustituye 'HistoriaClinica.SERVICIOS_VIVIENDA_CHOICES' con tus choices reales.
    servicio_vivienda = SimpleArrayField(
        forms.CharField(),
        # IMPORTANTE: Asegúrate de que HistoriaClinica esté disponible con sus CHOICES
        widget=CheckboxCardSelectMultiple(choices=HistoriaClinica.SERVICIOS_VIVIENDA_CHOICES),
        label="Servicios con los que cuenta la vivienda"
    )

    Antecedentes_familiares = SimpleArrayField(
        forms.CharField(),
        widget=CheckboxCardSelectMultiple(choices=HistoriaClinica.ANTECENDENTES_FAMILIARES_CHOICES),
        label='Antecedentes Familiares'
    )

    habitos_toxicos = SimpleArrayField(
        forms.CharField(),
        widget=CheckboxCardSelectMultiple(choices=HistoriaClinica.HABITOS_TOXICOS_CHOICES),
        label='Hábitos tóxicos'
    )

    Patologias = SimpleArrayField(
        forms.CharField(),
        widget=CheckboxCardSelectMultiple(choices=HistoriaClinica.PATOLOGIAS_CHOICES),
        label='Patologías'
    )

    Allimentación = SimpleArrayField(
        forms.CharField(),
        widget=CheckboxCardSelectMultiple(choices=HistoriaClinica.ALIMENTACION_CHOICES),
        label='Alimentación'
    )

    class Meta:
        model = HistoriaClinica
        # Se combinan TODOS los campos de Parte1, Parte2 y Ginecológico
        fields = [
            # Secciones principales (Motivo de Consulta y Enfermedad Actual primero)
            'motivo_consulta',
            'enfermedad_actual',


            # Parte 2 - Información General
            'GradoInstruccion',
            'inmunizaciones_o_vacunas',

            # Parte 2 - Higiene
            'baño_diario', 'aseo_dental', 'lavado_manos_antes_comer', 'lavado_manos_despues',

            # Parte 2 - Vivienda
            'tamanio_vivienda', 'tipo_vivienda', 'servicio_vivienda',

            # Parte 2 - Antecedentes y Fisiológicos
            'Antecedentes_familiares',
          #  'Residencia_Anterior',
            'habitos_toxicos',
            'Allimentación',
            'Ingesta_Agua', 'Cantidad_veces_Orina', 'Catarsis', 'Somnia',

            # Parte 2 - Patológicos
            'Infancia', 'Adulto', 'Patologias',
            'ha_sido_operado', 'fecha_operacion', 'traumatismo_o_fractura', 'Otro',

            # Parte 3 - Gineco-Obstétricos
            'fum', 'fpp', 'edad_gestacional', 'menarquia', 'rm_rit_menstr', 'irs',
            'no_de_parejas', 'flujo_genital', 'gestas', 'partos', 'cesareas', 'abortos',
            'anticonceptivos', 'anticonceptivos_tipo', 'anticonceptivos_tiempo',
            'anticonceptivos_ultima_toma', 'cirugia_ginecologica', 'otros_ginecologicos',
            #'Ingesta_Agua',
            # Parte 1 - Comentarios finales
            'comentarios',
        ]

        widgets = {
            # Widgets RadioSelect (Parte 2)
            'baño_diario': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'aseo_dental': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_antes_comer': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_despues': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'tamanio_vivienda': forms.RadioSelect,
            'tipo_vivienda': forms.RadioSelect,
            'fecha_operacion': forms.DateInput(attrs={'type': 'date'}),
            #
            'Ingesta_Agua': forms.NumberInput(attrs={'class': 'form-control'}),
            'Cantidad_veces_Orina': forms.NumberInput(attrs={'class': 'form-control'}),
            'Catarsis': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Somnia': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            #boolean
            'ha_sido_operado': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
    # ...
            # Widgets DateInput (Ginecológico)
            'fum': forms.DateInput(attrs={'type': 'date'}),
            'fpp': forms.DateInput(attrs={'type': 'date'}),
            'anticonceptivos_ultima_toma': forms.DateInput(attrs={'type': 'date'}),
            'menarquia': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'rm_rit_menstr': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'irs': forms.TextInput(attrs={'class': 'input-linea-corta'}),

    # Y asegúrate de que estos otros también estén correctos:
            'no_de_parejas': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'flujo_genital': forms.TextInput(attrs={'class': 'input-linea-corta'}),

            # Campos de texto con estilo de línea (clases CSS)
            'motivo_consulta': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'enfermedad_actual': forms.Textarea(attrs={'rows': 3, 'class': 'input-linea-larga'}),
            'comentarios': forms.Textarea(attrs={'rows': 3, 'class': 'input-linea-larga'}),
            'GradoInstruccion': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'GradoInstruccion': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'inmunizaciones_o_vacunas': forms.TextInput(attrs={'class': 'input-linea-corta', 'value': ''}),
            'Infancia': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'Adulto': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'traumatismo_o_fractura': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Otro': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'anticonceptivos_tipo': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'anticonceptivos_tiempo': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'cirugia_ginecologica': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'otros_ginecologicos': forms.TextInput(attrs={'class': 'input-linea-corta'}),
        }

#######################################################################################################
################SEGUNDA HOJA ##########################################################################

# Formulario Único: Cuestionario Completo por Sistemas
# ====================================================
class HistoriaClinicaSegundaHoja(forms.ModelForm):

    class Meta:
        model = HistoriaClinica

        # 📚 CONSOLIDACIÓN DE TODOS LOS FIELDS 📚
        fields = [
            # 1. Sistema Digestivo
            'digest_halitosis', 'digest_boca_seca', 'digest_masticacion', 'digest_disfagia',
            'digest_pirosis', 'digest_nausea', 'digest_vomito_hematemesis', 'digest_colicos',
            'digest_dolor_abdominal', 'digest_meteorismo', 'digest_flatulencias',
            'digest_constipacion', 'digest_diarrea', 'digest_rectorragias', 'digest_melenas',
            'digest_pujo', 'digest_tenesmo', 'digest_ictericia', 'digest_coluria',
            'digest_acolia', 'digest_prurito_cutaneo', 'digest_hemorragias',
            'digest_prurito_anal', 'digest_hemorroides', 'Comentarios_digestivo',

            # 2. Aparato Cardiovascular y Respiratorio
            'cardio_tos_seca', 'cardio_tos_espasmodica', 'cardio_hemoptisis',
            'cardio_dolor_precordial', 'cardio_palpitaciones', 'cardio_cianosis',
            'cardio_edema', 'cardio_acufenos', 'cardio_fosfenos', 'cardio_sincope',
            'cardio_lipotimia', 'cardio_cefaleas', 'pulso_carotideo', 'pulso_humeral',
            'pulso_radial', 'pulso_femoral', 'pulso_popliteo', 'pulso_tibial_posterior',
            'pulso_pedio', 'pulso_carotideo_izq', 'pulso_humeral_izq',
            'pulso_radial_izq', 'pulso_femoral_izq', 'pulso_popliteo_izq',
            'pulso_tibial_posterior_izq', 'pulso_pedio_izq','resp_tos',
            'resp_disnea', 'resp_dolor_toracico', 'resp_hemoptisis',
            'resp_cianosis', 'resp_vomica', 'resp_alteraciones_voz',
            'Comentarios_cardio', 'Comentarios_respiratorio',

            # 3. Aparato Genital y Urinario
            'genital_criptorquidea', 'genital_fimosis', 'genital_funcion_sexual',
            'genital_sangrado_genital', 'genital_flujo_leucorrea',
            'genital_dolor_ginecologico', 'genital_prurito_vulvar',
            'Comentarios_genital',

            'Poliuria', 'Anuria', 'Oliguria', 'Nicturia', 'Opsuria',
            'Disuria', 'Tenesmo_vesical', 'Urgencia', 'Chorro',
            'Enuresis', 'Incontinencia', 'Ninguna',
            'urin_volumen_orina', 'urin_color_orina', 'urin_olor_orina',
            'urin_aspecto_orina', 'urin_dolor_lumbar', 'urin_edema_palpebral_sup',
            'urin_edema_palpebral_inf', 'urin_edema_renal',
            'urin_hipertension_arterial', 'urin_datos_clinicos_anemia',
            'Comentarios_urinario',

            # 4. Hematológico, Endocrino y Exploración de Cuello
            'Palidez', 'Astenia', 'Adinamia', 'Otros',
            'hemato_hemorragias', 'hemato_adenopatias', 'hemato_esplenomegalia',
            'Comentarios_anemia',
            'endocr_bocio', 'endocr_letargia', 'endocr_bradipsiquia_idia',
            'endocr_intolerancia_calor_frio', 'endocr_nerviosismo', 'endocr_hiperquinesis',
            'endocr_caracteres_sexuales', 'endocr_galactorrea', 'endocr_amenorrea',
            'endocr_ginecomastia', 'endocr_obesidad', 'endocr_ruborizacion',
            'Comentarios_endocrino',
            'cuello_tiroides', 'cuello_musculos', 'cuello_ganglios_linfaticos',
        ]

        # ⚙️ CONSOLIDACIÓN DE TODOS LOS WIDGETS ⚙️
        widgets = {
            # 1. Sistema Digestivo
            'digest_halitosis': forms.CheckboxInput(),
            'digest_boca_seca': forms.CheckboxInput(),
            'digest_masticacion': forms.CheckboxInput(),
            'digest_disfagia': forms.CheckboxInput(),
            'digest_pirosis': forms.CheckboxInput(),
            'digest_nausea': forms.CheckboxInput(),
            'digest_vomito_hematemesis': forms.CheckboxInput(),
            'digest_colicos': forms.CheckboxInput(),
            'digest_dolor_abdominal': forms.CheckboxInput(),
            'digest_meteorismo': forms.CheckboxInput(),
            'digest_flatulencias': forms.CheckboxInput(),
            'digest_constipacion': forms.CheckboxInput(),
            'digest_diarrea': forms.CheckboxInput(),
            'digest_rectorragias': forms.CheckboxInput(),
            'digest_melenas': forms.CheckboxInput(),
            'digest_pujo': forms.CheckboxInput(),
            'digest_tenesmo': forms.CheckboxInput(),
            'digest_ictericia': forms.CheckboxInput(),
            'digest_coluria': forms.CheckboxInput(),
            'digest_acolia': forms.CheckboxInput(),
            'digest_prurito_cutaneo': forms.CheckboxInput(),
            'digest_hemorragias': forms.CheckboxInput(),
            'digest_prurito_anal': forms.CheckboxInput(),
            'digest_hemorroides': forms.CheckboxInput(),

            # 2. Aparato Cardiovascular y Respiratorio (Solo los campos que tenían widget explícito)
            'cardio_tos_seca': forms.CheckboxInput(),
            'cardio_tos_espasmodica': forms.CheckboxInput(),
            'cardio_hemoptisis': forms.CheckboxInput(),
            'cardio_dolor_precordial': forms.CheckboxInput(),
            'cardio_palpitaciones': forms.CheckboxInput(),
            'cardio_cianosis': forms.CheckboxInput(),
            'cardio_edema': forms.CheckboxInput(),
            'cardio_acufenos': forms.CheckboxInput(),
            'cardio_fosfenos': forms.CheckboxInput(),
            'cardio_sincope': forms.CheckboxInput(),
            'cardio_lipotimia': forms.CheckboxInput(),
            'cardio_cefaleas': forms.CheckboxInput(),
            'resp_tos': forms.CheckboxInput(),
            'resp_disnea': forms.CheckboxInput(),
            'resp_dolor_toracico': forms.CheckboxInput(),
            'resp_hemoptisis': forms.CheckboxInput(),
            'resp_cianosis': forms.CheckboxInput(),
            'resp_vomica': forms.CheckboxInput(),
            'resp_alteraciones_voz': forms.CheckboxInput(),

            # 3. Aparato Genital y Urinario
            'genital_criptorquidea': forms.CheckboxInput(),
            'genital_fimosis': forms.CheckboxInput(),
            'genital_funcion_sexual': forms.CheckboxInput(),
            'genital_sangrado_genital': forms.CheckboxInput(),
            'genital_flujo_leucorrea': forms.CheckboxInput(),
            'genital_dolor_ginecologico': forms.CheckboxInput(),
            'genital_prurito_vulvar': forms.CheckboxInput(),
            'Poliuria': forms.CheckboxInput(),
            'Anuria': forms.CheckboxInput(),
            'Oliguria': forms.CheckboxInput(),
            'Nicturia': forms.CheckboxInput(),
            'Opsuria': forms.CheckboxInput(),
            'Disuria': forms.CheckboxInput(),
            'Tenesmo_vesical': forms.CheckboxInput(),
            'Urgencia': forms.CheckboxInput(),
            'Chorro': forms.CheckboxInput(),
            'Enuresis': forms.CheckboxInput(),
            'Incontinencia': forms.CheckboxInput(),
            'Ninguna': forms.CheckboxInput(),
            'urin_volumen_orina': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'urin_color_orina': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'urin_olor_orina': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'urin_aspecto_orina': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'urin_dolor_lumbar': forms.CheckboxInput(),
            'urin_edema_palpebral_sup': forms.CheckboxInput(),
            'urin_edema_palpebral_inf': forms.CheckboxInput(),
            'urin_edema_renal': forms.CheckboxInput(),
            'urin_hipertension_arterial': forms.CheckboxInput(),
            'urin_datos_clinicos_anemia': forms.CheckboxInput(),

            # 4. Hematológico, Endocrino y Exploración de Cuello
            'Palidez': forms.CheckboxInput(),
            'Astenia': forms.CheckboxInput(),
            'Adinamia': forms.CheckboxInput(),
            'hemato_hemorragias': forms.CheckboxInput(),
            'hemato_adenopatias': forms.CheckboxInput(),
            'hemato_esplenomegalia': forms.CheckboxInput(),
            'endocr_bocio': forms.CheckboxInput(),
            'endocr_letargia': forms.CheckboxInput(),
            'endocr_bradipsiquia_idia': forms.CheckboxInput(),
            'endocr_intolerancia_calor_frio': forms.CheckboxInput(),
            'endocr_nerviosismo': forms.CheckboxInput(),
            'endocr_hiperquinesis': forms.CheckboxInput(),
            'endocr_caracteres_sexuales': forms.CheckboxInput(),
            'endocr_galactorrea': forms.CheckboxInput(),
            'endocr_amenorrea': forms.CheckboxInput(),
            'endocr_ginecomastia': forms.CheckboxInput(),
            'endocr_obesidad': forms.CheckboxInput(),
            'endocr_ruborizacion': forms.CheckboxInput(),
        }


#######################################################################################################
################TERCER HOJA ##########################################################################
# ----------------------------------------------------
# Formulario 1: Exploración de Columna Vertebral y MMSS
# ----------------------------------------------------
class CuestionarioExploracion1Form(forms.ModelForm):
    # Campos para la Exploración de Columna Vertebral
    ecv_cervical_asc = forms.CharField(label='Ascendente', required=False)
    ecv_cervical_desc = forms.CharField(label='Descendente', required=False)
    ecv_cervical_obs = forms.CharField(label='Observaciones', required=False)

    ecv_dorsal_asc = forms.CharField(label='Ascendente', required=False)
    ecv_dorsal_desc = forms.CharField(label='Descendente', required=False)
    ecv_dorsal_obs = forms.CharField(label='Observaciones', required=False)

    ecv_lumbosacra_asc = forms.CharField(label='Ascendente', required=False)
    ecv_lumbosacra_desc = forms.CharField(label='Descendente', required=False)
    ecv_lumbosacra_obs = forms.CharField(label='Observaciones', required=False)

    # Campos para la Exploración de Miembros Superiores - Hombros
    mmss_hombros_cs_ad = forms.CharField(label='Adducción', required=False)
    mmss_hombros_cs_ab = forms.CharField(label='Abducción', required=False)
    mmss_hombros_cs_f = forms.CharField(label='Flexión', required=False)
    mmss_hombros_cs_e = forms.CharField(label='Extensión', required=False)
    mmss_hombros_cv_ad = forms.CharField(label='Adducción', required=False)
    mmss_hombros_cv_ab = forms.CharField(label='Abducción', required=False)
    mmss_hombros_cv_f = forms.CharField(label='Flexión', required=False)
    mmss_hombros_cv_e = forms.CharField(label='Extensión', required=False)

    # Campos para la Evaluación articular de MMSS Codo y Muñeca
    art_codo_e = forms.CharField(label='E', required=False)
    art_codo_f = forms.CharField(label='F', required=False)
    art_muneca_e = forms.CharField(label='E', required=False)
    art_muneca_f = forms.CharField(label='F', required=False)
    art_muneca_p = forms.CharField(label='P', required=False)
    art_muneca_s = forms.CharField(label='S', required=False)

    # Campos para la Evaluación articular de MMSS del Pulgar y Dedos
    art_pulgar_ab = forms.CharField(label='AB', required=False)
    art_pulgar_ad = forms.CharField(label='AD', required=False)
    art_pulgar_e = forms.CharField(label='E', required=False)
    art_pulgar_f = forms.CharField(label='F', required=False)
    art_dedos_f = forms.CharField(label='F', required=False)
    art_dedos_e = forms.CharField(label='E', required=False)
    art_dedos_ifp = forms.CharField(label='IFP', required=False)

    class Meta:
        model = HistoriaClinica
        # Django ahora usará los campos que definiste arriba en lugar de intentar inferirlos del modelo
        fields = [
            'ecv_cervical_asc', 'ecv_cervical_desc', 'ecv_cervical_obs',
            'ecv_dorsal_asc', 'ecv_dorsal_desc', 'ecv_dorsal_obs',
            'ecv_lumbosacra_asc', 'ecv_lumbosacra_desc', 'ecv_lumbosacra_obs',

            'mmss_hombros_cs_ad', 'mmss_hombros_cs_ab', 'mmss_hombros_cs_f',
            'mmss_hombros_cs_e', 'mmss_hombros_cv_ad', 'mmss_hombros_cv_ab',
            'mmss_hombros_cv_f', 'mmss_hombros_cv_e',

            'art_codo_e', 'art_codo_f',
            'art_muneca_e', 'art_muneca_f', 'art_muneca_p', 'art_muneca_s',
            'art_pulgar_ab', 'art_pulgar_ad', 'art_pulgar_e', 'art_pulgar_f',
            'art_dedos_f', 'art_dedos_e', 'art_dedos_ifp',
        ]
        widgets = {}

# ----------------------------------------------------
# Formulario 2: Exploración de MMII y Nasal
# ----------------------------------------------------
class ExploracionCompletaForm(forms.ModelForm):

    # 1. Campos de Exploración de Columna Vertebral (ECV) - Definidos explícitamente como CharField
    ecv_cervical_asc = forms.CharField(label='Ascendente', required=False)
    ecv_cervical_desc = forms.CharField(label='Descendente', required=False)
    ecv_cervical_obs = forms.CharField(label='Observaciones', required=False)

    ecv_dorsal_asc = forms.CharField(label='Ascendente', required=False)
    ecv_dorsal_desc = forms.CharField(label='Descendente', required=False)
    ecv_dorsal_obs = forms.CharField(label='Observaciones', required=False)

    ecv_lumbosacra_asc = forms.CharField(label='Ascendente', required=False)
    ecv_lumbosacra_desc = forms.CharField(label='Descendente', required=False)
    ecv_lumbosacra_obs = forms.CharField(label='Observaciones', required=False)

    # 2. Campos de Exploración de Miembros Superiores (MMSS) - Hombros
    mmss_hombros_cs_ad = forms.CharField(label='Adducción', required=False)
    mmss_hombros_cs_ab = forms.CharField(label='Abducción', required=False)
    mmss_hombros_cs_f = forms.CharField(label='Flexión', required=False)
    mmss_hombros_cs_e = forms.CharField(label='Extensión', required=False)
    mmss_hombros_cv_ad = forms.CharField(label='Adducción', required=False)
    mmss_hombros_cv_ab = forms.CharField(label='Abducción', required=False)
    mmss_hombros_cv_f = forms.CharField(label='Flexión', required=False)
    mmss_hombros_cv_e = forms.CharField(label='Extensión', required=False)

    # 3. Campos para la Evaluación articular de MMSS Codo y Muñeca
    art_codo_e = forms.CharField(label='E', required=False)
    art_codo_f = forms.CharField(label='F', required=False)
    art_muneca_e = forms.CharField(label='E', required=False)
    art_muneca_f = forms.CharField(label='F', required=False)
    art_muneca_p = forms.CharField(label='P', required=False)
    art_muneca_s = forms.CharField(label='S', required=False)

    # 4. Campos para la Evaluación articular de MMSS del Pulgar y Dedos
    art_pulgar_ab = forms.CharField(label='AB', required=False)
    art_pulgar_ad = forms.CharField(label='AD', required=False)
    art_pulgar_e = forms.CharField(label='E', required=False)
    art_pulgar_f = forms.CharField(label='F', required=False)
    art_dedos_f = forms.CharField(label='F', required=False)
    art_dedos_e = forms.CharField(label='E', required=False)
    art_dedos_ifp = forms.CharField(label='IFP', required=False)

    class Meta:
        model = HistoriaClinica

        # 📚 CONSOLIDACIÓN DE TODOS LOS FIELDS 📚
        fields = [
            # ECV
            'ecv_cervical_asc', 'ecv_cervical_desc', 'ecv_cervical_obs',
            'ecv_dorsal_asc', 'ecv_dorsal_desc', 'ecv_dorsal_obs',
            'ecv_lumbosacra_asc', 'ecv_lumbosacra_desc', 'ecv_lumbosacra_obs',

            # MMSS - Hombros
            'mmss_hombros_cs_ad', 'mmss_hombros_cs_ab', 'mmss_hombros_cs_f',
            'mmss_hombros_cs_e', 'mmss_hombros_cv_ad', 'mmss_hombros_cv_ab',
            'mmss_hombros_cv_f', 'mmss_hombros_cv_e',

            # MMSS - Codo y Muñeca
            'art_codo_e', 'art_codo_f',
            'art_muneca_e', 'art_muneca_f', 'art_muneca_p', 'art_muneca_s',

            # MMSS - Pulgar y Dedos
            'art_pulgar_ab', 'art_pulgar_ad', 'art_pulgar_e', 'art_pulgar_f',
            'art_dedos_f', 'art_dedos_e', 'art_dedos_ifp',

            # MMII - Cadera, Tobillo, Subastragalina (Del Formulario 2)
            'art_cadera_ab', 'art_cadera_ad', 'art_cadera_f', 'art_cadera_e',
            'art_tobillo_f', 'art_tobillo_e',
            'art_subastragalina_f', 'art_subastragalina_ev',

            # Exploración Nasal (Del Formulario 2)
            'nasal_mucosa', 'nasal_cochas', 'nasal_vascularizacion',
        ]

        # Como no se especificaron widgets, se usarán los widgets por defecto (TextInput)
        # para todos los CharField. Los campos definidos explícitamente arriba aseguran
        # que se usen CharField aunque el modelo defina otros tipos (si ese fuera el caso).
        widgets = {}

#######################################################################################################
################CUARTA HOJA ##########################################################################
# ----------------------------------------------------
# Formulario 1: Pulsos y Estado de Conciencia
# ----------------------------------------------------
class CuestionarioExploracionGlasgow(forms.ModelForm):

    # Campo ArrayField del Formulario 2 (debe definirse explícitamente)
    # Nota: Tu CHOICES (HistoriaClinica.CAMPOS_VISUALES_CHOICES) debe ser accesible aquí.
    campos_visuales_opciones = SimpleArrayField(
        forms.CharField(),
        # Asumo que HistoriaClinica.CAMPOS_VISUALES_CHOICES está definido en tu modelo.
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.CAMPOS_VISUALES_CHOICES),
        label='Campos Visuales Opciones'
    )

    class Meta:
        model = HistoriaClinica

        # 📚 CONSOLIDACIÓN DE TODOS LOS FIELDS 📚
        fields = [
            # Campos del Formulario 1: Pulsos y Conciencia
            'me_pulso_carotideo_derecho', 'me_pulso_carotideo_izquierdo',
            'me_pulso_humeral_derecho', 'me_pulso_humeral_izquierdo',
            'me_pulso_radial_derecho', 'me_pulso_radial_izquierdo',
            'me_pulso_femoral_derecho', 'me_pulso_femoral_izquierdo',
            'me_pulso_popliteo_derecho', 'me_pulso_popliteo_izquierdo',
            'me_pulso_tibial_posterior_derecho', 'me_pulso_tibial_posterior_izquierdo',
            'me_pulso_pedio_derecho', 'me_pulso_pedio_izquierdo',
            'ascitis', 'Estado_Conciencia',

            # Campos del Formulario 2: Glasgow y Visual
            'glasgow_apertura_ojos_respuesta', 'glasgow_apertura_ojos_puntuacion',
            'glasgow_respuesta_verbal_respuesta', 'glasgow_respuesta_verbal_puntuacion',
            'glasgow_respuesta_motora_respuesta', 'glasgow_respuesta_motora_puntuacion',
            'reflejo_fotomotor_tamano', 'reflejo_fotomotor_relaciones',
            'reflejo_fotomotor_respuestas_luz', 'par_craneal_iii_oculomotor',
            'par_craneal_iv_patetico', 'par_craneal_vi_motor_ocular_externo',
            'retina_relacion_arterio_venosa',
            'retina_macula', 'campos_visuales_opciones', # Este campo está definido explícitamente arriba
            'par_craneal_iii_oculomotor_cv', 'par_craneal_iv_patetico_cv',
            'par_craneal_vi_motor_ocular_externo_cv'
        ]

        # ⚙️ CONSOLIDACIÓN DE TODOS LOS WIDGETS ⚙️
        widgets = {
            # Widget del Formulario 1
            'ascitis': forms.CheckboxInput(),
            'Estado_Conciencia':forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),

            # Los demás campos usan widgets por defecto o se definen explícitamente arriba (SimpleArrayField)
        }

#######################################################################################################
################QUINTA HOJA ##########################################################################
class CuestionarioExploracionFinalForm(forms.ModelForm):
    # Campos que usan ArrayField y necesitan una configuración especial
    Naso_palpebral = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Naso palpebral'
    )
    Superciliar = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Superciliar'
    )
    Maseterino = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Maseterino'
    )
    Bicipital = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Bicipital'
    )
    Estilo_Radial = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Estilo Radial'
    )
    Tricipital = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Tricipital'
    )
    Cubito_Pronador = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Cúbito Pronador'
    )
    Medio_Pubiano = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Medio Pubiano'
    )
    Rotuliano = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Rotuliano'
    )
    Corneo_Palpebral = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Córneo Palpebral'
    )
    Conjuntivo_Palpebral = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Conjuntivo Palpebral'
    )
    Palatino_o_Velo_Palatino = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Palatino o Velo Palatino'
    )
    Faringeo = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Faríngeo'
    )
    Tusigeno = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Tusígeno'
    )
    Vomito = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Vómito'
    )
    Respiratorio = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Respiratorio'
    )
    Miccional = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Miccional'
    )
    Defecatorio = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Defecatorio'
    )
    Aquileo = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Aquíleo'
    )
    Babinski = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Babinski'
    )
    Chaddock = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Chaddock'
    )
    Oppenheim = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Oppenheim'
    )
    Gordon = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Gordon'
    )
    Kerning = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Kerning'
    )
    Brudzinski = SimpleArrayField(
        forms.CharField(),
        widget=forms.RadioSelect(choices=HistoriaClinica.CHOICES_NUMERICAS),
        label='Brudzinski'
    )

    class Meta:
        model = HistoriaClinica
        fields = [
            'Conducta_auditiva', 'Membrana_timpatica', 'conduccion_osea',
            'conduccion_area', 'Naso_palpebral', 'Superciliar', 'Maseterino',
            'Bicipital', 'Estilo_Radial', 'Tricipital', 'Cubito_Pronador',
            'Medio_Pubiano', 'Rotuliano', 'Corneo_Palpebral', 'Conjuntivo_Palpebral',
            'Palatino_o_Velo_Palatino', 'Faringeo', 'Tusigeno', 'Vomito',
            'Respiratorio', 'Miccional', 'Defecatorio', 'Aquileo',
            'Babinski', 'Chaddock', 'Oppenheim', 'Gordon', 'Kerning', 'Brudzinski',
        ]


















##################################################################################################33
###################################################################################################
##############PARTE NUEVA QUE VAMOS A INTEGRAR

class RecoveryRequestForm(forms.Form):
    """
    Formulario para solicitar la recuperación de la cuenta.
    Pide el nombre de usuario o el correo electrónico.
    """
    username_or_email = forms.CharField(
        label="Nombre de usuario o Correo electrónico",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario o correo'})
    )

    def clean_username_or_email(self):
        data = self.cleaned_data['username_or_email']
        try:
            # Intenta encontrar el usuario por username o email
            user = CustomUser.objects.get(username=data)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(email=data)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError("Usuario no encontrado.")

        # Guarda el usuario en el formulario para usarlo en la vista
        self.user = user
        return data


class RecoveryVerifyForm(forms.Form):
    """
    Formulario para verificar el NIP de recuperación de 4 dígitos.
    """
    nip = forms.CharField(
        label="NIP de Recuperación",
        max_length=4,
        min_length=4,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIP de 4 dígitos'})
    )

    def clean_nip(self):
        nip = self.cleaned_data.get('nip')
        if not nip.isdigit():
            raise forms.ValidationError("El NIP debe contener solo dígitos.")
        return nip


class RecoveryPasswordResetForm(forms.Form):
    """
    Formulario para establecer una nueva contraseña.
    """
    new_password = forms.CharField(
        label="Nueva Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )
    confirm_password = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False
    )

    def clean_confirm_password(self):
        new_password = self.cleaned_data.get('new_password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return confirm_password




class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        exclude = ['paciente', 'medico', 'fecha']
        widgets = {
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ej. HTA, Gripe'}),
        }












#######################################################################################################
###########FORMS DE HISTORIA CLINICA MUSCULO ESQUELETICA##############################################

from django import forms
from django.contrib.postgres.forms import SimpleArrayField
# Asegúrate de importar tu modelo HistoriaClinicaMusculoEsqueletico (y tus CHOICES)

class HistoriaClinicaMusculoEsqueleticoCompletoForm(forms.ModelForm):
    # ----------------------------------------------------
    # CAMPOS ARRAYFIELD (USANDO CheckboxSelectMultiple)
    # ----------------------------------------------------
    servicio_vivienda = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.SERVICIOS_VIVIENDA_CHOICES),
        label="Servicios con los que cuenta la vivienda"
    )

    Antecedentes_familiares = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.ANTECENDENTES_FAMILIARES_CHOICES),
        label='Antecedentes Familiares'
    )

    habitos_toxicos = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.HABITOS_TOXICOS_CHOICES),
        label='Hábitos tóxicos'
    )

    Patologias = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.PATOLOGIAS_CHOICES),
        label='Patologías'
    )

    Allimentación = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.ALIMENTACION_CHOICES),
        label='Alimentación'
    )

    Tejido_celular = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.PROBLEMAS_PIEL),
        label='Tejido celular',
        required=False
    )

    class Meta:
        model = HistoriaClinicaMusculoEsqueletico
        fields = [
            # ... todos tus fields ...
            'motivo_consulta', 'comentarios', 'GradoInstruccion', 'inmunizaciones_o_vacunas',
            'baño_diario', 'aseo_dental', 'lavado_manos_antes_comer', 'lavado_manos_despues',
            'tamanio_vivienda', 'tipo_vivienda', 'servicio_vivienda', 'enfermedad_actual',
            'Antecedentes_familiares', 'habitos_toxicos', 'Allimentación', 'Ingesta_Agua',
            'Cantidad_veces_Orina', 'Catarsis', 'Somnia', 'Infancia', 'Adulto',
            'Patologias', 'ha_sido_operado', 'fecha_operacion', 'traumatismo_o_fractura', 'Otro',
            'Constitucional', 'Marcha', 'Actitud', 'Ubicacion', 'Impresion_general',
            'FC', 'TA', 'FR', 'T_Auxiliar', 'T_rectal', 'Peso_Habitual', 'Peso_Actual',
            'Talla', 'IMC', 'Aspecto', 'Distribuición_pilosa', 'Lesiones', 'Faneras',
            'Tejido_celular_subcutaneo', 'Tejido_celular',
        ]

        widgets = {
            # ----------------------------------------------------
            # WIDGETS DE OPCIÓN MÚLTIPLE (RadioSelect)
            # ----------------------------------------------------
            'baño_diario': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'aseo_dental': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_antes_comer': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_despues': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'tamanio_vivienda': forms.RadioSelect, # Asume choices definidos en el modelo
            'tipo_vivienda': forms.RadioSelect,     # Asume choices definidos en el modelo

            'ha_sido_operado': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),

            # ----------------------------------------------------
            # WIDGETS DE ENTRADA CON ESTILO DE LÍNEA Y FORMATO
            # ----------------------------------------------------
            # TextAreas (Línea larga)
            'motivo_consulta': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'enfermedad_actual': forms.Textarea(attrs={'rows': 3, 'class': 'input-linea-larga'}),
            'comentarios': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'Infancia': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),
            'Adulto': forms.Textarea(attrs={'rows': 2, 'class': 'input-linea-larga'}),

            # TextInputs (Línea corta/normal)
            'GradoInstruccion': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'inmunizaciones_o_vacunas': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'traumatismo_o_fractura': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Otro': forms.TextInput(attrs={'class': 'input-linea-corta'}),

            # Examen Físico - Inspección General (Línea corta)
            'Constitucional': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Marcha': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Actitud': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Ubicacion': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Impresion_general': forms.TextInput(attrs={'class': 'input-linea-larga'}),

            # Examen Físico - Piel (Línea corta)
            'Aspecto': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Distribuición_pilosa': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Lesiones': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Faneras': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Tejido_celular_subcutaneo': forms.TextInput(attrs={'class': 'input-linea-larga'}),

            # Signos Vitales y Antropometría (Números y Fechas)
            'Ingesta_Agua': forms.NumberInput(attrs={'class': 'input-linea-corta'}),
            'Cantidad_veces_Orina': forms.NumberInput(attrs={'class': 'input-linea-corta'}),
            'Catarsis': forms.TextInput(attrs={'class': 'input-linea-corta'}),
            'Somnia': forms.TextInput(attrs={'class': 'input-linea-corta'}),

            'FC': forms.NumberInput(attrs={'class': 'input-linea-corta'}),
            'TA': forms.TextInput(attrs={'class': 'input-linea-corta'}), # TA suele ser string (ej: 120/80)
            'FR': forms.NumberInput(attrs={'class': 'input-linea-corta'}),
            'T_Auxiliar': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),
            'T_rectal': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),
            'Peso_Habitual': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),
            'Peso_Actual': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),
            'Talla': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),
            'IMC': forms.NumberInput(attrs={'class': 'input-linea-corta', 'step': '0.1'}),

            'fecha_operacion': forms.DateInput(attrs={'type': 'date'}),
        }