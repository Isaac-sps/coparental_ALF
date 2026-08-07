"""Formularios de la app core."""
from django import forms
from django.contrib.auth.models import User
from .models import Padre, MensajeCanal, DocumentoCanal


class UsuarioForm(forms.ModelForm):
    """Datos básicos de cuenta (nombre, apellido, correo)."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
        }


class PadreForm(forms.ModelForm):
    """Formulario para editar el perfil del padre."""
    class Meta:
        model = Padre
        fields = ["foto", "fecha_nacimiento", "telefono", "domicilio"]
        widgets = {
            "fecha_nacimiento": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date"}
            ),
        }


class MensajeCanalForm(forms.ModelForm):
    """Formulario para enviar un mensaje dentro de un canal de rol."""
    class Meta:
        model = MensajeCanal
        fields = ["contenido"]
        labels = {"contenido": ""}
        widgets = {
            "contenido": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Escribe un mensaje..."}
            ),
        }


class DocumentoCanalForm(forms.ModelForm):
    """Formulario para subir un documento a un canal de rol."""
    class Meta:
        model = DocumentoCanal
        fields = ["titulo", "archivo", "descripcion"]
