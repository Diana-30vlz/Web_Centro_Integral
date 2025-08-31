from django.contrib import admin
from .models import Paciente, Cita, Receta # Importa Paciente y Cita
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, FarmaciaProfile
# Register your models here.
from django.contrib.auth.models import User as AuthUser # Importa el modelo de usuario por defecto




# Desregistra el modelo de usuario por defecto
try:
    admin.site.unregister(AuthUser)
except admin.sites.NotRegistered:
    pass

# Usa el decorador para registrar CustomUser
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active'
    )
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email', 'user_type', 'recovery_nip')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

# Para DoctorProfile
'''@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    # CORRECCIÓN: Accede a first_name y last_name a través de 'user'
    list_display = ('id', 'user', 'user_id', 'get_user_first_name', 'get_user_last_name',)
    readonly_fields = ('id', 'user',) # Los IDs no se editan
    # Si tienes campos específicos en DoctorProfile, añádelos aquí:
    # list_display = ('id', 'user', 'user_id', 'get_user_first_name', 'get_user_last_name', 'cedula_profesional', 'especialidad',)


    # Métodos para obtener los campos de CustomUser
    @admin.display(description='Nombre(s) del Usuario')
    def get_user_first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='Apellidos del Usuario')
    def get_user_last_name(self, obj):
        return obj.user.last_name'''

# Para FarmaciaProfile
@admin.register(FarmaciaProfile)
class FarmaciaProfileAdmin(admin.ModelAdmin):
    # CORRECCIÓN: Accede a first_name y last_name a través de 'user'
    list_display = ('id', 'user', 'user_id', 'get_user_first_name', 'get_user_last_name',)
    readonly_fields = ('id', 'user',) # Los IDs no se editan
    # Si tienes campos específicos en FarmaciaProfile, añádelos aquí:
    # list_display = ('id', 'user', 'user_id', 'get_user_first_name', 'get_user_last_name', 'nombre_farmacia', 'rfc',)

    # Métodos para obtener los campos de CustomUser
    @admin.display(description='Nombre(s) del Usuario')
    def get_user_first_name(self, obj):
        return obj.user.first_name

    @admin.display(description='Apellidos del Usuario')
    def get_user_last_name(self, obj):
        return obj.user.last_name


admin.site.register(Paciente) # Asegúrate de que Paciente ya esté registrado
admin.site.register(Cita) # Registra tu nuevo modelo Cita


class RecetaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha', 'diagnostico')
    list_filter = ('fecha', 'medico')
    search_fields = ('paciente__nombre', 'paciente__apellido_paterno', 'diagnostico')

# Registra el modelo
admin.site.register(Receta, RecetaAdmin)