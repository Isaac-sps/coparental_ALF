"""Formularios para el chat interno."""
from django import forms
from .models import Mensaje


class MensajeForm(forms.ModelForm):
    """Formulario para enviar un mensaje de chat."""
    class Meta:
        model = Mensaje
        fields = ["contenido"]
