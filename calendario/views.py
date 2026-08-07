"""Vistas para el calendario de eventos."""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Evento
from .forms import EventoForm
from core.models import registrar_actividad
from core.decorators import solo_padres


@solo_padres
def lista_eventos(request):
    """Lista de los eventos del grupo del usuario (ambos padres ven todo)."""
    eventos = Evento.objects.filter(grupo=request.grupo).order_by("fecha_inicio")
    return render(request, "calendario/lista_eventos.html", {"eventos": eventos})


@solo_padres
def crear_evento(request):
    """Crear un nuevo evento de calendario en el grupo del usuario."""
    if request.method == "POST":
        form = EventoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.grupo = request.grupo
            evento.save()

            # ⭐ NUEVO: registrar actividad al crear evento
            registrar_actividad(
                request.user, "Evento creado", f"Evento: {evento}"
            )

            return redirect(reverse("calendario:lista"))
    else:
        form = EventoForm()

    return render(request, "calendario/evento_form.html", {"form": form})


@solo_padres
def editar_evento(request, pk):
    """Editar un evento existente del grupo del usuario."""
    evento = get_object_or_404(Evento, pk=pk, grupo=request.grupo)

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


@solo_padres
def eliminar_evento(request, pk):
    """Eliminar un evento existente del grupo del usuario."""
    evento = get_object_or_404(Evento, pk=pk, grupo=request.grupo)

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
