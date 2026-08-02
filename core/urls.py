"""URLs de la app core."""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("historial/", views.historial_actividad, name="historial"),
    path("invitar/", views.invitar_coparental, name="invitar"),
    path("grupo/", views.panel_grupo, name="panel_grupo"),
    path(
        "externo/solicitar/",
        views.solicitar_acceso_externo,
        name="solicitar_acceso_externo",
    ),
    path(
        "externo/aprobar/padre/<int:externo_id>/",
        views.aprobar_externo_padre,
        name="aprobar_externo_padre",
    ),
    path(
        "externo/aprobar/madre/<int:externo_id>/",
        views.aprobar_externo_madre,
        name="aprobar_externo_madre",
    ),
    path(
        "externo/revocar/<int:externo_id>/",
        views.revocar_externo,
        name="revocar_externo",
    ),
]
