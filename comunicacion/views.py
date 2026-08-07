"""Vistas para el chat interno entre padre y madre.

Los archivos compartidos se suben desde Canal ALF (ver core.views.canal_alf),
clasificados por rol.
"""
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Mensaje
from .forms import MensajeForm
from core.decorators import solo_padres


@solo_padres
def chat(request):
    """Vista principal del chat interno del grupo."""
    mensajes = Mensaje.objects.filter(grupo=request.grupo).order_by("-fecha_creacion")[:50]

    if request.method == "POST":
        form = MensajeForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.grupo = request.grupo
            mensaje.autor = request.user
            mensaje.save()
            return redirect(reverse("comunicacion:chat"))
    else:
        form = MensajeForm()

    return render(
        request,
        "comunicacion/chat.html",
        {"mensajes": mensajes, "form": form},
    )
