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
            'apellido_paterno',  # <-- Asegúrate de que estos sean los nombres correctos del modelo
            'apellido_materno',  # <-- Asegúrate de que estos sean los nombres correctos del modelo
            'fecha_nacimiento',
            'genero',
            'telefono',
            'email',
            'direccion',
        ]
        # Opcional: widgets para Bootstrap y placeholders
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s) del paciente'}),
            'apellido_paterno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Paterno'}),
            'apellido_materno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido Materno (Opcional)'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5512345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección completa'}),
        }
        labels = {
            'nombre': 'Nombre(s)',
            'apellido_paterno': 'Apellido Paterno',
            'apellido_materno': 'Apellido Materno',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'genero': 'Género',
            'telefono': 'Teléfono',
            'email': 'Email',
            'direccion': 'Dirección',

        }
        
# Nuevo formulario para Citas
class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['paciente', 'fecha', 'hora_inicio', 'hora_fin', 'motivo', 'notas', 'estado']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
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








#Formulario Consentimiento

class ConsentimientoInformadoForm(forms.ModelForm):
    class Meta:
        model = ConsentimientoInformado
        fields = '__all__' # Incluye todos los campos del nuevo modelo

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'my-input'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'my-input my-date-input'}),
            'edad': forms.NumberInput(attrs={'class': 'my-input'}),
            'temp': forms.TextInput(attrs={'class': 'my-input'}),
            'peso': forms.TextInput(attrs={'class': 'my-input'}),
            'talla': forms.TextInput(attrs={'class': 'my-input'}),
            'ta': forms.TextInput(attrs={'class': 'my-input'}),
            'rp': forms.Textarea(attrs={'class': 'my-textarea', 'rows': 5}),
        }




# ----------------------------------------------------
# Formulario 1: Comentarios y fecha de internación
# ----------------------------------------------------
class CuestionarioParte1Form(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'motivo_consulta',
            'comentarios',
            
        ]

# ----------------------------------------------------
# Formulario 2: Datos generales y vivienda
# ----------------------------------------------------

class CheckboxCardSelectMultiple(CheckboxSelectMultiple):
    template_name = 'forms/widgets/checkbox_card_multiple.html'
   # El código de SimpleArrayField que tenías arriba ya no es necesario
# ----------------------------------------------------
# Formulario 2: Datos generales y vivienda
# ----------------------------------------------------
class CuestionarioParte2Form(forms.ModelForm):
    # Campos que usan ArrayField y necesitan una configuración especial
    servicio_vivienda = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.SERVICIOS_VIVIENDA_CHOICES),
        label="Servicios con los que cuenta la vivienda"
    )
    
    Antecedentes_familiares = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.ANTECENDENTES_FAMILIARES_CHOICES),
        label='Antecedentes Familiares'
    )
    
    habitos_toxicos = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.HABITOS_TOXICOS_CHOICES),
        label='Hábitos tóxicos'
    )
    
    Patologias = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.PATOLOGIAS_CHOICES),
        label='Patologías'
    )
    
    Allimentación = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.ALIMENTACION_CHOICES),
        label='Alimentación'
    )
    
    class Meta:
        model = HistoriaClinica
        fields = [
            'GradoInstruccion',
            'inmunizaciones_o_vacunas',
            'baño_diario',
            'aseo_dental',
            'lavado_manos_antes_comer',
            'lavado_manos_despues',
            'tamanio_vivienda',
            'tipo_vivienda',
            'servicio_vivienda',
            'enfermedad_actual',
            'Antecedentes_familiares',
            'habitos_toxicos',
            'Allimentación',
            'Ingesta_Agua',
            'Cantidad_veces_Orina',
            'Catarsis',
            'Somnia',
            'Infancia',
            'Adulto',
            'Patologias',
            'ha_sido_operado',
            'fecha_operacion',
            'traumatismo_o_fractura',
            'Otro'
        ]
        
        widgets = {
            'baño_diario': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'aseo_dental': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_antes_comer': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_despues': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'tamanio_vivienda': forms.RadioSelect,
            'tipo_vivienda': forms.RadioSelect,
            'fecha_operacion': forms.DateInput(attrs={'type': 'date'}),
            # Aquí es donde vas a usar tu widget personalizado para los ArrayFields
            'servicio_vivienda': CheckboxCardSelectMultiple(choices=HistoriaClinica.SERVICIOS_VIVIENDA_CHOICES),
            'Antecedentes_familiares': CheckboxCardSelectMultiple(choices=HistoriaClinica.ANTECENDENTES_FAMILIARES_CHOICES),
            'habitos_toxicos': CheckboxCardSelectMultiple(choices=HistoriaClinica.HABITOS_TOXICOS_CHOICES),
            'Patologias': CheckboxCardSelectMultiple(choices=HistoriaClinica.PATOLOGIAS_CHOICES),
            'Allimentación': CheckboxCardSelectMultiple(choices=HistoriaClinica.ALIMENTACION_CHOICES),
        
        }      

