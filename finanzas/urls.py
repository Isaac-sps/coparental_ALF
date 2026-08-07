"""URLs de la app finanzas."""

from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    # --- RESUMEN ---
    path("", views.resumen, name="resumen"),

    # --- PAGOS ---
    path("pago/nuevo/", views.nuevo_pago, name="nuevo_pago"),
    path("pago/<int:pk>/pagado/", views.marcar_pagado, name="marcar_pagado"),
    path("pago/<int:pk>/editar/", views.PagoUpdateView.as_view(), name="editar_pago"),
    path("pago/<int:pk>/eliminar/", views.PagoDeleteView.as_view(), name="eliminar_pago"),

    # --- GASTOS ---
    path("gasto/nuevo/", views.nuevo_gasto, name="nuevo_gasto"),
    path("gasto/<int:pk>/editar/", views.GastoUpdateView.as_view(), name="editar_gasto"),
    path("gasto/<int:pk>/eliminar/", views.GastoDeleteView.as_view(), name="eliminar_gasto"),

    # --- DEUDA 50/50 ---
    path("gasto/<int:pk>/pagar-deuda/", views.pagar_deuda, name="pagar_deuda"),

    # --- PDF NORMAL ---
    path("exportar/pdf/", views.exportar_pdf, name="exportar_pdf"),

    # --- NUEVO: PANTALLA PARA ELEGIR TIPO DE PDF ---
    path("pdf/elegir/", views.elegir_pdf, name="elegir_pdf"),

    # --- NUEVO: PDF PARA JUZGADO ---
    path("pdf/juzgado/", views.pdf_juzgado, name="pdf_juzgado"),
]
