# InventarioInsumos/admin.py
from django.contrib import admin
from .models import Insumo, TagInsumo

@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cantidad_disponible', 'unidad_medida', 'fecha_ultima_actualizacion')
    list_filter = ('fecha_ultima_actualizacion',)
    search_fields = ('nombre', 'descripcion', 'fabricante')
    prepopulated_fields = {'nombre': ('nombre',)}

@admin.register(TagInsumo)
class TagInsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
# Register your models here.