# ----------------------------------------------------
# Formulario 3: Datos ginecológicos (condicional)
# ----------------------------------------------------
class CuestionarioGinecologicoForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'fum',
            'fpp',
            'edad_gestacional',
            'menarquia',
            'rm_rit_menstr',
            'irs',
            'no_de_parejas',
            'flujo_genital',
            'gestas',
            'partos',
            'cesareas',
            'abortos',
            'anticonceptivos',
            'anticonceptivos_tipo',
            'anticonceptivos_tiempo',
            'anticonceptivos_ultima_toma',
            'cirugia_ginecologica',
            'otros_ginecologicos',
        ]
        
        widgets = {
            'fum': forms.DateInput(attrs={'type': 'date'}),
            'fpp': forms.DateInput(attrs={'type': 'date'}),
            'anticonceptivos_ultima_toma': forms.DateInput(attrs={'type': 'date'}),
        }
#######################################################################################################
################SEGUNDA HOJA ##########################################################################


# ----------------------------------------------------
# Formulario 1: Sistema Digestivo
# ----------------------------------------------------
class CuestionarioDigestivoForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'digest_halitosis', 'digest_boca_seca', 'digest_masticacion', 'digest_disfagia',
            'digest_pirosis', 'digest_nausea', 'digest_vomito_hematemesis', 'digest_colicos',
            'digest_dolor_abdominal', 'digest_meteorismo', 'digest_flatulencias',
            'digest_constipacion', 'digest_diarrea', 'digest_rectorragias', 'digest_melenas',
            'digest_pujo', 'digest_tenesmo', 'digest_ictericia', 'digest_coluria',
            'digest_acolia', 'digest_prurito_cutaneo', 'digest_hemorragias',
            'digest_prurito_anal', 'digest_hemorroides', 'Comentarios_digestivo'
        ]
        widgets = {
            # Se usa CheckboxSelectMultiple para los BooleanFields
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
        }

# ----------------------------------------------------
# Formulario 2: Aparato Cardiovascular y Respiratorio
# ----------------------------------------------------
class CuestionarioCardioRespiratorioForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'cardio_tos_seca', 'cardio_tos_espasmodica', 'cardio_hemoptisis',
            'cardio_dolor_precordial', 'cardio_palpitaciones', 'cardio_cianosis',
            'cardio_edema', 'cardio_acufenos', 'cardio_fosfenos', 'cardio_sincope',
            'cardio_lipotimia', 'cardio_cefaleas', 'pulso_carotideo', 'pulso_humeral',
            'pulso_radial', 'pulso_femoral', 'pulso_popliteo', 'pulso_tibial_posterior',
            'pulso_pedio', 'pulso_carotideo_izq', 'pulso_humeral_izq',
            'pulso_radial_izq', 'pulso_femoral_izq', 'pulso_popliteo_izq', 'pulso_tibial_posterior_izq',
            'pulso_pedio_izq','resp_tos', 'resp_disnea', 'resp_dolor_toracico',
            'resp_hemoptisis', 'resp_cianosis', 'resp_vomica', 'resp_alteraciones_voz','Comentarios_cardio', 'Comentarios_respiratorio'
        ]
        widgets = {
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
        }

# ----------------------------------------------------
# Formulario 3: Aparato Genital y Urinario
# ----------------------------------------------------
# Asegúrate de importar esto en la parte superior de tu archivo
# from django.forms import forms, ModelForm, CheckboxInput
# from .models import HistoriaClinica # O el nombre de tu modelo

