"""Formularios para la gestión de eventos."""
from django import forms
from .models import Evento


class EventoForm(forms.ModelForm):
    """Formulario para crear/editar eventos."""
    class Meta:
        model = Evento
        fields = ["tipo", "fecha_inicio", "fecha_fin", "punto_encuentro", "notas"]
