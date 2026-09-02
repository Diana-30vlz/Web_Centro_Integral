# Inventario/forms.py
from django import forms
from .models import Medicamento, Tag, CorteDeCaja # <-- Asegúrate de importar Tag

class MedicamentoForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Etiquetas"
    )

    class Meta:
        model = Medicamento
        fields = '__all__'
        widgets = {
            # MODIFICACIÓN CLAVE AQUÍ
            'fecha_caducidad': forms.DateInput(
                format='%Y-%m-%d',  # <--- ¡ESTA ES LA LÍNEA QUE SOLUCIONA EL PROBLEMA!
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        # ... El resto de tu form se queda igual
        labels = {
            'nombre': 'Nombre del Medicamento',
            'descripcion': 'Descripción',
            'fabricante': 'Fabricante',
            'unidad_medida': 'Unidad de Medida',
            'cantidad_disponible': 'Cantidad Disponible',
            'precio_compra': 'Precio de Compra (unidad)',
            'precio_unitario': 'Precio de Venta (unidad)',
            'fecha_caducidad': 'Fecha de Caducidad',
            'tags': 'Etiquetas',
        }

class SeleccionarMedicamentosForm(forms.Form):
    # Este formulario solo servirá para inicializar la lista de medicamentos en la plantilla.
    # La selección de cantidad se manejará en el HTML/JS.
    medicamentos = forms.ModelMultipleChoiceField(
        queryset=Medicamento.objects.all().order_by('nombre'),
        widget=forms.CheckboxSelectMultiple,
        label="Seleccionar Medicamentos a Imprimir"
    )







class IniciarCorteForm(forms.Form):
    fondo_inicial = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Fondo Inicial en Caja ($)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 500.00'})
    )

class CerrarCorteForm(forms.Form):
    monto_final_contado = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Ingresa el monto total contado en caja FÍSICA (Efectivo $)",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg border-danger', 'placeholder': 'Ej: 600.00'})
    )
    monto_final_tarjeta = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Ingresa el monto total contado en Tarjeta (Vouchers $)",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg border-primary', 'placeholder': 'Ej: 400.00'})
    )
    monto_final_transferencia = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Ingresa el monto total contado en Transferencias ($)",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg border-info', 'placeholder': 'Ej: 0.00'})
    )