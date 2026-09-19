# Inventario/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
# --- CORRECCIÓN 1: Se separó la línea 5 ---
from .forms import MedicamentoForm, Tag
import io
from django.http import HttpResponse
from datetime import datetime, timedelta, date
from collections import defaultdict
from .models import CorteDeCaja
# Importaciones para ReportLab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, mm
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, red
from reportlab.graphics.barcode import createBarcodeDrawing

from .models import Medicamento, Tag
# --- CORRECCIÓN 2: Se movieron todas las importaciones al inicio ---
from .forms import SeleccionarMedicamentosForm, MedicamentoForm, IniciarCorteForm, CerrarCorteForm

from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Medicamento, Venta, ItemVenta, Tag
from datetime import datetime

# --- CORRECCIÓN 2: Se añadió la importación faltante ---
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from Pacientes.alcance import doctor_del_usuario, ids_usuarios_consultorio


def _medicamentos_consultorio(request):
    doctor = doctor_del_usuario(request.user)
    if not doctor:
        return Medicamento.objects.none()
    return Medicamento.objects.filter(doctor=doctor)


def _asignar_doctor_medicamento(request, medicamento):
    medicamento.doctor = doctor_del_usuario(request.user)
    medicamento.save()

# ... (asegúrate de que los imports necesarios estén arriba) ...

