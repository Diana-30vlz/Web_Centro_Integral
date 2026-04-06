from django.db import models

# Create your models here.
# InventarioInsumos/models.py
from django.db import models
from django.core.validators import MinValueValidator

# Si vas a usar etiquetas, debes crear un modelo de Tag para esta aplicación
class TagInsumo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Insumo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Insumo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    fabricante = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fabricante")
    
    unidad_medida = models.CharField(max_length=50, blank=True, null=True, verbose_name="Unidad de Medida")
    cantidad_disponible = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Cantidad Disponible"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Precio de Compra"
    )

    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    tags = models.ManyToManyField(TagInsumo, blank=True, verbose_name="Etiquetas")

    def __str__(self):
        return f"{self.nombre} ({self.cantidad_disponible} {self.unidad_medida or ''})"

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre']