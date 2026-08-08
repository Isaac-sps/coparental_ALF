"""Vistas para el calendario de eventos."""

import calendar
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Evento
from .forms import EventoForm
from core.models import registrar_actividad
from core.decorators import solo_padres

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@solo_padres
def calendario_mensual(request):
    """Vista de calendario mensual (grid) con navegación mes anterior/siguiente."""
    hoy = date.today()
    try:
        ano = int(request.GET.get("ano", hoy.year))
        mes = int(request.GET.get("mes", hoy.month))
    except (TypeError, ValueError):
        ano, mes = hoy.year, hoy.month

    # Navegar fuera de [1, 12] pasa al año anterior/siguiente
    if mes < 1:
        mes, ano = 12, ano - 1
    elif mes > 12:
        mes, ano = 1, ano + 1

    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(ano, mes)

    eventos_mes = Evento.objects.filter(
        grupo=request.grupo,
        fecha_inicio__lte=semanas[-1][-1],
        fecha_fin__gte=semanas[0][0],
    )

    eventos_por_dia = {}
    for evento in eventos_mes:
        dia = evento.fecha_inicio
        while dia <= evento.fecha_fin:
            eventos_por_dia.setdefault(dia, []).append(evento)
            dia += timedelta(days=1)

    semanas_calendario = [
        [
            {"fecha": dia, "del_mes": dia.month == mes, "eventos": eventos_por_dia.get(dia, [])}
            for dia in semana
        ]
        for semana in semanas
    ]

    primer_dia_mes = date(ano, mes, 1)
    mes_anterior = primer_dia_mes - timedelta(days=1)
    mes_siguiente = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)

    context = {
        "semanas": semanas_calendario,
        "dias_semana": DIAS_SEMANA,
        "mes_actual": primer_dia_mes,
        "mes_anterior": mes_anterior,
        "mes_siguiente": mes_siguiente,
        "hoy": hoy,
    }
    return render(request, "calendario/calendario_mensual.html", context)


@solo_padres
def historial_eventos(request):
    """Historial de eventos con búsqueda: por defecto solo los pasados."""
    hoy = date.today()
    texto = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    incluir_futuros = request.GET.get("incluir_futuros") == "1"

    eventos = Evento.objects.filter(grupo=request.grupo)

    if not incluir_futuros and not desde and not hasta:
        eventos = eventos.filter(fecha_fin__lt=hoy)

    if texto:
        eventos = eventos.filter(notas__icontains=texto)
    if tipo:
        eventos = eventos.filter(tipo=tipo)
    if desde:
        eventos = eventos.filter(fecha_fin__gte=desde)
    if hasta:
        eventos = eventos.filter(fecha_inicio__lte=hasta)

    eventos = eventos.order_by("-fecha_inicio")

    context = {
        "eventos": eventos,
        "texto": texto,
        "tipo": tipo,
        "desde": desde,
        "hasta": hasta,
        "incluir_futuros": incluir_futuros,
        "tipo_choices": Evento.TIPO_CHOICES,
    }
    return render(request, "calendario/historial_eventos.html", context)


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
