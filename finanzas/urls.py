"""URLs de la app finanzas."""

from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    path("", views.resumen, name="resumen"),
    path("pago/nuevo/", views.nuevo_pago, name="nuevo_pago"),
    path("pago/<int:pk>/pagado/", views.marcar_pagado, name="marcar_pagado"),
    path("gasto/nuevo/", views.nuevo_gasto, name="nuevo_gasto"),
    # --- NUEVAS RUTAS PARA EDITAR Y ELIMINAR ---
    path("pago/<int:pk>/editar/", views.PagoUpdateView.as_view(), name="editar_pago"),
    path(
        "pago/<int:pk>/eliminar/", views.PagoDeleteView.as_view(), name="eliminar_pago"
    ),
    path(
        "gasto/<int:pk>/editar/", views.GastoUpdateView.as_view(), name="editar_gasto"
    ),
    path(
        "gasto/<int:pk>/eliminar/",
        views.GastoDeleteView.as_view(),
        name="eliminar_gasto",
    ),
    path("exportar/pdf/", views.exportar_pdf, name="exportar_pdf"),
]
