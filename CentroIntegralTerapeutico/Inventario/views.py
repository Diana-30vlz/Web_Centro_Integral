# Inventario/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import * # <-- Ahora importa desde el mismo directorio
from .forms import MedicamentoForm, Tag # <-- Ahora importa desde el mismo directorio
import io
from django.http import HttpResponse

# Importaciones para ReportLab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, mm
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, red # Para colores de texto o error
from reportlab.graphics.barcode import createBarcodeDrawing # <--- Importación corregida y clave

from .models import Medicamento, Tag
from .forms import SeleccionarMedicamentosForm, MedicamentoForm # Importa el nuevo formulario

from django.contrib import messages
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Medicamento, Venta, ItemVenta, Tag
from datetime import datetime


# ... (asegúrate de que los imports necesarios estén arriba) ...

@login_required
def lista_medicamentos(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    medicamentos = Medicamento.objects.all().order_by('nombre')
    context = {
        'medicamentos': medicamentos,
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    return render(request, 'inventario/lista_medicamentos.html', context)

@login_required
def crear_medicamento(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicamento añadido al inventario exitosamente.')
            return redirect('lista_medicamentos')
    else:
        form = MedicamentoForm()
    
    context = {
        'form': form,
        'titulo': 'Añadir Nuevo Medicamento',
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    return render(request, 'inventario/medicamento_form.html', context)

@login_required
def editar_medicamento(request, pk):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    medicamento = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        form = MedicamentoForm(request.POST, instance=medicamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicamento actualizado exitosamente.')
            return redirect('lista_medicamentos')
    else:
        form = MedicamentoForm(instance=medicamento)
    
    context = {
        'form': form,
        'medicamento': medicamento,
        'titulo': 'Editar Medicamento',
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    return render(request, 'inventario/medicamento_form.html', context)

@login_required
def eliminar_medicamento(request, pk):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    medicamento = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        medicamento.delete()
        messages.success(request, 'Medicamento eliminado del inventario.')
        return redirect('lista_medicamentos')
    
    context = {
        'medicamento': medicamento,
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    return render(request, 'inventario/confirmar_eliminar_medicamento.html', context)




# --- DEFINICIONES GLOBALES DE DIMENSIONES Y CÁLCULOS DE CUADRÍCULA ---
ETIQUETA_ANCHO = 70 * mm
ETIQUETA_ALTO = 40 * mm
TAMANO_ETIQUETA = (ETIQUETA_ANCHO, ETIQUETA_ALTO)

HOJA_ANCHO, HOJA_ALTO = letter
MARGEN_HORIZONTAL_HOJA = 10 * mm
MARGEN_VERTICAL_HOJA = 10 * mm

ESPACIO_ENTRE_ETIQUETA_X = 3 * mm
ESPACIO_ENTRE_ETIQUETA_Y = 3 * mm

ETIQUETAS_POR_FILA = int((HOJA_ANCHO - 2 * MARGEN_HORIZONTAL_HOJA + ESPACIO_ENTRE_ETIQUETA_X) / (ETIQUETA_ANCHO + ESPACIO_ENTRE_ETIQUETA_X))
ETIQUETAS_POR_COLUMNA = int((HOJA_ALTO - 2 * MARGEN_VERTICAL_HOJA + ESPACIO_ENTRE_ETIQUETA_Y) / (ETIQUETA_ALTO + ESPACIO_ENTRE_ETIQUETA_Y))
ETIQUETAS_POR_PAGINA = ETIQUETAS_POR_FILA * ETIQUETAS_POR_COLUMNA

print(f"Cabrán {ETIQUETAS_POR_FILA} etiquetas por fila y {ETIQUETAS_POR_COLUMNA} por columna.")
print(f"Total de {ETIQUETAS_POR_PAGINA} etiquetas por página.")


# --- FUNCIÓN AUXILIAR PARA DIBUJAR EL CONTENIDO DE UNA SOLA ETIQUETA ---
def dibujar_una_etiqueta(p, medicamento, x_offset, y_offset):
    # 'p' es el objeto canvas
    # 'medicamento' es la instancia del objeto Medicamento
    # 'x_offset', 'y_offset' son las coordenadas de la esquina inferior izquierda de ESTA etiqueta en la página

    # Ajusta las posiciones internas de la etiqueta relativa al offset
    margen_izquierdo_interno = x_offset + 5 * mm
    margen_superior_interno = y_offset + ETIQUETA_ALTO - 5 * mm
    current_y = margen_superior_interno
    
    # --- CÁLCULO DE POSICIONES PARA EL CÓDIGO DE BARRAS Y EL ID (CORREGIDO) ---
    barcode_desired_height = 10 * mm
    id_text_desired_height = 3 * mm
    gap_between_barcode_and_id = 1 * mm
    bottom_padding = 2 * mm

    id_text_y_abs = y_offset + bottom_padding
    barcode_y_abs = id_text_y_abs + id_text_desired_height + gap_between_barcode_and_id

    limite_superior_para_texto_en_etiqueta = barcode_y_abs + barcode_desired_height + 2 * mm

    # 1. Nombre del Medicamento
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margen_izquierdo_interno, current_y, medicamento.nombre)
    current_y -= 6 * mm

    # 2. Cantidad y Unidad
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margen_izquierdo_interno, current_y, f"Cant: {medicamento.cantidad_disponible} {medicamento.unidad_medida}")
    current_y -= 5 * mm

    # 3. Fecha de Caducidad (si existe)
    if medicamento.fecha_caducidad:
        p.setFont("Helvetica", 8)
        caducidad_str = medicamento.fecha_caducidad.strftime("%d/%m/%Y")
        p.drawString(margen_izquierdo_interno, current_y, f"Cad: {caducidad_str}")
        current_y -= 4 * mm

    # 4. Etiquetas (Tags)
    tags_list = [tag.nombre for tag in medicamento.tags.all()]
    if tags_list:
        p.setFont("Helvetica-Oblique", 7)
        tags_str = ", ".join(tags_list)

        potential_tag_y = current_y - 3 * mm

        if potential_tag_y < limite_superior_para_texto_en_etiqueta:
            display_tag_y = limite_superior_para_texto_en_etiqueta + 1 * mm
            p.drawString(margen_izquierdo_interno, display_tag_y, f"Etiquetas: {tags_str}")
        else:
            p.drawString(margen_izquierdo_interno, potential_tag_y, f"Etiquetas: {tags_str}")
            current_y -= 8 * mm

    # --- Generación del Código de Barras EAN-13 ---
    ean13_data = str(medicamento.pk).zfill(12)
    barcode_x_abs = x_offset + 5 * mm
    # Ya no es necesario reasignar barcode_y_abs, ya se calculó arriba.
    
    id_text_x_abs_center = x_offset + (ETIQUETA_ANCHO / 2)
    # Ya no es necesario reasignar id_text_y_abs, ya se calculó arriba.

    if len(ean13_data) == 12:
        try:
            barcode = createBarcodeDrawing(
                'EAN13',
                value=ean13_data,
                barHeight=barcode_desired_height,
                barWidth=0.3 * mm,
            )
            barcode.drawOn(p, barcode_x_abs, barcode_y_abs)
        except Exception as e:
            p.setFont("Helvetica-Bold", 8)
            p.setFillColor(red)
            p.drawString(barcode_x_abs, barcode_y_abs + (barcode_desired_height / 2), f"Error Code: {e}")
            p.setFillColor(black)
    else:
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(red)
        p.drawString(barcode_x_abs, barcode_y_abs + (barcode_desired_height / 2), "Error: ID demasiado largo para EAN-13")
        p.setFillColor(black)

    # --- Texto del ID debajo del Código de Barras ---
    p.setFont("Helvetica", 6)
    p.drawCentredString(id_text_x_abs_center, id_text_y_abs, f"ID: {medicamento.pk}")


# --- VISTAS EXISTENTES (sin cambios) ---
@login_required
def lista_medicamentos(request):
    medicamentos = Medicamento.objects.all().order_by('nombre')
    context = {
        'medicamentos': medicamentos
    }
    return render(request, 'inventario/lista_medicamentos.html', context)

@login_required
def crear_medicamento(request):
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicamento añadido al inventario exitosamente.')
            return redirect('lista_medicamentos')
    else:
        form = MedicamentoForm()
    
    context = {
        'form': form,
        'titulo': 'Añadir Nuevo Medicamento'
    }
    return render(request, 'inventario/medicamento_form.html', context)

@login_required
def editar_medicamento(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        form = MedicamentoForm(request.POST, instance=medicamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicamento actualizado exitosamente.')
            return redirect('lista_medicamentos')
    else:
        form = MedicamentoForm(instance=medicamento)
    
    context = {
        'form': form,
        'medicamento': medicamento,
        'titulo': 'Editar Medicamento'
    }
    return render(request, 'inventario/medicamento_form.html', context)

@login_required
def eliminar_medicamento(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        medicamento.delete()
        messages.success(request, 'Medicamento eliminado del inventario.')
        return redirect('lista_medicamentos')
    
    context = {
        'medicamento': medicamento
    }
    return render(request, 'inventario/confirmar_eliminar_medicamento.html', context)

@login_required
def imprimir_etiqueta_medicamento(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=TAMANO_ETIQUETA)
    dibujar_una_etiqueta(p, medicamento, 0, 0)
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="etiqueta_EAN13_{medicamento.nombre.replace(" ", "_")}.pdf"'
    return response


# --- VISTA PARA MOSTRAR EL FORMULARIO DE SELECCIÓN DE MEDICAMENTOS ---
@login_required
def seleccionar_medicamentos_para_imprimir(request):
    # Este formulario solo se usa para obtener la lista de medicamentos para la plantilla
    form = SeleccionarMedicamentosForm() #
    return render(request, 'inventario/seleccionar_medicamentos.html', {'form': form}) #


# --- VISTA PRINCIPAL PARA IMPRIMIR MÚLTIPLES ETIQUETAS EN UNA HOJA (MODIFICADA) ---
@login_required
def imprimir_varias_etiquetas_pdf(request, selected_ids_str):
    # selected_ids_str ahora viene en formato "ID:CANTIDAD,ID:CANTIDAD,..."
    
    # Diccionario para almacenar {medicamento_id: cantidad_a_imprimir}
    medicamentos_con_cantidades = {}
    
    if selected_ids_str and selected_ids_str != '0': # '0' es el placeholder inicial
        for item in selected_ids_str.split(','):
            try:
                med_id, quantity = item.split(':')
                medicamentos_con_cantidades[int(med_id)] = int(quantity)
            except ValueError:
                # Manejar errores si el formato no es el esperado
                messages.error(request, "Error en el formato de selección de medicamentos.")
                return redirect('seleccionar_medicamentos_para_imprimir')

    if not medicamentos_con_cantidades:
        messages.warning(request, "No se seleccionaron medicamentos para imprimir o hubo un error.")
        return redirect('seleccionar_medicamentos_para_imprimir')

    # Obtener los objetos Medicamento de la base de datos
    # Solo necesitamos los IDs, luego iteraremos según las cantidades
    medicamento_ids = list(medicamentos_con_cantidades.keys())
    medicamentos_dict = {med.pk: med for med in Medicamento.objects.filter(pk__in=medicamento_ids)}

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(HOJA_ANCHO, HOJA_ALTO))

    etiquetas_en_pagina_actual = 0
    col = 0
    row = 0

    # Iterar sobre los medicamentos y sus cantidades para dibujar
    for med_id, cantidad_a_imprimir in medicamentos_con_cantidades.items():
        medicamento = medicamentos_dict.get(med_id)
        if not medicamento:
            # Si por alguna razón el medicamento no se encuentra, saltarlo
            continue

        for _ in range(cantidad_a_imprimir): # Repetir el dibujo 'cantidad_a_imprimir' veces
            x_offset = MARGEN_HORIZONTAL_HOJA + col * (ETIQUETA_ANCHO + ESPACIO_ENTRE_ETIQUETA_X)
            y_offset = HOJA_ALTO - MARGEN_VERTICAL_HOJA - (row + 1) * (ETIQUETA_ALTO + ESPACIO_ENTRE_ETIQUETA_Y) + ESPACIO_ENTRE_ETIQUETA_Y

            dibujar_una_etiqueta(p, medicamento, x_offset, y_offset)
            etiquetas_en_pagina_actual += 1

            col += 1
            if col >= ETIQUETAS_POR_FILA:
                col = 0
                row += 1

            if row >= ETIQUETAS_POR_COLUMNA:
                p.showPage()
                col = 0
                row = 0
                etiquetas_en_pagina_actual = 0 # Resetear contador de etiquetas en la nueva página

    # Asegurarse de guardar la última página si no se llenó por completo
    if etiquetas_en_pagina_actual > 0:
        p.showPage()
    
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="etiquetas_medicamentos.pdf"'
    return response







# --- Vistas para el Punto de Venta ---
# --- Vistas para el Punto de Venta ---
@login_required
def punto_venta(request):
    """
    Vista principal para el punto de venta.
    Muestra todos los medicamentos y la venta actual en sesión.
    """
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    if not is_farmacia:
        messages.warning(request, "No tienes permiso para acceder al punto de venta.")
        return redirect('HomeSinInicio')
    
    venta_actual_id = request.session.get('venta_actual_id')
    venta_actual = None
    if venta_actual_id:
        try:
            venta_actual = Venta.objects.get(pk=venta_actual_id, estado='pendiente', farmaceuta=request.user)
        except Venta.DoesNotExist:
            venta_actual = None
            request.session.pop('venta_actual_id', None)

    if not venta_actual:
        venta_actual = Venta.objects.create(farmaceuta=request.user, estado='pendiente')
        request.session['venta_actual_id'] = venta_actual.pk
    
    context = {
        'medicamentos': Medicamento.objects.all().order_by('nombre'),
        'venta_actual': venta_actual,
        'items_venta': venta_actual.items.all() if venta_actual else [],
        'is_farmacia': is_farmacia,
        'is_doctora': is_doctora,
    }
    return render(request, 'inventario/punto_de_venta.html', context)


@login_required
def ajax_agregar_a_venta(request):
    if request.method == 'POST':
        med_id = request.POST.get('med_id')
        cantidad = int(request.POST.get('cantidad', 1))

        try:
            medicamento = Medicamento.objects.get(pk=med_id)
            if cantidad > medicamento.cantidad_disponible:
                return JsonResponse({'error': f'No hay suficiente stock para {medicamento.nombre}. Stock disponible: {medicamento.cantidad_disponible}'}, status=400)
        except Medicamento.DoesNotExist:
            return JsonResponse({'error': 'Medicamento no encontrado.'}, status=404)

        venta_actual_id = request.session.get('venta_actual_id')
        if not venta_actual_id:
            return JsonResponse({'error': 'No hay una venta activa.'}, status=400)

        with transaction.atomic():
            venta = get_object_or_404(Venta, pk=venta_actual_id, estado='pendiente', farmaceuta=request.user)
            
            item, created = ItemVenta.objects.get_or_create(
                venta=venta,
                medicamento=medicamento,
                defaults={
                    'cantidad': cantidad,
                    'precio_unitario_venta': medicamento.precio_unitario,
                    'subtotal': medicamento.precio_unitario * cantidad
                }
            )

            if not created:
                item.cantidad += cantidad
                item.subtotal = item.cantidad * item.precio_unitario_venta
                item.save()

            medicamento.cantidad_disponible -= cantidad
            medicamento.save()
            
            venta.total = venta.items.all().aggregate(total=models.Sum('subtotal'))['total'] or Decimal('0.00')
            venta.save()
            
        return JsonResponse({'success': True, 'message': f'Se agregaron {cantidad} de {medicamento.nombre} a la venta.'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def ajax_eliminar_de_venta(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        try:
            item = ItemVenta.objects.select_related('medicamento', 'venta').get(pk=item_id)
        except ItemVenta.DoesNotExist:
            return JsonResponse({'error': 'Item de venta no encontrado.'}, status=404)

        with transaction.atomic():
            item.medicamento.cantidad_disponible += item.cantidad
            item.medicamento.save()
            
            venta = item.venta
            item.delete()
            
            venta.total = venta.items.all().aggregate(total=models.Sum('subtotal'))['total'] or Decimal('0.00')
            venta.save()

        return JsonResponse({'success': True, 'message': 'Producto eliminado de la venta y stock devuelto.'})

    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def ajax_finalizar_venta(request):
    if request.method == 'POST':
        venta_actual_id = request.session.get('venta_actual_id')
        venta = get_object_or_404(Venta, pk=venta_actual_id, estado='pendiente', farmaceuta=request.user)
        
        venta.estado = 'finalizada'
        venta.fecha_finalizacion = timezone.now()
        venta.save()
        
        request.session.pop('venta_actual_id', None)
        
        messages.success(request, f"Venta #{venta.pk} finalizada exitosamente.")
        return JsonResponse({'success': True, 'message': 'Venta finalizada.', 'venta_id': venta.pk})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ----------------- Nueva vista para el Recibo -----------------

# Inventario/views.py

@login_required
def imprimir_recibo(request, venta_id):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    venta = get_object_or_404(Venta.objects.select_related('farmaceuta'), pk=venta_id)
    items = ItemVenta.objects.select_related('medicamento').filter(venta=venta)
    
    context = {
        'venta': venta,
        'items': items,
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    
    return render(request, 'inventario/recibo.html', context)


@login_required
def historial_ventas(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    
    ventas = Venta.objects.filter(estado='finalizada').select_related('farmaceuta').order_by('-fecha_finalizacion')

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            ventas = ventas.filter(fecha_finalizacion__date__gte=fecha_inicio)
        except ValueError:
            messages.error(request, "El formato de la fecha de inicio no es válido.")
    
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            ventas = ventas.filter(fecha_finalizacion__date__lte=fecha_fin)
        except ValueError:
            messages.error(request, "El formato de la fecha de fin no es válido.")
    
    context = {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        'titulo': 'Historial de Ventas',
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }
    
    return render(request, 'inventario/historial_ventas.html', context)