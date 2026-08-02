"""Modelos para chat interno y archivos compartidos."""
from django.db import models
from django.contrib.auth.models import User


class Mensaje(models.Model):
    """Mensaje de chat interno entre los dos padres."""
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensajes")
    contenido = models.TextField("Contenido")
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    def __str__(self):
        return f"{self.autor}: {self.contenido[:30]}"


class ArchivoCompartido(models.Model):
    """Archivos compartidos en la comunicación interna."""
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="archivos_compartidos")
    archivo = models.FileField("Archivo", upload_to="comunicacion/")
    descripcion = models.CharField("Descripción", max_length=255, blank=True)
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    def __str__(self):
        return f"{self.descripcion or self.archivo.name}"


# Create your models here.
