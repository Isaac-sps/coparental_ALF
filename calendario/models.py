"""Modelos para eventos de calendario (visitas, vacaciones)."""
from django.db import models
from django.utils.dateformat import format as date_format


class Evento(models.Model):
    """Evento de calendario: visitas y vacaciones."""
    TIPO_CHOICES = [
        ("visita", "Visita"),
        ("vacacion", "Vacaciones"),
        ("cumpleanos", "Cumpleaños"),
        ("viaje", "Viajes"),
        ("aniversario", "Aniversarios"),
        ("boda", "Bodas"),
        ("comida_familiar", "Comida Familiar"),
        ("graduacion", "Graduación"),
        ("bautizo_comunion", "Bautizo/Comunión"),
        ("extranjeria", "Extranjería"),
    ]

    grupo = models.ForeignKey(
        "core.GrupoCoparental", on_delete=models.CASCADE, related_name="eventos"
    )
    tipo = models.CharField("Tipo de evento", max_length=20, choices=TIPO_CHOICES)
    fecha_inicio = models.DateField("Fecha de inicio")
    fecha_fin = models.DateField("Fecha de fin")
    punto_encuentro = models.CharField(
        "Punto de encuentro",
        max_length=255,
        help_text="Describe el sitio donde se va a gestionar/concertar la visita.",
    )
    notas = models.TextField("Notas", blank=True)

    def __str__(self):
        return f"{self.get_tipo_display()} del {self.fecha_inicio} al {self.fecha_fin}"

    @property
    def mes_label(self):
        """Mes y año de la fecha de inicio, para agrupar eventos (ej. 'Agosto 2026')."""
        return date_format(self.fecha_inicio, "F Y").capitalize()

