# Inventario/admin.py
from django.contrib import admin
from .models import Medicamento, Tag, Venta, ItemVenta

@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cantidad_disponible', 'precio_unitario', 'fecha_caducidad')
    search_fields = ('nombre', 'tags__nombre')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'farmaceuta', 'fecha_creacion', 'total', 'estado')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('farmaceuta__username',)

@admin.register(ItemVenta)
class ItemVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'medicamento', 'cantidad', 'precio_unitario_venta', 'subtotal')
    list_filter = ('venta__estado',)
    search_fields = ('medicamento__nombre',)