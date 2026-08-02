"""Formularios de la app core."""
from django import forms
from django.contrib.auth.models import User
from .models import Padre


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
