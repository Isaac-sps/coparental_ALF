"""Vistas para el calendario de eventos."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Evento
from .forms import EventoForm
from core.models import registrar_actividad


@login_required
def lista_eventos(request):
    """Lista de todos los eventos (ambos padres ven todo)."""
    eventos = Evento.objects.order_by("fecha_inicio")
    return render(request, "calendario/lista_eventos.html", {"eventos": eventos})


@login_required
def crear_evento(request):
    """Crear un nuevo evento de calendario."""
    if request.method == "POST":
        form = EventoForm(request.POST)
        if form.is_valid():
            evento = form.save()

            # ⭐ NUEVO: registrar actividad al crear evento
            registrar_actividad(
                request.user, "Evento creado", f"Evento: {evento}"
            )

            return redirect(reverse("calendario:lista"))
    else:
        form = EventoForm()

    return render(request, "calendario/evento_form.html", {"form": form})


@login_required
def editar_evento(request, pk):
    """Editar un evento existente (ambos padres pueden editar)."""
    evento = get_object_or_404(Evento, pk=pk)

    if request.method == "POST":
        form = EventoForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()

            # ⭐ NUEVO: registrar actividad al editar evento
            registrar_actividad(
                request.user, "Evento editado", f"Evento: {evento}"
            )

            return redirect(reverse("calendario:lista"))
    else:
        form = EventoForm(instance=evento)

    return render(
        request, "calendario/evento_form.html", {"form": form, "evento": evento}
    )


@login_required
def eliminar_evento(request, pk):
    """Eliminar un evento existente (ambos padres pueden eliminar)."""
    evento = get_object_or_404(Evento, pk=pk)

    if request.method == "POST":
        descripcion = str(evento)  # Guardamos la descripción antes de eliminar
        evento.delete()

        # ⭐ NUEVO: registrar actividad al eliminar evento
        registrar_actividad(
            request.user,
            "Evento eliminado",
            f"Evento eliminado: {descripcion}"
        )

        return redirect(reverse("calendario:lista"))

    return render(
        request,
        "calendario/confirmar_eliminar.html",
        {"evento": evento}
    )

