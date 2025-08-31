from django.db import models
from django.conf import settings # Para referenciar el modelo de Usuario (Doctor)
from django.forms import ModelForm
from django import forms
from datetime import date
from django.contrib.auth.models import User, AbstractUser # Importamos el modelo User de Django
from django.core.validators import RegexValidator
from django.contrib.postgres.fields import ArrayField
from django.conf import settings # ¡Paso 1: Importar settings!


# Create your models here.

from django.db import models


class CustomUser(AbstractUser):
    # Ya tenías un ID explícito aquí, lo mantengo.
    id = models.BigAutoField(primary_key=True, editable=False)

    # CORRECCIÓN PARA EL ERROR DE related_name
    # Estos campos ya existen en AbstractUser, pero los redeclaramos
    # para añadir un related_name único.
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=('groups'),
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set", # ¡CAMBIO AQUÍ! Nombre único
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=('user permissions'),
        blank=True,
        help_text=('Specific permissions for this user.'),
        related_name="customuser_set", # ¡CAMBIO AQUÍ! Nombre único
        related_query_name="customuser",
    )

    USER_TYPE_CHOICES = (
        ('doctor', 'Doctor'),
        ('farmacia', 'Farmacia'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='doctor')

    # Campo para el NIP de recuperación, ahora directamente en el modelo de usuario
    recovery_nip = models.CharField(
        max_length=4,
        validators=[RegexValidator(r'^\d{4}$', 'El NIP debe ser un número de 4 dígitos.')],
        help_text="Introduce un NIP de 4 dígitos para recuperar tu cuenta.",
        unique=True,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username

class Doctor(models.Model):
    # OneToOneField asegura que cada CustomUser tenga un único perfil de Doctor
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='doctor_profile',
        verbose_name="Usuario Asociado"
    )
    # Campos adicionales para el doctor
    especialidad = models.CharField(max_length=100, blank=True, null=True, verbose_name="Especialidad")
    telefono_consultorio = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono del Consultorio")
    
    def __str__(self):
        full_name = self.user.get_full_name()
        if not full_name:
            full_name = self.user.username
        return f"Dr(a). {full_name} ({self.especialidad if self.especialidad else 'Sin Especialidad'})"

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctores"

# 3. Tu modelo de perfil para Farmacias: FarmaciaProfile
class FarmaciaProfile(models.Model):
    # ¡NUEVO CAMPO ID! Este será el ID primario para FarmaciaProfile.
    id = models.BigAutoField(primary_key=True, editable=False)

    # El OneToOneField ahora NO tiene primary_key=True.
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, unique=True, related_name='farmacia_profile')
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="farmacias",
        verbose_name="Doctor Asociado"
    )
    # ... otros campos específicos de la farmacia (los que tengas o los que vayas a añadir) ...

    def __str__(self):
        # Asegúrate de que este __str__ use un campo que exista, como el ID o el nombre de usuario asociado
        return f"Perfil de Farmacia (ID: {self.id}): {self.user.username}"



class Paciente(models.Model):
    # Campo 'id' como clave primaria auto-incrementable
    # Django lo crea automáticamente si no se define una primary_key,
    # pero aquí lo estamos haciendo explícito.
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)

    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=10, choices=[('Masculino', 'Masculino'), ('Femenino', 'Femenino'), ('Otro', 'Otro')])
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True) # Uso null=True para la BD
    direccion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    numero_expediente = models.CharField(max_length=50, unique=True, blank=True, null=True)
    doctor_responsable = models.ForeignKey(
        Doctor, 
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='pacientes_asignados', # Nombre más claro para la relación inversa
        verbose_name="Doctor Responsable"
    )

    def __str__(self):
        # Una forma más robusta de construir el nombre completo, manejando campos nulos.
        full_name_parts = [self.nombre, self.apellido_paterno]
        if self.apellido_materno:
            full_name_parts.append(self.apellido_materno)
        return " ".join(filter(None, full_name_parts)).strip()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        
        
        
        
        
        
