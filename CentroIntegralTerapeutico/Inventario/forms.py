# Inventario/forms.py
from django import forms
from .models import Medicamento, Tag # <-- Asegúrate de importar Tag

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
            'fecha_caducidad': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), # <--- ¡Nuevo campo!
        }
        labels = {
            'nombre': 'Nombre del Medicamento',
            'descripcion': 'Descripción',
            'fabricante': 'Fabricante',
            'unidad_medida': 'Unidad de Medida',
            'cantidad_disponible': 'Cantidad Disponible',
            'precio_compra': 'Precio de Compra (unidad)',
            'precio_unitario': 'Precio de Venta (unidad)', # <--- ¡Nuevo campo!
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
