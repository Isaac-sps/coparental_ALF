"""URLs de la app core."""

from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("perfil/", views.perfil, name="perfil"),
    path("historial/", views.historial_actividad, name="historial"),
    path("invitar/", views.invitar_coparental, name="invitar"),
    path(
        "invitacion/aceptar/<uuid:token>/",
        views.aceptar_invitacion,
        name="aceptar_invitacion",
    ),
    path("grupo/", views.panel_grupo, name="panel_grupo"),
    path("externos/", views.panel_externos, name="panel_externos"),
    path("externo/invitar/", views.invitar_externo, name="invitar_externo"),
    path(
        "externo/invitacion/aceptar/<uuid:token>/",
        views.aceptar_invitacion_externo,
        name="aceptar_invitacion_externo",
    ),
    path("externo/panel/", views.panel_profesional, name="panel_profesional"),
    path("canal-alf/", views.canal_alf, name="canal_alf"),
    path("canal-alf/subir/", views.subir_documento_rol, name="subir_documento_rol"),
    path("canal/<int:canal_id>/", views.canal_rol, name="canal_rol"),
    path(
        "canal/<int:canal_id>/documento/nuevo/",
        views.subir_documento_canal,
        name="subir_documento_canal",
    ),
    path(
        "documento/<int:doc_id>/descargar/",
        views.descargar_documento_canal,
        name="descargar_documento_canal",
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
