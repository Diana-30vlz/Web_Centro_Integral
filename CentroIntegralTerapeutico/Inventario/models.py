# Inventario/models.py
from django.db import models
from django.contrib.auth import get_user_model

from django.core.validators import MinValueValidator

# Inventario/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings


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
    doctor = models.ForeignKey(
        'Pacientes.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicamentos',
        verbose_name="Doctor dueño",
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Medicamento")
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
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'nombre'], name='uniq_medicamento_doctor_nombre'),
        ]
        
        
# --- NUEVOS MODELOS PARA EL PUNTO DE VENTA ---








class CorteDeCaja(models.Model):
    # --- AÑADE ESTAS LÍNEAS ---
    ROL_CHOICES = (
        ('doctora', 'Doctora'),
        ('farmacia', 'Farmacia'),
    )
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, verbose_name="Rol del Corte")
    # --- FIN DE LAS LÍNEAS A AÑADIR ---

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_apertura = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Apertura")
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Cierre")
    
    fondo_inicial = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fondo Inicial en Caja")
    monto_final_contado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto Final Contado")
    
    # --- NUEVOS CAMPOS ---
    monto_final_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto Final Tarjeta")
    monto_final_transferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto Final Transferencia")
    
    diferencia_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Diferencia Tarjeta")
    diferencia_transferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Diferencia Transferencia")
    # ---------------------
    
    total_ventas_calculado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Total de Ventas (Calculado)")
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Diferencia")
    
    total_ventas_calculado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Total de Ventas (Calculado)")
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Diferencia")
    
    is_open = models.BooleanField(null=True, blank=True,verbose_name="¿Está abierto?")

    def __str__(self):
        return f"Corte de {self.get_rol_display()} ({self.usuario.username}) - {self.fecha_apertura.strftime('%d/%m/%Y')}"










class Venta(models.Model):
    """Representa una transacción de venta."""
    corte = models.ForeignKey(CorteDeCaja, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')

    doctor = models.ForeignKey(
        'Pacientes.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas',
        verbose_name="Doctor dueño",
    )
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
    
    
    METODO_PAGO_CHOICES = (
        ('Efectivo', 'Efectivo'),
        ('Tarjeta', 'Tarjeta de Crédito/Débito'),
        ('Transferencia', 'Transferencia Bancaria'),
    )
    
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='Efectivo',
        verbose_name="Método de Pago"
    )
    
    # Estos campos son muy útiles para el ticket y el corte, te sugiero agregarlos
    monto_pagado_por_cliente = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Cuánto dinero entregó el cliente"
    )
    cambio_devuelto = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Cuánto se le devolvió"
    )

    def __str__(self):
        return f"Venta #{self.pk} - {self.get_estado_display()} - {self.metodo_pago}"
    
    
    

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
    
    
    
    
    
    
    
    
    
    
