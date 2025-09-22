# Inventario/models.py
from django.db import models
from django.contrib.auth import get_user_model

from django.core.validators import MinValueValidator

# Inventario/models.py
from django.db import models
from django.core.validators import MinValueValidator


User = get_user_model() 



# --- Nuevo Modelo para Etiquetas ---
class Tag(models.Model):
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre de la Etiqueta")
    
    class Meta:
        verbose_name = "Etiqueta"
        verbose_name_plural = "Etiquetas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

# --- Modelo Medicamento (Modificado) ---
class Medicamento(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del Medicamento")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    fabricante = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fabricante")
    
    unidad_medida = models.CharField(max_length=50, verbose_name="Unidad de Medida")
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
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Precio de Venta"
    ) # <--- ¡Este es el campo que faltaba!

    fecha_caducidad = models.DateField(blank=True, null=True, verbose_name="Fecha de Caducidad")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    # --- Campo ManyToMany para etiquetas (ya lo tenías) ---
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Etiquetas")

    def __str__(self):
        return f"{self.nombre} ({self.cantidad_disponible} {self.unidad_medida})"

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ['nombre']
        
        
# --- NUEVOS MODELOS PARA EL PUNTO DE VENTA ---

class Venta(models.Model):
    """Representa una transacción de venta."""
    farmaceuta = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estado = models.CharField(
        max_length=20, 
        choices=[('pendiente', 'Pendiente'), ('finalizada', 'Finalizada')],
        default='pendiente'
    )

    def __str__(self):
        return f"Venta #{self.pk} - {self.get_estado_display()}"

class ItemVenta(models.Model):
    """Representa un producto dentro de una venta."""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name='items_venta')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario_venta = models.DecimalField(max_digits=10, decimal_places=2) # Precio al momento de la venta
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario_venta
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.medicamento.nombre} en Venta #{self.venta.pk}"        