@login_required
def lista_medicamentos(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    medicamentos = _medicamentos_consultorio(request).order_by('nombre')
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
            medicamento = form.save(commit=False)
            medicamento.doctor = doctor_del_usuario(request.user)
            medicamento.save()
            form.save_m2m()
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

    medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
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

    medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
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







# --- INICIO: NUEVA VISTA AJAX (Solo Doctora) ---

@login_required
@require_POST  # Asegura que esta vista solo acepte peticiones POST
@transaction.atomic  # Asegura que la operación en la DB sea atómica
def modificar_cantidad_medicamento(request, pk):
    """
    Modifica la cantidad de un medicamento (aumenta o disminuye en 1).
    Responde con JSON para ser usada por AJAX.
    SOLO 'Doctora' puede usarla.
    """

    # --- Validación de Permisos Estricta ---
    if not request.user.groups.filter(name='Doctora').exists():
        return JsonResponse({'error': 'No tienes permiso para esta acción.'}, status=403)

    try:
        medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
        action = request.POST.get('action')  # 'aumentar' o 'disminuir'

        if action == 'aumentar':
            medicamento.cantidad_disponible += 1

        elif action == 'disminuir':
            if medicamento.cantidad_disponible > 0:
                medicamento.cantidad_disponible -= 1
            else:
                # Si ya es 0, no hacemos nada y solo informamos
                return JsonResponse({
                    'status': 'info',
                    'message': 'La cantidad ya es 0.',
                    'nueva_cantidad': 0
                })
        else:
            return JsonResponse({'error': 'Acción no válida.'}, status=400)

        # Guardar el cambio en la base de datos
        medicamento.save()

        # Responder con éxito y la nueva cantidad
        return JsonResponse({
            'success': True,
            'nueva_cantidad': medicamento.cantidad_disponible
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- FIN: NUEVA VISTA AJAX ---





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
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()
    medicamentos = _medicamentos_consultorio(request).order_by('nombre')
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
            medicamento = form.save(commit=False)
            medicamento.doctor = doctor_del_usuario(request.user)
            medicamento.save()
            form.save_m2m()
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


    medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
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
    medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
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

@login_required
def imprimir_etiqueta_medicamento(request, pk):
    medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=pk)
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
    form = SeleccionarMedicamentosForm()
    form.fields['medicamentos'].queryset = _medicamentos_consultorio(request).order_by('nombre')

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
    medicamentos_dict = {med.pk: med for med in _medicamentos_consultorio(request).filter(pk__in=medicamento_ids)}

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
@login_required
def punto_venta(request):
    """
    Vista principal para el punto de venta.
    Muestra todos los medicamentos y la venta actual en sesión.
    """
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()


    # --- INICIO DE LA MODIFICACIÓN ---
    # 1. Verificar si hay un corte de caja activo para el usuario.
    try:
        corte_activo = CorteDeCaja.objects.get(usuario=request.user, is_open=True)
    except CorteDeCaja.DoesNotExist:
        # Si no hay corte activo, no se puede vender.
        messages.error(request, "No hay un corte de caja activo. Por favor, inicia uno para comenzar a vender.")
        return redirect('iniciar_corte') # Redirige a la página para iniciar un corte
    # --- FIN DE LA MODIFICACIÓN ---

    venta_actual_id = request.session.get('venta_actual_id')
    venta_actual = None
    if venta_actual_id:
        try:
            venta_actual = Venta.objects.get(pk=venta_actual_id, estado='pendiente', farmaceuta=request.user)
        except Venta.DoesNotExist:
            venta_actual = None
            request.session.pop('venta_actual_id', None)

    if not venta_actual:
        venta_actual = Venta.objects.create(
            farmaceuta=request.user,
            doctor=doctor_del_usuario(request.user),
            estado='pendiente',
        )
        request.session['venta_actual_id'] = venta_actual.pk

    context = {
        'medicamentos': _medicamentos_consultorio(request).order_by('nombre'),
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
            medicamento = get_object_or_404(_medicamentos_consultorio(request), pk=med_id)
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

        # 1. Buscar el corte activo
        try:
            corte_activo = CorteDeCaja.objects.get(usuario=request.user, is_open=True)
        except CorteDeCaja.DoesNotExist:
            return JsonResponse({'error': 'No se encontró un corte de caja activo. No se puede finalizar la venta.'}, status=400)

        # 2. Asociar la venta al corte activo
        venta.corte = corte_activo

        # --- INICIO DE LA NUEVA LÓGICA DE PAGO ---
        # Recibir los datos enviados por AJAX
        metodo_pago = request.POST.get('metodo_pago', 'Efectivo')
        monto_pagado_str = request.POST.get('monto_pagado_por_cliente')
        
        venta.metodo_pago = metodo_pago
        
        if monto_pagado_str:
            try:
                # Convertimos el string a Decimal de forma segura
                monto_pagado = Decimal(monto_pagado_str)
                if monto_pagado < venta.total:
                    return JsonResponse({'error': 'El monto pagado es menor al total de la venta.'}, status=400)
                
                venta.monto_pagado_por_cliente = monto_pagado
                
                # Calculamos el cambio solo si pagan en Efectivo
                if metodo_pago == 'Efectivo':
                    venta.cambio_devuelto = monto_pagado - venta.total
                else:
                    venta.cambio_devuelto = Decimal('0.00')
            except ValueError:
                return JsonResponse({'error': 'Monto pagado inválido.'}, status=400)
        else:
            # Si no envían monto, asumimos el pago exacto
            venta.monto_pagado_por_cliente = venta.total
            venta.cambio_devuelto = Decimal('0.00')
        # --- FIN DE LA NUEVA LÓGICA DE PAGO ---

        venta.estado = 'finalizada'
        venta.fecha_finalizacion = timezone.now()
        venta.save()

        request.session.pop('venta_actual_id', None)

        messages.success(request, f"Venta #{venta.pk} finalizada exitosamente por {metodo_pago}.")
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


_MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _fecha_local_venta(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).date()
    return dt.date()


def _restar_meses(origen, meses):
    mes = origen.month - meses
    anio = origen.year
    while mes <= 0:
        mes += 12
        anio -= 1
    return date(anio, mes, 1)


def _serie_ventas(desde, hasta, agrupacion='dia', doctor=None):
    qs = Venta.objects.filter(
        estado='finalizada',
        fecha_finalizacion__isnull=False,
        fecha_finalizacion__date__gte=desde,
        fecha_finalizacion__date__lte=hasta,
    ).only('fecha_finalizacion', 'total')
    if doctor:
        qs = qs.filter(doctor=doctor)

    buckets = defaultdict(lambda: Decimal('0.00'))
    for venta in qs:
        dia = _fecha_local_venta(venta.fecha_finalizacion)
        if not dia:
            continue
        clave = dia if agrupacion == 'dia' else date(dia.year, dia.month, 1)
        buckets[clave] += venta.total or Decimal('0.00')

    labels = []
    values = []
    if agrupacion == 'dia':
        cursor = desde
        while cursor <= hasta:
            labels.append(str(cursor.day))
            values.append(float(buckets[cursor]))
            cursor += timedelta(days=1)
    else:
        anio, mes = desde.year, desde.month
        fin = date(hasta.year, hasta.month, 1)
        while date(anio, mes, 1) <= fin:
            clave = date(anio, mes, 1)
            labels.append(f"{_MESES_ES[mes - 1]} {anio}")
            values.append(float(buckets[clave]))
            if mes == 12:
                anio += 1
                mes = 1
            else:
                mes += 1

    return {
        'labels': labels,
        'values': values,
        'total': round(sum(values), 2),
    }


@login_required
def historial_ventas(request):
    is_farmacia = request.user.groups.filter(name='Farmacia').exists()
    is_doctora = request.user.groups.filter(name='Doctora').exists()

    if is_farmacia and not is_doctora:
        messages.error(request, "No tienes permiso para ver el reporte de ventas.")
        return redirect('dashboard_farmacia')

    doctor = doctor_del_usuario(request.user)
    ventas = Venta.objects.filter(estado='finalizada', doctor=doctor).select_related('farmaceuta').prefetch_related('items__medicamento').order_by('-fecha_finalizacion')

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

    total_periodo = Decimal('0.00')
    for venta in ventas:
        if venta.total:
            total_periodo += venta.total

    hoy = timezone.localdate()
    chart_mes = _serie_ventas(hoy.replace(day=1), hoy, 'dia', doctor)
    chart_6m = _serie_ventas(_restar_meses(hoy, 5), hoy, 'mes', doctor)
    chart_anio = _serie_ventas(_restar_meses(hoy, 11), hoy, 'mes', doctor)

    context = {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        'titulo': 'Historial de Ventas',
        'total_periodo': total_periodo,
        'chart_mes': chart_mes,
        'chart_6m': chart_6m,
        'chart_anio': chart_anio,
        'is_farmacia': is_farmacia, # <-- ¡AGREGADO!
        'is_doctora': is_doctora, # <-- ¡AGREGADO!
    }

    return render(request, 'inventario/historial_ventas.html', context)



















@login_required
def iniciar_corte_view(request):
    # Reglas para no iniciar un corte si ya existe uno
    if CorteDeCaja.objects.filter(usuario=request.user, is_open=True).exists():
        messages.warning(request, "Ya tienes un corte de caja activo.")
        return redirect('corte_activo') # Asegúrate que 'corte_activo' es el name= de tu URL

    today = timezone.now().date()
    if CorteDeCaja.objects.filter(usuario=request.user, fecha_cierre__date=today, is_open=False).exists():
        messages.error(request, "Ya has realizado y cerrado tu corte de caja del día de hoy.")
        if request.user.groups.filter(name='Farmacia').exists():
            return render(request, 'Cortes/corte_ya_hecho.html')
        return redirect('historial_cortes') # Asegúrate que 'historial_cortes' es el name= de tu URL

    if request.method == 'POST':
        form = IniciarCorteForm(request.POST)
        if form.is_valid():
            fondo_inicial = form.cleaned_data['fondo_inicial']
            rol_usuario = 'doctora' if request.user.groups.filter(name='Doctora').exists() else 'farmacia'

            CorteDeCaja.objects.create(
                usuario=request.user,
                fondo_inicial=fondo_inicial,
                rol=rol_usuario,
                is_open=True  # <--- ¡ESTA ES LA CORRECCIÓN!
            )
            messages.success(request, "Corte de caja iniciado exitosamente.")
            return redirect('corte_activo') # Asegúrate que 'corte_activo' es el name= de tu URL
    else:
        form = IniciarCorteForm()

    return render(request, 'Cortes/iniciar_corte.html', {'form': form})


# Reemplaza estas dos vistas en tu Inventario/views.py

@login_required
def corte_activo_view(request):
    try:
        corte_activo = CorteDeCaja.objects.get(usuario=request.user, is_open=True)
    except CorteDeCaja.DoesNotExist:
        messages.info(request, "No tienes un corte de caja activo. Por favor, inicia uno.")
        return redirect('iniciar_corte')

    ventas_del_corte = Venta.objects.filter(corte=corte_activo)
    
    # Cálculos por método de pago
    total_ventas = Decimal('0.00')
    total_efectivo = Decimal('0.00')
    total_tarjeta = Decimal('0.00')
    total_transferencia = Decimal('0.00')

    for venta in ventas_del_corte:
        if venta.total:
            total_ventas += venta.total
            if venta.metodo_pago == 'Efectivo':
                total_efectivo += venta.total
            elif venta.metodo_pago == 'Tarjeta':
                total_tarjeta += venta.total
            elif venta.metodo_pago == 'Transferencia':
                total_transferencia += venta.total

    # El total esperado en FÍSICO (lo que debe haber en el cajón)
    total_esperado_efectivo = corte_activo.fondo_inicial + total_efectivo

    context = {
        'corte': corte_activo,
        'ventas': ventas_del_corte,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_tarjeta': total_tarjeta,
        'total_transferencia': total_transferencia,
        'total_esperado_efectivo': total_esperado_efectivo,
    }
    return render(request, 'Cortes/corte_activo.html', context)


@login_required
def cerrar_corte_view(request):
    corte_activo = get_object_or_404(CorteDeCaja, usuario=request.user, is_open=True)
    ventas_del_corte = Venta.objects.filter(corte=corte_activo)
    
    # Cálculos por método de pago
    total_ventas = Decimal('0.00')
    total_efectivo = Decimal('0.00')
    total_tarjeta = Decimal('0.00')
    total_transferencia = Decimal('0.00')

    for venta in ventas_del_corte:
        if venta.total:
            total_ventas += venta.total
            if venta.metodo_pago == 'Efectivo':
                total_efectivo += venta.total
            elif venta.metodo_pago == 'Tarjeta':
                total_tarjeta += venta.total
            elif venta.metodo_pago == 'Transferencia':
                total_transferencia += venta.total

    # El total esperado en FÍSICO es Fondo Inicial + Ventas en Efectivo
    total_esperado_efectivo = corte_activo.fondo_inicial + total_efectivo

    if request.method == 'POST':
        form = CerrarCorteForm(request.POST)
        if form.is_valid():
            # Extraemos los 3 valores que ingresó el usuario
            monto_final_contado = form.cleaned_data['monto_final_contado']
            monto_final_tarjeta = form.cleaned_data['monto_final_tarjeta']
            monto_final_transferencia = form.cleaned_data['monto_final_transferencia']

            # Guardamos los montos que ingresó
            corte_activo.monto_final_contado = monto_final_contado
            corte_activo.monto_final_tarjeta = monto_final_tarjeta
            corte_activo.monto_final_transferencia = monto_final_transferencia

            corte_activo.total_ventas_calculado = total_ventas
            
            # Calculamos las 3 diferencias por separado
            corte_activo.diferencia = monto_final_contado - total_esperado_efectivo
            corte_activo.diferencia_tarjeta = monto_final_tarjeta - total_tarjeta
            corte_activo.diferencia_transferencia = monto_final_transferencia - total_transferencia
            
            # Cerramos el corte
            corte_activo.is_open = False
            corte_activo.fecha_cierre = timezone.now()
            corte_activo.save()

            if request.user.groups.filter(name='Farmacia').exists():
                return redirect('corte_exitoso')
            else:
                messages.success(request, "Corte de caja cerrado exitosamente.")
                return redirect('historial_cortes')
    else:
        form = CerrarCorteForm()

    context = {
        'corte': corte_activo,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_tarjeta': total_tarjeta,
        'total_transferencia': total_transferencia,
        'total_esperado_efectivo': total_esperado_efectivo,
        'form': form,
    }
    return render(request, 'Cortes/cerrar_corte.html', context)


@login_required
def corte_exitoso_view(request):
    return render(request, 'Cortes/corte_exitoso.html')


# Función auxiliar para el decorador
def es_doctora(user):
    return user.groups.filter(name='Doctora').exists()



from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import IniciarCorteForm, CerrarCorteForm




@login_required
@user_passes_test(es_doctora, login_url='/')
def historial_cortes_view(request):
    doctor = doctor_del_usuario(request.user)
    cortes = CorteDeCaja.objects.filter(
        is_open=False,
        usuario_id__in=ids_usuarios_consultorio(doctor),
    ).order_by('-fecha_cierre')
    return render(request, 'Cortes/historial_cortes.html', {'cortes': cortes})








# Pacientes/context_processors.py

def user_roles_processor(request):
    """
    Este procesador de contexto añade los roles del usuario (is_doctora, is_farmacia)
    a todas las plantillas, siempre y cuando el usuario esté autenticado.
    """
    context = {
        'is_doctora': False,
        'is_farmacia': False,
    }

    # Solo calculamos los roles si el usuario ha iniciado sesión
    if request.user.is_authenticated:
        context['is_doctora'] = request.user.groups.filter(name='Doctora').exists()
        context['is_farmacia'] = request.user.groups.filter(name='Farmacia').exists()

    return context













@login_required
@user_passes_test(es_doctora, login_url='/')
@require_POST
def eliminar_cortes_antiguos(request):
    """
    Elimina los registros de CorteDeCaja antiguos.
    Las ventas asociadas no se borran gracias al on_delete=models.SET_NULL
    """
    periodo = request.POST.get('periodo')
    now = timezone.now()
    
    if periodo == '1_mes':
        fecha_limite = now - timedelta(days=30)
    elif periodo == '3_meses':
        fecha_limite = now - timedelta(days=90)
    else:
        messages.error(request, "Período no válido.")
        return redirect('historial_cortes')
        
    # Buscamos cortes cerrados (is_open=False) anteriores a la fecha límite
    doctor = doctor_del_usuario(request.user)
    cortes_a_borrar = CorteDeCaja.objects.filter(
        is_open=False,
        fecha_cierre__lt=fecha_limite,
        usuario_id__in=ids_usuarios_consultorio(doctor),
    )
    cantidad = cortes_a_borrar.count()
    
    if cantidad > 0:
        cortes_a_borrar.delete()
        messages.success(request, f"¡Limpieza exitosa! Se han eliminado {cantidad} cortes antiguos de la base de datos.")
    else:
        messages.info(request, "No se encontraron cortes tan antiguos para borrar.")
        
    return redirect('historial_cortes')


def _puede_borrar_ventas(user):
    return user.groups.filter(name='Doctora').exists()


@login_required
@require_POST
def eliminar_ventas_lote(request):
    if not _puede_borrar_ventas(request.user):
        messages.error(request, "No tienes permiso para borrar ventas.")
        return redirect('historial_ventas')

    ventas_ids = request.POST.getlist('ventas_ids')
    if not ventas_ids:
        messages.warning(request, "No seleccionaste ninguna venta para borrar.")
        return redirect('historial_ventas')

    ventas_a_borrar = Venta.objects.filter(
        pk__in=ventas_ids,
        estado='finalizada',
        doctor=doctor_del_usuario(request.user),
    )
    cantidad = ventas_a_borrar.count()
    ventas_a_borrar.delete()

    if cantidad:
        messages.success(request, f"Se borraron {cantidad} venta{'s' if cantidad != 1 else ''} del historial.")
    else:
        messages.info(request, "No se encontraron ventas finalizadas para borrar.")
    return redirect('historial_ventas')


@login_required
@require_POST
def eliminar_ventas_antiguas(request):
    if not _puede_borrar_ventas(request.user):
        messages.error(request, "No tienes permiso para borrar ventas.")
        return redirect('historial_ventas')

    periodo = request.POST.get('periodo')
    if periodo != '3_meses':
        messages.error(request, "Período no válido.")
        return redirect('historial_ventas')

    fecha_limite = timezone.now() - timedelta(days=90)
    ventas_a_borrar = Venta.objects.filter(
        estado='finalizada',
        fecha_finalizacion__isnull=False,
        fecha_finalizacion__lt=fecha_limite,
        doctor=doctor_del_usuario(request.user),
    )
    cantidad = ventas_a_borrar.count()
    ventas_a_borrar.delete()

    if cantidad:
        messages.success(request, f"Se borraron {cantidad} ventas de más de 3 meses.")
    else:
        messages.info(request, "No hay ventas de más de 3 meses para borrar.")
    return redirect('historial_ventas')