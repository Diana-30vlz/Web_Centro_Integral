
def user_roles_processor(request):
    """
    Este procesador de contexto añade los roles del usuario (is_doctora, is_farmacia)
    a todas las plantillas, siempre y cuando el usuario esté autenticado.
    """
    context = {
        'is_doctora': False,
        'is_farmacia': False,
        'cit_sesion_anim': '',
        'cit_sesion_nombre': '',
    }

    if hasattr(request, 'session'):
        context['cit_sesion_anim'] = request.session.pop('cit_sesion_anim', '')
        context['cit_sesion_nombre'] = request.session.pop('cit_sesion_nombre', '')

    # Solo calculamos los roles si el usuario ha iniciado sesión
    if request.user.is_authenticated:
        context['is_doctora'] = request.user.groups.filter(name='Doctora').exists()
        context['is_farmacia'] = request.user.groups.filter(name='Farmacia').exists()
            
    return context