# Nuevo modelo para las Citas
class Cita(models.Model):
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name="Paciente"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Referencia al modelo de usuario que puede ser el doctor
        on_delete=models.SET_NULL, # Si el doctor es eliminado, no elimina la cita, solo pone el campo a NULL
        related_name='citas_como_doctor',
        null=True,
        blank=True,
        verbose_name="Doctor"
    )
    
    fecha = models.DateField(verbose_name="Fecha de la Cita")
    hora_inicio = models.TimeField(verbose_name="Hora de Inicio")
    hora_fin = models.TimeField(verbose_name="Hora de Fin")
    
    MOTIVO_CHOICES = [
        ('Consulta', 'Consulta General'),
        ('Seguimiento', 'Seguimiento'),
        ('Terapia', 'Sesión de Terapia'),
        ('Emergencia', 'Emergencia'),
        ('Otro', 'Otro'),
    ]
    motivo = models.CharField(
        max_length=50,
        choices=MOTIVO_CHOICES,
        default='Consulta',
        verbose_name="Motivo de la Cita"
    )
    
    notas = models.TextField(blank=True, null=True, verbose_name="Notas Adicionales")
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Confirmada', 'Confirmada'),
        ('Completada', 'Completada'),
        ('Cancelada', 'Cancelada'),
        ('Reprogramada', 'Reprogramada'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Pendiente',
        verbose_name="Estado de la Cita"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['fecha', 'hora_inicio'] # Ordena las citas por fecha y luego por hora
        unique_together = ('doctor', 'fecha', 'hora_inicio') # Un doctor no puede tener dos citas a la misma hora en la misma fecha

    def __str__(self):
        doctor_str = self.doctor.username if self.doctor else "Sin Doctor"
        return f"Cita de {self.paciente.nombre} con {doctor_str} el {self.fecha} a las {self.hora_inicio}"

    # Puedes añadir métodos para validar la hora o duración si lo necesitas más adelante
    def clean(self):
        # Validación para asegurarse de que la hora de inicio sea anterior a la hora de fin
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            from django.core.exceptions import ValidationError
            raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')
        # Aquí podrías añadir validación para no superponer citas, etc.
        
        
        
        

class ConsentimientoInformado(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consentimientos_simplificados')
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Paciente")
    fecha = models.DateField(default=date.today)
    edad = models.IntegerField(null=True, blank=True)
    temp = models.CharField(max_length=50, blank=True, null=True, verbose_name="Temperatura")
    peso = models.CharField(max_length=50, blank=True, null=True, verbose_name="Peso")
    talla = models.CharField(max_length=50, blank=True, null=True, verbose_name="Talla")
    ta = models.CharField(max_length=50, blank=True, null=True, verbose_name="T/A (Tensión Arterial)")
    rp = models.TextField(blank=True, null=True, verbose_name="Rp. (Receta o Recomendación)")

    def __str__(self):
        return f"Consentimiento simplificado de {self.nombre} ({self.fecha})"       
    
    
    
    
    
    
    

def get_default_servicios():
    return ['-----']






class HistoriaClinica(models.Model):
    id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='PacienteHistoriaClinica')
    no_historia_clinica = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de Historia Clínica") 
    fecha_registro = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")
    comentarios = models.TextField(blank=True, null=True, verbose_name="ComentariosAdicionales")
    fecha_internacion = models.DateField(blank=True, null=True)
    GradoInstruccion = models.CharField(max_length=255, blank=True, null=True)
    inmunizaciones_o_vacunas = models.TextField(blank=True, null=True)
    baño_diario = models.CharField(max_length=100, blank=True, null=True)
    aseo_dental = models.CharField(max_length=100, blank=True, null=True)
    lavado_manos_antes_comer = models.CharField(max_length=100, blank=True, null=True)
    lavado_manos_despues = models.CharField(max_length=100, blank=True, null=True)
    CHOICES_TAMANIO_VIVIENDA_CUARTOS = [
    ('1_cuarto', '1 Cuarto'),
    ('2_cuartos', '2 Cuartos'),
    ('3_cuartos', '3 Cuartos'),
    ('4_cuartos', '4 Cuartos'),
    ('5_o_mas_cuartos', '5 o más Cuartos'),
    ]

    tamanio_vivienda = models.CharField(max_length=100, blank=True, null=True, choices=CHOICES_TAMANIO_VIVIENDA_CUARTOS)
    CHOICES_TIPO_VIVIENDA = [

    ('Casa independiente (particular)', 'Casa independiente (particular)'),
    ('Departamento en edificio o condominio', 'Departamento en edificio o condominio'),
    ('Vivienda en vecindad', 'Vivienda en vecindad'),
    ('Cuarto en vivienda compartida', 'Cuarto en vivienda compartida'),
    ('Vivienda en local no construido para habitación', 'Vivienda en local no construido para habitación'), # Ej. locales comerciales adaptados
    ('Vivienda móvil (casa rodante, barco, etc.)', 'Vivienda móvil (casa rodante, barco, etc.)'),
    ('Refugio (albergue, casa hogar, etc.)', 'Refugio (albergue, casa hogar, etc.)'),
    ('otro', 'Otro tipo de vivienda')
    ]

    tipo_vivienda = models.CharField(max_length=100, blank=True, null=True, choices=CHOICES_TIPO_VIVIENDA)

    SERVICIOS_VIVIENDA_CHOICES = [
    ('-----', '-----'),
    ('agua', 'Agua Potable'),
    ('luz', 'Electricidad'),
    ('gas', 'Gas Natural'),
    ('internet', 'Internet'),
    ('telefonia', 'Telefonía Fija'),
    ('alcantarillado', 'Alcantarillado'),
    ('recoleccion_basura', 'Recolección de Basura'),
    # ¡Aquí es donde pones las opciones!
                                    ]
    servicio_vivienda = ArrayField(
        models.CharField(max_length=50, choices=SERVICIOS_VIVIENDA_CHOICES),
        null=True,
        blank=True,
        verbose_name="Servicios con los que cuenta la vivienda", default=get_default_servicios
        )
    ANTECENDENTES_FAMILIARES_CHOICES = [
    ('-----', '-----'),
    ('Tuberculosis', 'Tuberculosis'),
    ('Diabetes', 'Diabetes'),
    ('Hipertensión', 'Hipertensión'),
    ('Obesidad', 'Obesidad'),
    ('Malformaciones', 'Malformaciones Congenitas'),
    ('Cáncer', 'Cáncer'),
    ('Alergias', 'Alergias'),
    ('Cardiacas','Enfermedades Cardiacas'),
    ('Psiquiátricas','Enfermdedades Psiquiátricas'),
    ('Reumaticas','Enfermedades Reumaticas'),
    ('Tumores','Tumores'),
    ('Luéticos','Luéticos'),
    ('Otros', 'otros')]
    motivo_consulta = models.TextField(null=True, blank=True, verbose_name="Motivo de Consulta")
    enfermedad_actual = models.CharField(max_length=50, blank=True, null=True)
        #ANTECEDENTES FAMILIARES
    Antecedentes_familiares = ArrayField(models.CharField(max_length=50, 
                                                        choices=ANTECENDENTES_FAMILIARES_CHOICES,
                                                        blank=True,
                                                        verbose_name='Antecendentes Familiares'))
        #ANTECEDENTES PERSONALES

        #Habitos tóxicos
    HABITOS_TOXICOS_CHOICES = [
        ('-----', '-----'),
            ('Alcohol','Alcohol'),
            ('Tabaquismo', 'Tabaquismo'),
            ('Drogas','Drogas'),
            ('Infusiones','Infusiones'),
            ('No aplica','No aplica'),
            
        ]
    habitos_toxicos = ArrayField(models.CharField(max_length=50, choices=HABITOS_TOXICOS_CHOICES, blank=True,null=True, verbose_name='Hábitos tóxicos', default=get_default_servicios))
        #Hábitos fisiologicos
    ALIMENTACION_CHOICES = [
        ('-----', '-----'),
            ('Carnivora', 'Carnivora'),
            ('vegetariana', 'Vegetariana'),
            ('vegana', 'Vegana (no productos animales)'),
            ('pescetariana', 'Pescetariana (no carne, sí pescado)'),
            ('flexitariana', 'Flexitariana (principalmente vegetariana, poca carne)'),
            ('keto', 'Cetogénica (Keto)'),
            ('paleo', 'Paleo'),
            ('otra', 'Otra (especifique)'), # Opción para describir si no está en la lista
            ('no_aplica', 'No aplica / No sabe / No responde'), # Para casos donde no se puede clasificar
            ]

    Allimentación = ArrayField(models.CharField(max_length=50, choices=ALIMENTACION_CHOICES, blank=True, null=True, default=get_default_servicios))
    Ingesta_Agua = models.IntegerField(blank=True, null=True, verbose_name='Ingesta de agua litros')
    Cantidad_veces_Orina = models.IntegerField(blank=True, null=True, verbose_name='Cantidad de veces de orina')
    Catarsis = models.CharField(max_length=50, null=True, blank=True)
    Somnia = models.CharField(max_length=50, null=True, blank=True)

        #Patologicosss
    PATOLOGIAS_CHOICES = [
            ('-----', '-----'),
            ('Herpes','Herpes'),
            ('Hepatitis','Hepatitis'),
            ('HTA','HTA'),
            ('Alergias','Alergias'),
            ('Diabetes','Diabetes'),
            ('Tifoidea','Tifoidea'),
            ('TBC','TBC'),
            ('Caries','Caries'),
            ('Rubeola','Rubeola'),
            ('Neoplasis','Neoplasis'),
            ('Otros','Otros'),    
        ]
    Infancia = models.TextField(max_length=100, blank=True, null=True)
    Adulto = models.TextField(max_length=100, blank=True, null=True)
    Patologias = ArrayField(models.CharField(max_length=50, choices=PATOLOGIAS_CHOICES,blank=True, null=True, default=get_default_servicios))

    ha_sido_operado = models.BooleanField(default=False)
    fecha_operacion = models.DateField(blank=True, null=True)
    traumatismo_o_fractura = models.BooleanField(blank=True, null=True)
    Otro = models.TextField(blank=True, null=True)

  
        #GINECO - OBSTRETICOS
    fum = models.DateField(blank=True, null=True)
    fpp = models.DateField(blank=True, null=True)
    edad_gestacional = models.IntegerField(blank=True, null=True)
    menarquia = models.IntegerField(blank=True, null=True)
    rm_rit_menstr = models.CharField(max_length=50, blank=True, null=True)
    irs = models.CharField(max_length=50, blank=True, null=True)
    no_de_parejas = models.IntegerField(blank=True, null=True)
    flujo_genital = models.CharField(max_length=100, blank=True, null=True)
    gestas = models.IntegerField(blank=True, null=True)
    partos = models.IntegerField(blank=True, null=True)
    cesareas = models.IntegerField(blank=True, null=True)
    abortos = models.IntegerField(blank=True, null=True)
    anticonceptivos = models.CharField(max_length=100, blank=True, null=True)
    anticonceptivos_tipo = models.CharField(max_length=100, blank=True, null=True)
    anticonceptivos_tiempo = models.CharField(max_length=100, blank=True, null=True)
    anticonceptivos_ultima_toma = models.DateField(blank=True, null=True)
    cirugia_ginecologica = models.TextField(blank=True, null=True)
    otros_ginecologicos = models.TextField(blank=True, null=True)
        ##################################################################################################
        #INTERROGATORIO PARA APARATOS Y SISTEMAS

    digest_halitosis = models.BooleanField(default=False, null=True, blank=True)
    digest_boca_seca = models.BooleanField(default=False, null=True, blank=True)
    digest_masticacion = models.BooleanField(default=False, null=True, blank=True)
    digest_disfagia = models.BooleanField(default=False, null=True, blank=True)
    digest_pirosis = models.BooleanField(default=False, null=True, blank=True)
    digest_nausea = models.BooleanField(default=False, null=True, blank=True)
    digest_vomito_hematemesis = models.BooleanField(default=False, null=True, blank=True)
    digest_colicos = models.BooleanField(default=False, null=True, blank=True)
    digest_dolor_abdominal = models.BooleanField(default=False, null=True, blank=True)
    digest_meteorismo = models.BooleanField(default=False, null=True, blank=True)
    digest_flatulencias = models.BooleanField(default=False, null=True, blank=True)
    digest_constipacion = models.BooleanField(default=False, null=True, blank=True)
    digest_diarrea = models.BooleanField(default=False, null=True, blank=True)
    digest_rectorragias = models.BooleanField(default=False, null=True, blank=True)
    digest_melenas = models.BooleanField(default=False, null=True, blank=True)
    digest_pujo = models.BooleanField(default=False, null=True, blank=True)
    digest_tenesmo = models.BooleanField(default=False, null=True, blank=True)
    digest_ictericia = models.BooleanField(default=False, null=True, blank=True)
    digest_coluria = models.BooleanField(default=False, null=True, blank=True)
    digest_acolia = models.BooleanField(default=False, null=True, blank=True)
    digest_prurito_cutaneo = models.BooleanField(default=False, null=True, blank=True)
    digest_hemorragias = models.BooleanField(default=False, null=True, blank=True)
    digest_prurito_anal = models.BooleanField(default=False, null=True, blank=True)
    digest_hemorroides = models.BooleanField(default=False, null=True, blank=True)
    Comentarios_digestivo = models.CharField(max_length=200, blank=True, null=True)
        # Aparato Cardiovascular
    cardio_tos_seca = models.BooleanField(default=False)
    cardio_tos_espasmodica = models.BooleanField(default=False)
    cardio_hemoptisis = models.BooleanField(default=False)
    cardio_dolor_precordial = models.BooleanField(default=False)
    cardio_palpitaciones = models.BooleanField(default=False)
    cardio_cianosis = models.BooleanField(default=False)
    cardio_edema = models.BooleanField(default=False)
    cardio_acufenos = models.BooleanField(default=False)
    cardio_fosfenos = models.BooleanField(default=False)
    cardio_sincope = models.BooleanField(default=False)
    cardio_lipotimia = models.BooleanField(default=False)
    cardio_cefaleas = models.BooleanField(default=False)
    Comentarios_cardio = models.CharField(max_length=200, blank=True, null=True)

    # Aparato Cardiovascular
    #derecho
    pulso_carotideo = models.CharField(max_length=50,blank=True, null=True)
    pulso_humeral = models.CharField(max_length=50,blank=True, null=True)
    pulso_radial = models.CharField(max_length=50,blank=True, null=True)
    pulso_femoral = models.CharField(max_length=50, blank=True, null=True)
    pulso_popliteo = models.CharField(max_length=50, blank=True, null=True)
    pulso_tibial_posterior = models.CharField(max_length=50, blank=True, null=True)
    pulso_pedio = models.CharField(max_length=50, blank=True, null=True)
    #izquierdo
    pulso_carotideo_izq = models.CharField(max_length=50,blank=True, null=True)
    pulso_humeral_izq = models.CharField(max_length=50,blank=True, null=True)
    pulso_radial_izq = models.CharField(max_length=50,blank=True, null=True)
    pulso_femoral_izq = models.CharField(max_length=50, blank=True, null=True)
    pulso_popliteo_izq = models.CharField(max_length=50, blank=True, null=True)
    pulso_tibial_posterior_izq = models.CharField(max_length=50, blank=True, null=True)
    pulso_pedio_izq = models.CharField(max_length=50, blank=True, null=True)

        # Aparato Respiratorio
    resp_tos = models.BooleanField(default=False)
    resp_disnea = models.BooleanField(default=False)
    resp_dolor_toracico = models.BooleanField(default=False)
    resp_hemoptisis = models.BooleanField(default=False)
    resp_cianosis = models.BooleanField(default=False)
    resp_vomica = models.BooleanField(default=False)
    resp_alteraciones_voz = models.BooleanField(default=False)
    Comentarios_respiratorio = models.CharField(max_length=200, blank=True, null=True)

        # Aparato Genital
    genital_criptorquidea = models.BooleanField(default=False)
    genital_fimosis = models.BooleanField(default=False)
    genital_funcion_sexual = models.BooleanField(default=False)
    genital_sangrado_genital = models.BooleanField(default=False)
    genital_flujo_leucorrea = models.BooleanField(default=False)
    genital_dolor_ginecologico = models.BooleanField(default=False)
    genital_prurito_vulvar = models.BooleanField(default=False)
    Comentarios_genital = models.CharField(max_length=200, blank=True, null=True)
        # Aparato Urinario
    #Alteraciones en la Micción
    Poliuria = models.BooleanField(default=False)
    Anuria = models.BooleanField(default=False)
    Oliguria = models.BooleanField(default=False)
    Nicturia = models.BooleanField(default=False)
    Opsuria = models.BooleanField(default=False)
    Disuria = models.BooleanField(default=False)
    Tenesmo_vesical = models.BooleanField(default=False)
    Urgencia = models.BooleanField(default=False)
    Chorro = models.BooleanField(default=False)
    Enuresis = models.BooleanField(default=False)
    Incontinencia = models.BooleanField(default=False)
    Ninguna = models.BooleanField(default=False)
    #CARACTERES EN LA ORINA
    urin_volumen_orina = models.CharField(max_length=100, blank=True, null=True)
    urin_color_orina = models.CharField(max_length=100, blank=True, null=True)
    urin_olor_orina = models.CharField(max_length=100, blank=True, null=True)
    urin_aspecto_orina = models.CharField(max_length=100, blank=True, null=True)
    urin_dolor_lumbar = models.BooleanField(default=False)
    urin_edema_palpebral_sup = models.BooleanField(default=False)
    urin_edema_palpebral_inf = models.BooleanField(default=False)
    urin_edema_renal = models.BooleanField(default=False)
    urin_hipertension_arterial = models.BooleanField(default=False)
    urin_datos_clinicos_anemia = models.BooleanField(default=False)
    Comentarios_urinario = models.CharField(max_length=200, blank=True, null=True)
    #Aparato Hematológico
    #Subitulo de anemia
    Palidez = models.BooleanField(default=False)
    Astenia = models.BooleanField(default=False)
    Adinamia = models.BooleanField(default=False)
    Otros = models.CharField(max_length=100, blank=True, null=True)
    hemato_hemorragias = models.BooleanField(default=False)
    hemato_adenopatias = models.BooleanField(default=False)
    hemato_esplenomegalia = models.BooleanField(default=False)
    Comentarios_anemia = models.CharField(max_length=200, blank=True, null=True)
        # Aparato Endocrino
    endocr_bocio = models.BooleanField(default=False)
    endocr_letargia = models.BooleanField(default=False)
    endocr_bradipsiquia_idia = models.BooleanField(default=False)
    endocr_intolerancia_calor_frio = models.BooleanField(default=False)
    endocr_nerviosismo = models.BooleanField(default=False)
    endocr_hiperquinesis = models.BooleanField(default=False)
    endocr_caracteres_sexuales = models.BooleanField(default=False)
    endocr_galactorrea = models.BooleanField(default=False)
    endocr_amenorrea = models.BooleanField(default=False)
    endocr_ginecomastia = models.BooleanField(default=False)
    endocr_obesidad = models.BooleanField(default=False)
    endocr_ruborizacion = models.BooleanField(default=False)
    Comentarios_endocrino = models.CharField(max_length=200, blank=True, null=True)

        #EXPLORACIÓN DE CUELLO
    cuello_tiroides = models.CharField(max_length=100, blank=True, null=True)
    cuello_musculos = models.CharField(max_length=100, blank=True, null=True)
    cuello_ganglios_linfaticos = models.CharField(max_length=100, blank=True, null=True)

    #-##################################################################################################################################
    #################SIGUIENTE PAGINAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    #eXPLORACIÓN DE COLUMNA VERTEBRAL
    ecv_cervical_asc = models.TextField(max_length=100, blank=True, null=True)
    ecv_cervical_desc = models.TextField(max_length=100, blank=True, null=True)
    ecv_cervical_obs = models.TextField(blank=True, null=True)
    ecv_dorsal_asc = models.TextField(max_length=100, blank=True, null=True)
    ecv_dorsal_desc = models.TextField(max_length=100, blank=True, null=True)
    ecv_dorsal_obs = models.TextField(blank=True, null=True)
    ecv_lumbosacra_asc = models.TextField(max_length=100, blank=True, null=True)
    ecv_lumbosacra_desc = models.TextField(max_length=100, blank=True, null=True)
    ecv_lumbosacra_obs = models.TextField(blank=True, null=True)

    #Evalaución MMS
    mmss_hombros_cs_ad = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cs_ab = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cs_f = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cs_e = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cv_ad = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cv_ab = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cv_f = models.CharField(max_length=50, blank=True, null=True)
    mmss_hombros_cv_e = models.CharField(max_length=50, blank=True, null=True)

    art_codo_e = models.CharField(max_length=50, blank=True, null=True)
    art_codo_f = models.CharField(max_length=50, blank=True, null=True)
    art_muneca_e = models.CharField(max_length=50, blank=True, null=True)
    art_muneca_f = models.CharField(max_length=50, blank=True, null=True)
    art_muneca_p = models.CharField(max_length=50, blank=True, null=True)
    art_muneca_s = models.CharField(max_length=50, blank=True, null=True)
    # Evaluación Articular Pulgar
    art_pulgar_ab = models.CharField(max_length=50, blank=True, null=True)
    art_pulgar_ad = models.CharField(max_length=50, blank=True, null=True)
    art_pulgar_e = models.CharField(max_length=50, blank=True, null=True)
    art_pulgar_f = models.CharField(max_length=50, blank=True, null=True)
    # Evaluación Articular Dedos
    art_dedos_f = models.CharField(max_length=50, blank=True, null=True)
    art_dedos_e = models.CharField(max_length=50, blank=True, null=True)
    art_dedos_ifp = models.CharField(max_length=50, blank=True, null=True)












    
    # Evaluación articular de la cadera
    art_cadera_ab = models.CharField(max_length=50, blank=True, null=True)
    art_cadera_ad = models.CharField(max_length=50, blank=True, null=True)
    art_cadera_f = models.CharField(max_length=50, blank=True, null=True)
    art_cadera_e = models.CharField(max_length=50, blank=True, null=True)
    # Evaluación Articular del tobillo
    art_tobillo_f = models.CharField(max_length=50, blank=True, null=True)
    art_tobillo_e = models.CharField(max_length=50, blank=True, null=True)
    # Evaluación Articular MMII Subastragalina
    art_subastragalina_f = models.CharField(max_length=50, blank=True, null=True)
    art_subastragalina_ev = models.CharField(max_length=50, blank=True, null=True)
    # Exploración de la cavidad nasal
    nasal_mucosa = models.CharField(max_length=100, blank=True, null=True)
    nasal_cochas = models.CharField(max_length=100, blank=True, null=True)
    nasal_vascularizacion = models.CharField(max_length=100, blank=True, null=True)
    #############################################################################################
    ####SIGUIENTEEEEEEEEEEEEEEEEE PAGINAAAAAAAAAAAAAAAAAAAAAAAA
    # Exploración Cardiovascular (Ascitis)

    me_pulso_carotideo_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Carotídeo Derecho")
    me_pulso_carotideo_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Carotídeo Izquierdo")

    # Pulso Humeral
    me_pulso_humeral_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Humeral Derecho")
    me_pulso_humeral_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Humeral Izquierdo")

    # Pulso Radial
    me_pulso_radial_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Radial Derecho")
    me_pulso_radial_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Radial Izquierdo")

    # Pulso Femoral
    me_pulso_femoral_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Femoral Derecho")
    me_pulso_femoral_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Femoral Izquierdo")

    # Pulso Poplíteo
    me_pulso_popliteo_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Poplíteo Derecho")
    me_pulso_popliteo_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Poplíteo Izquierdo")

    # Pulso Tibial Posterior
    me_pulso_tibial_posterior_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Tibial Posterior Derecho")
    me_pulso_tibial_posterior_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Tibial Posterior Izquierdo")

    # Pulso Pedio
    me_pulso_pedio_derecho = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Pedio Derecho")
    me_pulso_pedio_izquierdo = models.CharField(max_length=50,blank=True,null=True,verbose_name="Pulso Pedio Izquierdo")

    ascitis = models.BooleanField(default=False)

    Estado_Conciencia = models.TextField(blank=True, null = True)
    
    ##ESCALA DE GLASLOW

    glasgow_apertura_ojos_respuesta = models.CharField(max_length=100, blank=True, null=True)
    glasgow_apertura_ojos_puntuacion = models.IntegerField(blank=True, null=True)
    glasgow_respuesta_verbal_respuesta = models.CharField(max_length=100, blank=True, null=True)
    glasgow_respuesta_verbal_puntuacion = models.IntegerField(blank=True, null=True)
    glasgow_respuesta_motora_respuesta = models.CharField(max_length=100, blank=True, null=True)
    glasgow_respuesta_motora_puntuacion = models.IntegerField(blank=True, null=True)

    ##reflejo fotomotor
    
    reflejo_fotomotor_tamano = models.CharField(max_length=100, blank=True, null=True)
    reflejo_fotomotor_relaciones = models.CharField(max_length=100, blank=True, null=True)
    reflejo_fotomotor_respuestas_luz = models.CharField(max_length=100, blank=True, null=True)

    # Exploración Partes Craneales
    par_craneal_iii_oculomotor = models.CharField(max_length=100, blank=True, null=True)
    par_craneal_iv_patetico = models.CharField(max_length=100, blank=True, null=True)
    par_craneal_vi_motor_ocular_externo = models.CharField(max_length=100, blank=True, null=True)
        # campos visuales
    par_craneal_iii_oculomotor_cv = models.CharField(max_length=100, blank=True, null=True)
    par_craneal_iv_patetico_cv = models.CharField(max_length=100, blank=True, null=True)
    par_craneal_vi_motor_ocular_externo_cv = models.CharField(max_length=100, blank=True, null=True)
    # Campos Visuales y Retina
    retina_relacion_arterio_venosa = models.CharField(max_length=100, blank=True, null=True)
    retina_macula = models.CharField(max_length=100, blank=True, null=True)
    CAMPOS_VISUALES_CHOICES = [
        ('-----', '-----'),
        ('Extravasaciones','Extravasaciones'),
        ('Vasos Tortuosos','Vasos Tortuosos'),
        ('Catarata','Catarata'),
        ('Exudado Cotonoso','Exudado Cotonoso'),
        ('No aplica','No aplica'),

    ]
    campos_visuales_opciones = ArrayField(models.CharField(max_length=50, choices=CAMPOS_VISUALES_CHOICES, blank = True, null = True, default=get_default_servicios))

    ###############################################################################
    # Siguente pagina
    # 
    Conducta_auditiva = models.CharField(max_length=50, blank=True, null=True)
    Membrana_timpatica = models.CharField(max_length=50, blank=True, null=True)
    conduccion_osea = models.CharField(max_length=50, blank=True, null=True)
    conduccion_area = models.CharField(max_length=50, blank=True, null=True)

    CHOICES_NUMERICAS = [ 
        ('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4')
    ]
        # REFLEJOS OSTEO TENDINOSOS PROFUNDOS:
    Naso_palpebral = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Superciliar = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Maseterino = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Bicipital = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Estilo_Radial = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Tricipital = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Cubito_Pronador = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Medio_Pubiano = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Rotuliano = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))

    # REFLEJOS SUPERFICIALES O MUCOCUTANEOS:
    Corneo_Palpebral = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Conjuntivo_Palpebral = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Palatino_o_Velo_Palatino = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Faringeo = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Tusigeno = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Vomito = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Respiratorio = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Miccional = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Defecatorio = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Aquileo = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))

    # REFLEJO (del tercer bloque, sin categoría específica visible en la imagen):
    Babinski = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Chaddock = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Oppenheim = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Gordon = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Kerning = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))
    Brudzinski = ArrayField(models.CharField(max_length=10, blank=True, null=True, choices=CHOICES_NUMERICAS))








