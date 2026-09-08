"""Vistas para la gestión financiera."""

from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from weasyprint import HTML
import base64
import tempfile
from datetime import date
from django.db.models.aggregates import Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, UpdateView
from django.contrib import messages

from .models import Pago, Gasto
from .forms import PagoForm, GastoForm

# NOTIF: antes se importaba enviar_notificacion_email (notificaba solo al
# propio usuario); ahora se usa notificar_grupo, que avisa al otro coparental.
from shared.services import notificar_grupo

# ✔ CORRECTO: esta es la función real que sí debes usar
from core.models import registrar_actividad, Padre
from core.decorators import solo_padres, SoloPadresMixin


def _construir_contexto_resumen(request):
    """Arma el contexto de pagos/gastos/gráficos que comparten el resumen y el PDF."""
    pagos = Pago.objects.filter(grupo=request.grupo).order_by("-fecha")
    gastos = Gasto.objects.filter(grupo=request.grupo).order_by("-fecha")

    # ---------------------------
    # IDENTIDAD REAL DE LOS DOS PROGENITORES DEL GRUPO
    # ---------------------------
    # No existe un campo "rol" (padre/madre) en el modelo: antes se
    # etiquetaba "Padre" a quien coincidiera con request.user y "Madre" al
    # otro, así que la misma fila cambiaba de etiqueta según quién la
    # mirara. Ahora se usan los nombres reales de los dos usuarios.
    otro_perfil = (
        Padre.objects.filter(grupo=request.grupo)
        .exclude(user=request.user)
        .select_related("user")
        .first()
    )
    otro_usuario = otro_perfil.user if otro_perfil else None
    nombre_actual = Gasto.nombre_usuario(request.user)
    nombre_otro = Gasto.nombre_usuario(otro_usuario)

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

    # FILTRO POR QUIÉN PAGÓ (relativo a quien mira la página: "yo" / "el otro progenitor")
    if pagado_por == "yo":
        gastos = gastos.filter(pagado_por=request.user)
    elif pagado_por == "otro":
        gastos = gastos.exclude(pagado_por=request.user)

    # ---------------------------
    # BALANCE AUTOMÁTICO
    # ---------------------------
    # Solo los gastos aún pendientes generan saldo: si la deuda 50/50 ya
    # está finiquitada (con su comprobante), no debe seguir sumando al
    # balance porque ya se saldó entre las partes.
    balance = 0
    for g in gastos:
        if g.estado == "finiquitado":
            continue
        if g.pagado_por == request.user:
            balance += g.deuda_50_50
        elif g.pagado_por is not None:
            balance -= g.deuda_50_50

    # Versión absoluta del balance (quién debe a quién por nombre real), para
    # textos que deben leerse igual sin importar quién generó la página/PDF
    # (p. ej. el resumen para juzgado).
    if balance > 0:
        deudor_nombre, acreedor_nombre, monto_deuda = nombre_otro, nombre_actual, balance
    elif balance < 0:
        deudor_nombre, acreedor_nombre, monto_deuda = nombre_actual, nombre_otro, -balance
    else:
        deudor_nombre = acreedor_nombre = None
        monto_deuda = 0

    # ---------------------------
    # DATOS PARA EL GRÁFICO (orden cronológico ascendente)
    # ---------------------------
    gastos_con_fecha = sorted((g for g in gastos if g.fecha), key=lambda g: g.fecha)
    grafico_gastos = {
        "labels": [g.fecha.isoformat() for g in gastos_con_fecha],
        "data": [float(g.monto) for g in gastos_con_fecha],
    }

    # GRÁFICO COMPARATIVO ENTRE LOS DOS PROGENITORES (por nombre real)
    total_actual = (
        gastos.filter(pagado_por=request.user).aggregate(total=Sum("monto"))["total"]
        or 0
    )
    total_otro = (
        gastos.exclude(pagado_por=request.user).aggregate(total=Sum("monto"))["total"]
        or 0
    )

    grafico_comparativo = {
        "labels": [nombre_actual, nombre_otro],
        "data": [float(total_actual), float(total_otro)],
    }

    # GRÁFICO MENSUAL
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

    # GRÁFICO ANUAL
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

    # ---------------------------
    # NUEVO: TOTALES POR MES Y AÑO
    # ---------------------------
    totales_por_mes = gastos_por_mes
    totales_por_ano = gastos_por_ano

    # ---------------------------
    # TOTALES DE DEUDAS 50/50 YA SALDADAS, POR PERSONA REAL
    # ---------------------------
    # Antes se calculaba esto en la plantilla comparando
    # gasto.deuda_pagada_por == request.user, así que el mismo gasto
    # finiquitado terminaba sumando al "padre" o a la "madre" según quién
    # generara el PDF. Ahora se calcula una sola vez aquí, por identidad
    # real, y el resultado es el mismo sin importar quién lo mire.
    total_deuda_actual = 0
    total_deuda_otro = 0
    for g in gastos:
        if g.estado != "finiquitado":
            continue
        if g.deuda_pagada_por == request.user:
            total_deuda_actual += g.deuda_50_50
        elif g.deuda_pagada_por is not None:
            total_deuda_otro += g.deuda_50_50

    return {
        "pagos": pagos,
        "gastos": gastos,
        "balance": balance,
        "nombre_actual": nombre_actual,
        "nombre_otro": nombre_otro,
        "deudor_nombre": deudor_nombre,
        "acreedor_nombre": acreedor_nombre,
        "monto_deuda": monto_deuda,
        "total_deuda_actual": total_deuda_actual,
        "total_deuda_otro": total_deuda_otro,
        "hoy": date.today(),
        "grafico_gastos": grafico_gastos,
        "grafico_comparativo": grafico_comparativo,
        "grafico_mensual": grafico_mensual,
        "grafico_anual": grafico_anual,
        "totales_por_mes": totales_por_mes,
        "totales_por_ano": totales_por_ano,
    }


