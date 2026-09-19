# InventarioInsumos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Insumo
from .forms import InsumoForm
from Pacientes.alcance import doctor_del_usuario


def _insumos_consultorio(request):
    doctor = doctor_del_usuario(request.user)
    if not doctor:
        return Insumo.objects.none()
    return Insumo.objects.filter(doctor=doctor)


@login_required
def lista_insumos(request):
    # Esta vista es accesible para ambos, no necesita cambios de permisos.
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    insumos = _insumos_consultorio(request).order_by('nombre')
    context = {
        'insumos': insumos,
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'lista_insumos.html', context)

@login_required
def crear_insumo(request):
    # --- INICIO: Validación de Permisos ---
    # Solo los usuarios del grupo 'Doctora' pueden crear insumos.
    if not request.user.groups.filter(name='Doctora').exists():
        messages.error(request, 'No tienes permiso para crear insumos.')
        return redirect('lista_insumos')
    # --- FIN: Validación de Permisos ---

    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save(commit=False)
            insumo.doctor = doctor_del_usuario(request.user)
            insumo.save()
            form.save_m2m()
            messages.success(request, 'Insumo añadido al inventario exitosamente.')
            return redirect('lista_insumos')
    else:
        form = InsumoForm()

    # Ya no necesitamos pasar 'is_farmacia' o 'is_doctora' porque esta vista
    # ahora solo es accesible para la doctora.
    context = {
        'form': form,
        'titulo': 'Añadir Nuevo Insumo',
    }
    return render(request, 'insumo_form.html', context)

@login_required
def editar_insumo(request, pk):
    # --- INICIO: Validación de Permisos ---
    # Solo los usuarios del grupo 'Doctora' pueden editar insumos.
    if not request.user.groups.filter(name='Doctora').exists():
        messages.error(request, 'No tienes permiso para editar insumos.')
        return redirect('lista_insumos')
    # --- FIN: Validación de Permisos ---

    insumo = get_object_or_404(_insumos_consultorio(request), pk=pk)
    if request.method == 'POST':
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insumo actualizado exitosamente.')
            return redirect('lista_insumos')
    else:
        form = InsumoForm(instance=insumo)

    context = {
        'form': form,
        'insumo': insumo,
        'titulo': 'Editar Insumo',
    }
    return render(request, 'insumo_form.html', context)

@login_required
def eliminar_insumo(request, pk):
    # --- INICIO: Validación de Permisos ---
    # Solo los usuarios del grupo 'Doctora' pueden eliminar insumos.
    if not request.user.groups.filter(name='Doctora').exists():
        messages.error(request, 'No tienes permiso para eliminar insumos.')
        return redirect('lista_insumos')
    # --- FIN: Validación de Permisos ---

    insumo = get_object_or_404(_insumos_consultorio(request), pk=pk)
    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo eliminado del inventario.')
        return redirect('lista_insumos')

    context = {
        'insumo': insumo,
    }
    return render(request, 'confirmar_eliminar_insumo.html', context)











# InventarioInsumos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Insumo
from .forms import InsumoForm

# --- AÑADE ESTAS LÍNEAS ---
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_POST
# -------------------------

    # --- NUEVA VISTA PARA AJAX ---

# InventarioInsumos/views.py

@login_required
@require_POST
@transaction.atomic
def modificar_cantidad_insumo(request, pk):

    # --- LÓGICA DE PERMISO ACTUALIZADA ---
    # Comprobamos si es Doctora O Farmacia
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()

    if not (is_doctora or is_farmacia):
        return JsonResponse({'error': 'No tienes permiso para esta acción.'}, status=403)
    # --- FIN DE LA ACTUALIZACIÓN ---

    try:
        # 2. Obtener el insumo y la acción (desde el JavaScript)
        insumo = get_object_or_404(_insumos_consultorio(request), pk=pk)
        action = request.POST.get('action') # 'aumentar' o 'disminuir'

        # 3. Ejecutar la lógica
        if action == 'aumentar':
            insumo.cantidad_disponible += 1

        elif action == 'disminuir':
            if insumo.cantidad_disponible > 0:
                insumo.cantidad_disponible -= 1
            else:
                return JsonResponse({
                    'status': 'info',
                    'message': 'La cantidad ya es 0.',
                    'nueva_cantidad': 0
                })
        else:
            return JsonResponse({'error': 'Acción no válida.'}, status=400)

        # 4. Guardar y responder
        insumo.save()

        return JsonResponse({
            'success': True,
            'nueva_cantidad': insumo.cantidad_disponible
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)