class CuestionarioGenitalUrinarioForm(forms.ModelForm):

    class Meta:
        model = HistoriaClinica
        fields = [
            'genital_criptorquidea', 'genital_fimosis', 'genital_funcion_sexual',
            'genital_sangrado_genital', 'genital_flujo_leucorrea', 'genital_dolor_ginecologico',
            'genital_prurito_vulvar','Comentarios_genital',
            
            # Nuevos campos de Alteraciones en la Micción
            'Poliuria', 'Anuria', 'Oliguria', 'Nicturia', 'Opsuria',
            'Disuria', 'Tenesmo_vesical', 'Urgencia', 'Chorro',
            'Enuresis', 'Incontinencia', 'Ninguna',
            
            'urin_volumen_orina',
            'urin_color_orina', 'urin_olor_orina', 'urin_aspecto_orina',
            'urin_dolor_lumbar', 'urin_edema_palpebral_sup', 'urin_edema_palpebral_inf',
            'urin_edema_renal', 'urin_hipertension_arterial', 'urin_datos_clinicos_anemia',
            
            # Nuevo campo de comentarios
            'Comentarios_urinario',
        ]
        
        widgets = {
            'genital_criptorquidea': forms.CheckboxInput(),
            'genital_fimosis': forms.CheckboxInput(),
            'genital_funcion_sexual': forms.CheckboxInput(),
            'genital_sangrado_genital': forms.CheckboxInput(),
            'genital_flujo_leucorrea': forms.CheckboxInput(),
            'genital_dolor_ginecologico': forms.CheckboxInput(),
            'genital_prurito_vulvar': forms.CheckboxInput(),
            
            # Widgets para los nuevos campos de Alteraciones en la Micción
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
            
            'urin_dolor_lumbar': forms.CheckboxInput(),
            'urin_edema_palpebral_sup': forms.CheckboxInput(),
            'urin_edema_palpebral_inf': forms.CheckboxInput(),
            'urin_edema_renal': forms.CheckboxInput(),
            'urin_hipertension_arterial': forms.CheckboxInput(),
            'urin_datos_clinicos_anemia': forms.CheckboxInput(),
        }

# ----------------------------------------------------
# Formulario 4: Hematológico, Endocrino y Exploración de Cuello
# ----------------------------------------------------
class CuestionarioEndocrinoCuelloForm(forms.ModelForm):
    
    class Meta:
        model = HistoriaClinica
        fields = [
            # Nuevos campos de Aparato Hematológico
            'Palidez', 'Astenia', 'Adinamia', 'Otros',
            'hemato_hemorragias', 'hemato_adenopatias', 'hemato_esplenomegalia',
            'Comentarios_anemia',
            
            # Campos de Aparato Endocrino
            'endocr_bocio', 'endocr_letargia', 'endocr_bradipsiquia_idia',
            'endocr_intolerancia_calor_frio', 'endocr_nerviosismo', 'endocr_hiperquinesis',
            'endocr_caracteres_sexuales', 'endocr_galactorrea', 'endocr_amenorrea',
            'endocr_ginecomastia', 'endocr_obesidad', 'endocr_ruborizacion',
            'Comentarios_endocrino',
            
            # Campos de Exploración de Cuello
            'cuello_tiroides', 'cuello_musculos', 'cuello_ganglios_linfaticos',
        ]
        
        widgets = {
            # Widgets de Aparato Hematológico
            'Palidez': forms.CheckboxInput(),
            'Astenia': forms.CheckboxInput(),
            'Adinamia': forms.CheckboxInput(),
            'hemato_hemorragias': forms.CheckboxInput(),
            'hemato_adenopatias': forms.CheckboxInput(),
            'hemato_esplenomegalia': forms.CheckboxInput(),
            
            # Widgets de Aparato Endocrino
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
        }#######################################################################################################
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

# ----------------------------------------------------
# Formulario 2: Exploración de MMII y Nasal
# ----------------------------------------------------
class CuestionarioExploracion2Form(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'art_cadera_ab', 'art_cadera_ad', 'art_cadera_f', 'art_cadera_e',
            'art_tobillo_f', 'art_tobillo_e',
            'art_subastragalina_f', 'art_subastragalina_ev',
            
            'nasal_mucosa', 'nasal_cochas', 'nasal_vascularizacion',
        ]
#######################################################################################################
################CUARTA HOJA ##########################################################################
# ----------------------------------------------------
# Formulario 1: Pulsos y Estado de Conciencia
# ----------------------------------------------------
class CuestionarioPulsosConcienciaForm(forms.ModelForm):
    class Meta:
        model = HistoriaClinica
        fields = [
            'me_pulso_carotideo_derecho', 'me_pulso_carotideo_izquierdo',
            'me_pulso_humeral_derecho', 'me_pulso_humeral_izquierdo',
            'me_pulso_radial_derecho', 'me_pulso_radial_izquierdo',
            'me_pulso_femoral_derecho', 'me_pulso_femoral_izquierdo',
            'me_pulso_popliteo_derecho', 'me_pulso_popliteo_izquierdo',
            'me_pulso_tibial_posterior_derecho', 'me_pulso_tibial_posterior_izquierdo',
            'me_pulso_pedio_derecho', 'me_pulso_pedio_izquierdo',
            'ascitis', 'Estado_Conciencia',
        ]
        widgets = {
            'ascitis': forms.CheckboxInput(),
        }

