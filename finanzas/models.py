"""Modelos para pagos de manutención y gastos compartidos."""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# ---------------------------
# VALIDACIÓN DE ARCHIVOS PDF
# ---------------------------
def validar_pdf(value):
    if not value.name.lower().endswith(".pdf"):
        raise ValidationError("El archivo debe ser un PDF.")


class Pago(models.Model):
    """Pago de manutención (300€ del día 1 al 10)."""

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
    ]

    grupo = models.ForeignKey(
        "core.GrupoCoparental", on_delete=models.CASCADE, related_name="pagos"
    )
    monto = models.DecimalField("Monto", max_digits=8, decimal_places=2, default=300)
    fecha = models.DateField("Fecha del pago")

    comprobante_pdf = models.FileField(
        "Comprobante PDF",
        upload_to="comprobantes/",
        blank=True,
        null=True,
        validators=[validar_pdf],
    )

    estado = models.CharField(
        "Estado", max_length=10, choices=ESTADO_CHOICES, default="pendiente"
    )

    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_creados",
    )

    def __str__(self):
        return f"Pago {self.monto}€ - {self.fecha} ({self.get_estado_display()})"


class Gasto(models.Model):
    """Gasto compartido 50/50 con comprobantes y finiquito."""

    grupo = models.ForeignKey(
        "core.GrupoCoparental", on_delete=models.CASCADE, related_name="gastos"
    )
    concepto = models.CharField("Concepto", max_length=255)
    monto = models.DecimalField("Monto", max_digits=8, decimal_places=2)

    # Fecha real del gasto
    fecha = models.DateField("Fecha del gasto", auto_now_add=True, null=True)

    # Comprobante del gasto original (cualquier formato)
    comprobante = models.FileField(
        "Comprobante",
        upload_to="comprobantes/gastos/",
        blank=True,
        null=True,
    )

    # Comprobante del pago de la deuda 50/50 (PDF)
    comprobante_deuda = models.FileField(
        "Comprobante de deuda",
        upload_to="comprobantes/deuda/",
        blank=True,
        null=True,
        validators=[validar_pdf],
    )

    # Quién pagó el gasto original
    pagado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gastos_pagados",
    )

    # Quién pagó la deuda 50/50
    deuda_pagada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deudas_pagadas",
    )

    # Deuda automática 50/50
    deuda_50_50 = models.DecimalField(
        "Deuda 50/50",
        max_digits=8,
        decimal_places=2,
        editable=False,
    )

    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    # Estado del gasto compartido
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("finiquitado", "Finiquitado"),
    ]

    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=ESTADO_CHOICES,
        default="pendiente",
    )

    def save(self, *args, **kwargs):
        """Calcula automáticamente la deuda 50/50 antes de guardar."""
        self.deuda_50_50 = self.monto / 2
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.concepto} - {self.monto}€"