@solo_padres
def resumen(request):
    registrar_actividad(
        request.user,
        "ver_resumen_financiero",
        "El usuario ha visto el resumen financiero.",
    )

    contexto = _construir_contexto_resumen(request)
    return render(request, "finanzas/resumen.html", contexto)


@solo_padres
def exportar_pdf(request):
    """Genera un PDF del resumen financiero."""
    contexto = _construir_contexto_resumen(request)

    logo_path = finders.find("core/img/logo_pdf.png")
    if logo_path:
        with open(logo_path, "rb") as f:
            contexto["logo_base64"] = base64.b64encode(f.read()).decode("ascii")

    html_string = render_to_string(
        "finanzas/pdf_resumen.html", contexto, request=request
    )

    html = HTML(string=html_string)
    result = html.write_pdf()

    response_pdf = HttpResponse(result, content_type="application/pdf")
    response_pdf["Content-Disposition"] = "attachment; filename=resumen_financiero.pdf"

    return response_pdf


# ---------------------------------------------------------
# NUEVO: PDF PARA JUZGADO
# ---------------------------------------------------------
@solo_padres
def pdf_juzgado(request):
    contexto = _construir_contexto_resumen(request)

    logo_path = finders.find("core/img/logo_pdf.png")
    if logo_path:
        with open(logo_path, "rb") as f:
            contexto["logo_base64"] = base64.b64encode(f.read()).decode("ascii")

    html_string = render_to_string(
        "finanzas/pdf_juzgado.html", contexto, request=request
    )

    html = HTML(string=html_string)
    result = html.write_pdf()

    response_pdf = HttpResponse(result, content_type="application/pdf")
    response_pdf["Content-Disposition"] = "attachment; filename=resumen_juzgado.pdf"

    return response_pdf


# ---------------------------------------------------------
# NUEVO: PANTALLA PARA ELEGIR TIPO DE PDF
# ---------------------------------------------------------
@solo_padres
def elegir_pdf(request):
    return render(request, "finanzas/elegir_pdf.html")


@solo_padres
def nuevo_pago(request):
    """Registrar un nuevo pago de manutención."""
    if request.method == "POST":
        form = PagoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.grupo = request.grupo
            pago.creado_por = request.user

            if pago.comprobante_pdf:
                pago.estado = "pagado"

            pago.save()

            registrar_actividad(
                request.user, "crear_pago", f"Pago de {pago.monto} creado."
            )

            # NOTIF: solo notifica si se subió comprobante (antes se
            # notificaba siempre, y encima solo al propio usuario que lo creó).
            if pago.comprobante_pdf:
                notificar_grupo(
                    request.user,
                    "Comprobante de pago subido",
                    f"{request.user.get_full_name() or request.user.username} "
                    f"subió un comprobante de pago de {pago.monto}€ con fecha {pago.fecha}.",
                )
            return redirect(reverse("finanzas:resumen"))
    else:
        form = PagoForm()
    return render(request, "finanzas/pago_form.html", {"form": form})


@solo_padres
def marcar_pagado(request, pk):
    """Marcar un pago como pagado."""
    pago = get_object_or_404(Pago, pk=pk, grupo=request.grupo)
    pago.estado = "pagado"
    pago.save()

    registrar_actividad(
        request.user, "marcar_pago_pagado", f"Pago ID {pago.id} marcado como pagado."
    )
    # NOTIF: antes se enviaba un email aquí (a sí mismo). Se quitó porque
    # esta acción no sube comprobante nuevo, no es una de las 4 acciones de
    # interés (crear evento, crear gasto, comprobante de pago, comprobante
    # de deuda) — sigue quedando en el historial de auditoría, sin correo.

    return redirect(reverse("finanzas:resumen"))


