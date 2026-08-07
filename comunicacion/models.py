"""Modelos para chat interno entre padre y madre.

Los archivos compartidos ya no viven aquí: se subieron a Canal ALF
(core.DocumentoCanal), clasificados por rol, para que cada documento quede
en la biblioteca del profesional al que corresponde (o en "General").
"""
from django.db import models
from django.contrib.auth.models import User


class Mensaje(models.Model):
    """Mensaje de chat interno entre los dos padres de un grupo coparental."""
    grupo = models.ForeignKey(
        "core.GrupoCoparental", on_delete=models.CASCADE, related_name="mensajes_internos"
    )
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensajes")
    contenido = models.TextField("Contenido")
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    def __str__(self):
        return f"{self.autor}: {self.contenido[:30]}"
