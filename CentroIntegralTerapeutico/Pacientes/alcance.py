from Pacientes.models import Doctor, FarmaciaProfile, Paciente


def perfil_farmacia(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return FarmaciaProfile.objects.filter(user=user).select_related('doctor').first()


def farmacia_aceptada(user):
    perfil = perfil_farmacia(user)
    return bool(perfil and perfil.aceptada)


def doctor_del_usuario(user):
    """Doctor del consultorio: el propio perfil o el doctor ligado a la farmacia aceptada."""
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    doctor = Doctor.objects.filter(user=user).first()
    if doctor:
        return doctor
    farmacia = perfil_farmacia(user)
    if farmacia and farmacia.aceptada:
        return farmacia.doctor
    return None


def ids_usuarios_consultorio(doctor):
    if not doctor:
        return []
    ids = [doctor.user_id]
    ids.extend(list(doctor.farmacias.filter(aceptada=True).values_list('user_id', flat=True)))
    return ids


def pacientes_del_consultorio(user):
    doctor = doctor_del_usuario(user)
    if not doctor:
        return Paciente.objects.none()
    return Paciente.objects.filter(doctor_responsable=doctor)
