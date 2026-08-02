"""Formularios para chat y archivos."""
from django import forms
from .models import Mensaje, ArchivoCompartido


class MensajeForm(forms.ModelForm):
    """Formulario para enviar un mensaje de chat."""
    class Meta:
        model = Mensaje
        fields = ["contenido"]


class ArchivoForm(forms.ModelForm):
    """Formulario para subir un archivo compartido."""
    class Meta:
        model = ArchivoCompartido
        fields = ["archivo", "descripcion"]