class Receta(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    medico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    diagnostico = models.TextField()
    medicamento = models.TextField()
    indicaciones = models.TextField()
    
    # Campos existentes para la receta
    edad = models.IntegerField(null=True, blank=True)
    talla = models.FloatField(null=True, blank=True)
    peso = models.FloatField(null=True, blank=True)
    
    # --- NUEVOS CAMPOS AÑADIDOS ---
    ta = models.CharField(max_length=20, verbose_name='T/A', null=True, blank=True) # Tensión Arterial
    fc = models.IntegerField(verbose_name='F.C.', null=True, blank=True) # Frecuencia Cardiaca
    sat_o2 = models.IntegerField(verbose_name='SAT. O2', null=True, blank=True) # Saturación de Oxígeno
    
    def __str__(self):
        return f'Receta de {self.paciente.nombre} - {self.fecha}'
    
    
    
    
    
    
    
    
class HistoriaClinicaMusculoEsqueletico(models.Model):
    id = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='PacienteHistoriaClinicaME')
    fecha_registro = models.DateField(auto_now_add=True, verbose_name="Fecha de Registro")
    comentarios = models.TextField(blank=True, null=True, verbose_name="ComentariosAdicionales")
    GradoInstruccion = models.CharField(max_length=255, blank=True, null=True)
    inmunizaciones_o_vacunas = models.TextField(blank=True, null=True)
    #Habitos higienicos
    baño_diario = models.CharField(max_length=100, blank=True, null=True)
    aseo_dental = models.CharField(max_length=100, blank=True, null=True)
    lavado_manos_antes_comer = models.CharField(max_length=100, blank=True, null=True)
    lavado_manos_despues = models.CharField(max_length=100, blank=True, null=True)
    CHOICES_TAMANIO_VIVIENDA_CUARTOS = [
        ('-----', '-----'),
    ('1_cuarto', '1 Cuarto'),
    ('2_cuartos', '2 Cuartos'),
    ('3_cuartos', '3 Cuartos'),
    ('4_cuartos', '4 Cuartos'),
    ('5_o_mas_cuartos', '5 o más Cuartos'),
    ]

    tamanio_vivienda = models.CharField(max_length=100, blank=True, null=True, choices=CHOICES_TAMANIO_VIVIENDA_CUARTOS, default = get_default_servicios)
    CHOICES_TIPO_VIVIENDA = [
    ('Casa independiente (particular)', 'Casa independiente (particular)'),
    ('Departamento en edificio o condominio', 'Departamento en edificio o condominio'),
    ('Vivienda en vecindad', 'Vivienda en vecindad'),
    ('Cuarto en vivienda compartida', 'Cuarto en vivienda compartida'),
    ('Vivienda en local no construido para habitación', 'Vivienda en local no construido para habitación'), # Ej. locales comerciales adaptados
    ('Vivienda móvil (casa rodante, barco, etc.)', 'Vivienda móvil (casa rodante, barco, etc.)'),
    ('Refugio (albergue, casa hogar, etc.)', 'Refugio (albergue, casa hogar, etc.)'),
    ('otro', 'Otro tipo de vivienda')
    ]

    tipo_vivienda = models.CharField(max_length=100, blank=True, null=True, choices=CHOICES_TIPO_VIVIENDA, default=get_default_servicios)

    SERVICIOS_VIVIENDA_CHOICES = [
         ('-----', '-----'),
    ('agua', 'Agua Potable'),
    ('luz', 'Electricidad'),
    ('gas', 'Gas Natural'),
    ('internet', 'Internet'),
    ('telefonia', 'Telefonía Fija'),
    ('alcantarillado', 'Alcantarillado'),
    ('recoleccion_basura', 'Recolección de Basura'),
    # ¡Aquí es donde pones las opciones!
                                    ]
    servicio_vivienda = ArrayField(
        models.CharField(max_length=50, choices=SERVICIOS_VIVIENDA_CHOICES),
        null=True,
        blank=True,
        verbose_name="Servicios con los que cuenta la vivienda"
        )
    Personas_que_habitan = models.CharField(max_length=100, blank=True, null=True, verbose_name='Personas que habitan en la vivienda')
    Parentesco = models.CharField(max_length=100, blank=True, null=True, verbose_name='Parentesco')
    ANTECENDENTES_FAMILIARES_CHOICES = [
        ('-----', '-----'),
    ('Tuberculosis', 'Tuberculosis'),
    ('Diabetes', 'Diabetes'),
    ('Hipertensión', 'Hipertensión'),
    ('Obesidad', 'Obesidad'),
    ('Malformaciones', 'Malformaciones Congenitas'),
    ('Cáncer', 'Cáncer'),
    ('Alergias', 'Alergias'),
    ('Cardiacas','Enfermedades Cardiacas'),
    ('Psiquiátricas','Enfermdedades Psiquiátricas'),
    ('Reumaticas','Enfermedades Reumaticas'),
    ('Tumores','Tumores'),
    ('Luéticos','Luéticos'),
    ('Otros', 'otros')]
    motivo_consulta = models.TextField()
    enfermedad_actual = models.CharField(max_length=50, blank=True, null=True)
        #ANTECEDENTES FAMILIARES
    Antecedentes_familiares = ArrayField(models.CharField(max_length=50, 
                                                        choices=ANTECENDENTES_FAMILIARES_CHOICES,
                                                        blank=True,
                                                        verbose_name='Antecendentes Familiares', default=get_default_servicios, null=True))
        #ANTECEDENTES PERSONALES

        #Habitos tóxicos
    HABITOS_TOXICOS_CHOICES = [
        ('-----', '-----'),
            ('Alcohol','Alcohol'),
            ('Tabaquismo', 'Tabaquismo'),
            ('Drogas','Drogas'),
            ('Infusiones','Infusiones'),
            ('No aplica','No aplica'),
            
        ]
    habitos_toxicos = ArrayField(models.CharField(max_length=50, choices=HABITOS_TOXICOS_CHOICES, blank=True,null=True, default=get_default_servicios, verbose_name='Hábitos tóxicos'))
        #Hábitos fisiologicos
    ALIMENTACION_CHOICES = [
        ('-----', '-----'),
            ('Carnivora', 'Carnivora'),
            ('vegetariana', 'Vegetariana'),
            ('vegana', 'Vegana (no productos animales)'),
            ('pescetariana', 'Pescetariana (no carne, sí pescado)'),
            ('flexitariana', 'Flexitariana (principalmente vegetariana, poca carne)'),
            ('keto', 'Cetogénica (Keto)'),
            ('paleo', 'Paleo'),
            ('otra', 'Otra (especifique)'), # Opción para describir si no está en la lista
            ('no_aplica', 'No aplica / No sabe / No responde'), # Para casos donde no se puede clasificar
            ]

    Allimentación = ArrayField(models.CharField(max_length=50, choices=ALIMENTACION_CHOICES, blank=True, null=True, default=get_default_servicios))
    Ingesta_Agua = models.IntegerField(blank=True, null=True, verbose_name='Ingesta de agua litros')
    Cantidad_veces_Orina = models.IntegerField(blank=True, null=True, verbose_name='Cantidad de veces de orina')
    Catarsis = models.CharField(max_length=50, null=True, blank=True)
    Somnia = models.CharField(max_length=50, null=True, blank=True)

        #Patologicosss
    PATOLOGIAS_CHOICES = [
        ('-----', '-----'),
            ('Herpes','Herpes'),
            ('Hepatitis','Hepatitis'),
            ('HTA','HTA'),
            ('Alergias','Alergias'),
            ('Diabetes','Diabetes'),
            ('Tifoidea','Tifoidea'),
            ('TBC','TBC'),
            ('Caries','Caries'),
            ('Rubeola','Rubeola'),
            ('Neoplasis','Neoplasis'),
            ('Otros','Otros'),    
        ]
    Infancia = models.TextField(max_length=100, blank=True, null=True)
    Adulto = models.TextField(max_length=100, blank=True, null=True)
    Patologias = ArrayField(models.CharField(max_length=50, choices=PATOLOGIAS_CHOICES,blank=True, null=True, default=get_default_servicios))

    ha_sido_operado = models.BooleanField(default=False)
    fecha_operacion = models.DateField(blank=True, null=True)
    traumatismo_o_fractura = models.BooleanField(blank=True, null=True)
    Otro = models.TextField(blank=True, null=True)
    #EXAMEN FISICO
    #inspeccion general
    Constitucional = models.CharField(max_length=100, blank=True, null=True, verbose_name='Constitucional')
    Marcha = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marcha')
    Actitud = models.CharField(max_length=100, blank=True, null=True, verbose_name='Actitud')
    Ubicacion = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ubicación')
    Impresion_general = models.CharField(max_length=100, blank=True, null=True, verbose_name='Impresión General')
    #Signos Vitales
    FC = models.CharField(max_length=100, blank=True, null=True, verbose_name='Frecuencia Cardiaca')
    TA = models.CharField(max_length=100, blank=True, null=True, verbose_name='Tensión Arterial')
    FR = models.CharField(max_length=100, blank=True, null=True, verbose_name='Frecuencia Respiratoria')
    T_Auxiliar = models.CharField(max_length=100, blank=True, null=True, verbose_name='Temperatura Auxiliar')
    T_rectal = models.CharField(max_length=100, blank=True, null=True, verbose_name='Temperatura Rectal')
    Peso_Habitual = models.CharField(max_length=100, blank=True, null=True, verbose_name='Peso Habitual')
    Peso_Actual = models.CharField(max_length=100, blank=True, null=True, verbose_name='Peso Actual')
    Talla = models.CharField(max_length=100, blank=True, null=True, verbose_name='Talla')
    IMC = models.CharField(max_length=100, blank=True, null=True, verbose_name='Índice de Masa Corporal')
    #Piel, Faneras y Tejido celular subcutaneo
    Aspecto = models.CharField(max_length=100, blank=True, null=True, verbose_name='Aspecto')
    Distribuición_pilosa = models.CharField(max_length=100, blank=True, null=True, verbose_name='Distribución pilosa')
    Lesiones = models.CharField(max_length=100, blank=True, null=True, verbose_name='Lesiones')
    Faneras = models.CharField(max_length=100, blank=True, null=True, verbose_name='Faneras')
    Tejido_celular_subcutaneo = models.CharField(max_length=100, blank=True, null=True, verbose_name='Tejido celular subcutáneo')
    PROBLEMAS_PIEL = [
        ('-----', '-----'),
        ('lipomas', 'Lipomas'),
        ('Papada', 'Papada'),
        ('Paniculo Adiposo', 'Paniculo Adiposo'),
        ('Otros', 'Otros'),
        ('No aplica', 'No aplica'),
    ]
    Tejido_celular = ArrayField(models.CharField(max_length=100, blank=True, null=True, choices=PROBLEMAS_PIEL, verbose_name='Tejido celular', default =get_default_servicios ))