# ----------------------------------------------------
# Formulario 2: Escala de Glasgow y Exploración Visual
# ----------------------------------------------------
class CuestionarioGlasgowVisualForm(forms.ModelForm):
    campos_visuales_opciones = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinica.CAMPOS_VISUALES_CHOICES),
        label='Campos Visuales Opciones'
    )
    
    class Meta:
        model = HistoriaClinica
        fields = [
            'glasgow_apertura_ojos_respuesta', 'glasgow_apertura_ojos_puntuacion',
            'glasgow_respuesta_verbal_respuesta', 'glasgow_respuesta_verbal_puntuacion',
            'glasgow_respuesta_motora_respuesta', 'glasgow_respuesta_motora_puntuacion',
            'reflejo_fotomotor_tamano', 'reflejo_fotomotor_relaciones',
            'reflejo_fotomotor_respuestas_luz', 'par_craneal_iii_oculomotor',
            'par_craneal_iv_patetico', 'par_craneal_vi_motor_ocular_externo',
            'retina_relacion_arterio_venosa',
            'retina_macula', 'campos_visuales_opciones', 'par_craneal_iii_oculomotor_cv', 
            'par_craneal_iv_patetico_cv', 'par_craneal_vi_motor_ocular_externo_cv'
        ]
        
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
            'medicamento': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Nombre del medicamento'}),
            'dosis': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ej. 500mg, 1 pastilla c/8h'}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ej. HTA, Gripe'}),
            'indicaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Indicaciones adicionales'}),
        }
        
        
        









#######################################################################################################
###########FORMS DE HISTORIA CLINICA MUSCULO ESQUELETICA##############################################


# ----------------------------------------------------
# Formulario 1: Comentarios y fecha de internación
# ----------------------------------------------------
class CuestionarioParte1FormME(forms.ModelForm):
    class Meta:
        model = HistoriaClinicaMusculoEsqueletico
        fields = [
            'motivo_consulta',
            'comentarios',
            
        ]
    

# ----------------------------------------------------
# Formulario 2: Datos generales y vivienda
# ----------------------------------------------------
class CuestionarioParte2FormME(forms.ModelForm):
    # Campos que usan ArrayField y necesitan una configuración especial
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
    
    class Meta:
        model = HistoriaClinicaMusculoEsqueletico
        fields = [
            'GradoInstruccion',
            'inmunizaciones_o_vacunas',
            'baño_diario',
            'aseo_dental',
            'lavado_manos_antes_comer',
            'lavado_manos_despues',
            'tamanio_vivienda',
            'tipo_vivienda',
            'servicio_vivienda',
            'enfermedad_actual',
            'Antecedentes_familiares',
            'habitos_toxicos',
            'Allimentación',
            'Ingesta_Agua',
            'Cantidad_veces_Orina',
            'Catarsis',
            'Somnia',
            'Infancia',
            'Adulto',
            'Patologias',
            'ha_sido_operado',
            'fecha_operacion',
            'traumatismo_o_fractura',
            'Otro'
        ]
        
        widgets = {
            'baño_diario': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'aseo_dental': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_antes_comer': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'lavado_manos_despues': forms.RadioSelect(choices=[('Sí', 'Sí'), ('No', 'No')]),
            'tamanio_vivienda': forms.RadioSelect,
            'tipo_vivienda': forms.RadioSelect,
            'fecha_operacion': forms.DateInput(attrs={'type': 'date'}),
        }
class ExamenFisicoForm(forms.ModelForm):
    # Campo que usa ArrayField
    Tejido_celular = SimpleArrayField(
        forms.CharField(),
        widget=forms.CheckboxSelectMultiple(choices=HistoriaClinicaMusculoEsqueletico.PROBLEMAS_PIEL),
        label='Tejido celular',
        required=False
    )
    
    class Meta:
        model = HistoriaClinicaMusculoEsqueletico
        fields = [
            # Inspección general
            'Constitucional',
            'Marcha',
            'Actitud',
            'Ubicacion',
            'Impresion_general',
            # Signos Vitales
            'FC',
            'TA',
            'FR',
            'T_Auxiliar',
            'T_rectal',
            'Peso_Habitual',
            'Peso_Actual',
            'Talla',
            'IMC',
            # Piel, Faneras y Tejido celular subcutáneo
            'Aspecto',
            'Distribuición_pilosa',
            'Lesiones',
            'Faneras',
            'Tejido_celular_subcutaneo',
        ]