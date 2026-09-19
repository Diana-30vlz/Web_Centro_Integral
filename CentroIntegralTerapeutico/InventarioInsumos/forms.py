# InventarioInsumos/forms.py
from django import forms
from .models import Insumo, TagInsumo

class InsumoForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=TagInsumo.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Etiquetas"
    )

    class Meta:
        model = Insumo
        exclude = ('doctor',)
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'nombre': 'Nombre del Insumo',
            'descripcion': 'Descripción',
            'fabricante': 'Fabricante',
            'unidad_medida': 'Unidad de Medida',
            'cantidad_disponible': 'Cantidad Disponible',
            'precio_compra': 'Precio de Compra (unidad)',
            'tags': 'Etiquetas',
        }