@solo_padres
def nuevo_gasto(request):
    """Registrar un nuevo gasto compartido 50/50."""
    if request.method == "POST":
        form = GastoForm(request.POST, request.FILES)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.grupo = request.grupo
            gasto.pagado_por = request.user

            gasto.save()

            registrar_actividad(
                request.user, "crear_gasto", f"Gasto de {gasto.monto} creado."
            )

            # NOTIF: reemplaza el email que antes solo se mandaba al propio
            # usuario que creó el gasto; ahora avisa al otro coparental.
            notificar_grupo(
                request.user,
                "Nuevo gasto compartido",
                f"{request.user.get_full_name() or request.user.username} "
                f"registró un gasto de {gasto.concepto} por {gasto.monto}€.",
            )

            return redirect(reverse("finanzas:resumen"))
    else:
        form = GastoForm()
    return render(request, "finanzas/gasto_form.html", {"form": form})


@solo_padres
def pagar_deuda(request, pk):
    """
    Registrar el pago de la deuda 50/50 de un gasto compartido:
    - Deuda pagada por: request.user
    - Comprobante de la transferencia
    - Estado: finiquitado
    - Validación: el monto pagado debe ser >= deuda exacta
    """
    gasto = get_object_or_404(Gasto, pk=pk, grupo=request.grupo)

    if request.method == "POST":
        archivo = request.FILES.get("comprobante_deuda")
        monto_pagado = request.POST.get("monto_deuda_pagada")

        try:
            monto_pagado = float(monto_pagado)
        except:
            messages.error(request, "Monto inválido.")
            return redirect("finanzas:pagar_deuda", pk=pk)

        if monto_pagado < float(gasto.deuda_50_50):
            messages.error(
                request,
                f"El monto pagado ({monto_pagado}€) es inferior a la deuda exacta ({gasto.deuda_50_50}€).",
            )
            return redirect("finanzas:pagar_deuda", pk=pk)

        gasto.comprobante_deuda = archivo
        gasto.deuda_pagada_por = request.user
        gasto.estado = "finiquitado"
        gasto.save()

        registrar_actividad(
            request.user,
            "pagar_deuda",
            f"Deuda del gasto ID {gasto.id} saldada con {monto_pagado}€.",
        )

        # NOTIF: esta vista antes no enviaba ningún correo; se agregó porque
        # es el comprobante de "la otra parte" del gasto (la deuda 50/50).
        notificar_grupo(
            request.user,
            "Comprobante de deuda saldada",
            f"{request.user.get_full_name() or request.user.username} "
            f"subió el comprobante de la deuda saldada de {gasto.concepto} "
            f"por {monto_pagado}€.",
        )

        return redirect("finanzas:resumen")

    return render(request, "finanzas/pagar_deuda.html", {"gasto": gasto})


# --- EDITAR PAGO ---
class PagoUpdateView(SoloPadresMixin, UpdateView):
    model = Pago
    form_class = PagoForm
    template_name = "finanzas/editar_pago.html"
    success_url = reverse_lazy("finanzas:resumen")

    def get_queryset(self):
        return super().get_queryset().filter(grupo=self.grupo)

    def form_valid(self, form):
        registrar_actividad(
            self.request.user, "editar_pago", f"Pago ID {self.object.id} editado."
        )
        return super().form_valid(form)


# --- ELIMINAR PAGO ---
class PagoDeleteView(SoloPadresMixin, DeleteView):
    model = Pago
    template_name = "finanzas/eliminar_pago.html"
    success_url = reverse_lazy("finanzas:resumen")

    def get_queryset(self):
        return super().get_queryset().filter(grupo=self.grupo)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        registrar_actividad(
            request.user, "eliminar_pago", f"Pago ID {obj.id} eliminado."
        )
        return super().delete(request, *args, **kwargs)


# --- EDITAR GASTO ---
class GastoUpdateView(SoloPadresMixin, UpdateView):
    model = Gasto
    form_class = GastoForm
    template_name = "finanzas/editar_gasto.html"
    success_url = reverse_lazy("finanzas:resumen")

    def get_queryset(self):
        return super().get_queryset().filter(grupo=self.grupo)

    def form_valid(self, form):
        registrar_actividad(
            self.request.user, "editar_gasto", f"Gasto ID {self.object.id} editado."
        )
        return super().form_valid(form)


# --- ELIMINAR GASTO ---
class GastoDeleteView(SoloPadresMixin, DeleteView):
    model = Gasto
    template_name = "finanzas/eliminar_gasto.html"
    success_url = reverse_lazy("finanzas:resumen")

    def get_queryset(self):
        return super().get_queryset().filter(grupo=self.grupo)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        registrar_actividad(
            request.user, "eliminar_gasto", f"Gasto ID {obj.id} eliminado."
        )
        return super().delete(request, *args, **kwargs)
