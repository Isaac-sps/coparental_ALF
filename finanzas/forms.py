"""Formularios para pagos y gastos."""
from django import forms
from .models import Pago, Gasto


class PagoForm(forms.ModelForm):
    """Formulario para registrar un pago y subir comprobante."""
    class Meta:
        model = Pago
        fields = ["monto", "fecha", "comprobante_pdf"]


class GastoForm(forms.ModelForm):
    """Formulario para registrar un gasto compartido."""
    class Meta:
        model = Gasto
        # ❌ ANTES: ["concepto", "monto", "comprobante_pdf", "foto"]
        # ✔ AHORA: un solo campo comprobante
        fields = ["concepto", "monto", "comprobante"]
