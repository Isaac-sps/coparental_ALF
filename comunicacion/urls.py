from django.urls import path
from . import views
"""URLs de la app comunicación."""
from django.urls import path
from . import views

app_name = "comunicacion"

urlpatterns = [
    path("", views.chat, name="chat"),
    path("archivo/nuevo/", views.subir_archivo, name="subir_archivo"),
]

