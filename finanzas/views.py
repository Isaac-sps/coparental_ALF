"""Vistas para la gestión financiera."""

from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from weasyprint import HTML
import base64
import tempfile
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, UpdateView
from .models import Pago, Gasto
from .forms import PagoForm, GastoForm

# Servicio de notificaciones automáticas
from shared.services import enviar_notificacion_email

# ✔ CORRECTO: esta es la función real que sí debes usar
from core.models import registrar_actividad


def _construir_contexto_resumen(request):
    """Arma el contexto de pagos/gastos/gráficos que comparten el resumen y el PDF."""
    pagos = Pago.objects.order_by("-fecha")
    gastos = Gasto.objects.order_by("-fecha")

    # ---------------------------
    # FILTROS
    # ---------------------------
    mes = request.GET.get("mes")
    ano = request.GET.get("ano")
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    pagado_por = request.GET.get("pagado_por")

    # FILTRO POR AÑO
    if ano:
        gastos = gastos.filter(fecha__year=ano)

    # FILTRO POR MES
    if mes:
        gastos = gastos.filter(fecha__month=mes)

    # FILTRO POR RANGO DE FECHAS
    if desde and hasta:
        gastos = gastos.filter(fecha__range=[desde, hasta])

    # FILTRO POR QUIÉN PAGÓ
    if pagado_por == "padre":
        gastos = gastos.filter(pagado_por=request.user)
    elif pagado_por == "madre":
        gastos = gastos.exclude(pagado_por=request.user)

    # ---------------------------
    # BALANCE AUTOMÁTICO
    # ---------------------------
    total_padre = sum(g.monto for g in gastos if g.pagado_por == request.user)
    total_madre = sum(g.monto for g in gastos if g.pagado_por != request.user)

    balance = total_padre - total_madre

    # ---------------------------
    # DATOS PARA EL GRÁFICO (orden cronológico ascendente)
    # ---------------------------
    gastos_con_fecha = sorted((g for g in gastos if g.fecha), key=lambda g: g.fecha)
    grafico_gastos = {
        "labels": [g.fecha.isoformat() for g in gastos_con_fecha],
        "data": [float(g.monto) for g in gastos_con_fecha],
    }
    # GRÁFICO COMPARATIVO PADRE VS MADRE
    total_padre = (
        gastos.filter(pagado_por=request.user).aggregate(total=Sum("monto"))["total"]
        or 0
    )
    total_madre = (
        gastos.exclude(pagado_por=request.user).aggregate(total=Sum("monto"))["total"]
        or 0
    )

    grafico_comparativo = {
        "labels": ["Padre", "Madre"],
        "data": [float(total_padre), float(total_madre)],
    }

    gastos_por_mes = (
        gastos.annotate(mes=ExtractMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    grafico_mensual = {
        "labels": [f"Mes {g['mes']}" for g in gastos_por_mes],
        "data": [float(g["total"]) for g in gastos_por_mes],
    }

    gastos_por_ano = (
        gastos.annotate(ano=ExtractYear("fecha"))
        .values("ano")
        .annotate(total=Sum("monto"))
        .order_by("ano")
    )

    grafico_anual = {
        "labels": [str(g["ano"]) for g in gastos_por_ano],
        "data": [float(g["total"]) for g in gastos_por_ano],
    }

    return {
        "pagos": pagos,
        "gastos": gastos,
        "balance": balance,
        "hoy": date.today(),
        "grafico_gastos": grafico_gastos,
        "grafico_comparativo": grafico_comparativo,
        "grafico_mensual": grafico_mensual,
        "grafico_anual": grafico_anual,
    }


@login_required
def resumen(request):
    registrar_actividad(
        request.user,
        "ver_resumen_financiero",
        "El usuario ha visto el resumen financiero.",
    )

    contexto = _construir_contexto_resumen(request)
    return render(request, "finanzas/resumen.html", contexto)


@login_required
def exportar_pdf(request):
    """Genera un PDF del resumen financiero."""

    contexto = _construir_contexto_resumen(request)

    # Logo incrustado en base64: WeasyPrint no resuelve rutas /static/...
    # sin una petición HTTP aparte, así que se embebe directo en el HTML.
    logo_path = finders.find("core/img/logo_pdf.png")
    if logo_path:
        with open(logo_path, "rb") as f:
            contexto["logo_base64"] = base64.b64encode(f.read()).decode("ascii")

    # Renderizamos la plantilla HTML del PDF (con request para que
    # pdf_resumen.html pueda comparar gasto.pagado_por == request.user)
    html_string = render_to_string(
        "finanzas/pdf_resumen.html", contexto, request=request
    )

    # Creamos el PDF
    html = HTML(string=html_string)
    result = html.write_pdf()

    # Enviamos el PDF como descarga
    response_pdf = HttpResponse(result, content_type="application/pdf")
    response_pdf["Content-Disposition"] = "attachment; filename=resumen_financiero.pdf"

    return response_pdf


@login_required
def nuevo_pago(request):
    """Registrar un nuevo pago de manutención."""
    if request.method == "POST":
        form = PagoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.creado_por = request.user

            if pago.comprobante_pdf:
                pago.estado = "pagado"

            pago.save()

            # ✔ Registrar actividad correctamente
            registrar_actividad(
                request.user, "crear_pago", f"Pago de {pago.monto} creado."
            )

            enviar_notificacion_email(
                destinatario=request.user.email,
                asunto="Nuevo pago registrado",
                mensaje=f"Has registrado un pago de {pago.monto}€ con fecha {pago.fecha}.",
            )
            return redirect(reverse("finanzas:resumen"))
    else:
        form = PagoForm()
    return render(request, "finanzas/pago_form.html", {"form": form})


@login_required
def marcar_pagado(request, pk):
    """Marcar un pago como pagado."""
    pago = get_object_or_404(Pago, pk=pk)
    pago.estado = "pagado"
    pago.save()

    registrar_actividad(
        request.user, "marcar_pago_pagado", f"Pago ID {pago.id} marcado como pagado."
    )

    enviar_notificacion_email(
        destinatario=request.user.email,
        asunto="Pago marcado como pagado",
        mensaje=f"El pago del {pago.fecha} ha sido marcado como pagado.",
    )

    return redirect(reverse("finanzas:resumen"))


@login_required
def nuevo_gasto(request):
    """Registrar un nuevo gasto compartido 50/50."""
    if request.method == "POST":
        form = GastoForm(request.POST, request.FILES)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.pagado_por = request.user

            gasto.save()

            registrar_actividad(
                request.user, "crear_gasto", f"Gasto de {gasto.monto} creado."
            )

            enviar_notificacion_email(
                destinatario=request.user.email,
                asunto="Nuevo gasto registrado",
                mensaje=f"Has registrado un gasto de {gasto.concepto} por {gasto.monto}€.",
            )

            return redirect(reverse("finanzas:resumen"))
    else:
        form = GastoForm()
    return render(request, "finanzas/gasto_form.html", {"form": form})


# --- EDITAR PAGO ---
class PagoUpdateView(UpdateView):
    model = Pago
    form_class = PagoForm
    template_name = "finanzas/editar_pago.html"
    success_url = reverse_lazy("finanzas:resumen")

    def form_valid(self, form):
        registrar_actividad(
            self.request.user, "editar_pago", f"Pago ID {self.object.id} editado."
        )
        return super().form_valid(form)


# --- ELIMINAR PAGO ---
class PagoDeleteView(DeleteView):
    model = Pago
    template_name = "finanzas/eliminar_pago.html"
    success_url = reverse_lazy("finanzas:resumen")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        registrar_actividad(
            request.user, "eliminar_pago", f"Pago ID {obj.id} eliminado."
        )
        return super().delete(request, *args, **kwargs)

    # --- EDITAR GASTO ---


class GastoUpdateView(UpdateView):
    model = Gasto
    form_class = GastoForm
    template_name = "finanzas/editar_gasto.html"
    success_url = reverse_lazy("finanzas:resumen")

    def form_valid(self, form):
        registrar_actividad(
            self.request.user, "editar_gasto", f"Gasto ID {self.object.id} editado."
        )
        return super().form_valid(form)


# --- ELIMINAR GASTO ---
class GastoDeleteView(DeleteView):
    model = Gasto
    template_name = "finanzas/eliminar_gasto.html"
    success_url = reverse_lazy("finanzas:resumen")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        registrar_actividad(
            request.user, "eliminar_gasto", f"Gasto ID {obj.id} eliminado."
        )
        return super().delete(request, *args, **kwargs)
