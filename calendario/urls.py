"""URLs de la app calendario."""
from django.urls import path
from . import views

app_name = "calendario"

urlpatterns = [
    path("", views.calendario_mensual, name="lista"),
    path("historial/", views.historial_eventos, name="historial"),
    path("nuevo/", views.crear_evento, name="nuevo"),
    path("<int:pk>/editar/", views.editar_evento, name="editar"),
    path("eliminar/<int:pk>/", views.eliminar_evento, name="eliminar"),
]
