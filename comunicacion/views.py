"""Vistas para comunicación interna (chat + archivos)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Mensaje, ArchivoCompartido
from .forms import MensajeForm, ArchivoForm


@login_required
def chat(request):
    """Vista principal del chat interno."""
    mensajes = Mensaje.objects.order_by("-fecha_creacion")[:50]

    if request.method == "POST":
        form = MensajeForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
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


@login_required
def subir_archivo(request):
    """Subir un archivo compartido entre los padres."""
    if request.method == "POST":
        form = ArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.save(commit=False)
            archivo.autor = request.user
            archivo.save()
            return redirect(reverse("comunicacion:chat"))
    else:
        form = ArchivoForm()

    return render(request, "comunicacion/archivo_form.html", {"form": form})

