# InventarioInsumos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Insumo
from .forms import InsumoForm

@login_required
def lista_insumos(request):
    # Esta vista es accesible para ambos, no necesita cambios de permisos.
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    insumos = Insumo.objects.all().order_by('nombre')
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
            form.save()
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

    insumo = get_object_or_404(Insumo, pk=pk)
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
    
    insumo = get_object_or_404(Insumo, pk=pk)
    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo eliminado del inventario.')
        return redirect('lista_insumos')
    
    context = {
        'insumo': insumo,
    }
    return render(request, 'confirmar_eliminar_insumo.html', context)