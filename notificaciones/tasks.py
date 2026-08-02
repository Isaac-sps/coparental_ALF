"""Tareas de Celery para enviar recordatorios y alertas."""
from datetime import timedelta, date
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from calendario.models import Evento
from finanzas.models import Pago
from django.contrib.auth.models import User


@shared_task
def enviar_recordatorio_visita():
    """
    Envía email 2 días antes de la visita.
    Nota: Para WhatsApp real se necesitaría integrar una API externa (normalmente de pago),
    así que aquí solo usamos email para mantener coste cero.
    """
    hoy = date.today()
    objetivo = hoy + timedelta(days=2)

    eventos = Evento.objects.filter(fecha_inicio=objetivo, tipo="visita")
    if not eventos.exists():
        return

    # Obtenemos todos los usuarios (los dos padres)
    padres = User.objects.all()
    for evento in eventos:
        asunto = "Recordatorio de visita"
        mensaje = (
            f"Hay una visita programada para el día {evento.fecha_inicio} "
            f"en el punto de encuentro: {evento.get_punto_encuentro_display()}."
        )
        for padre in padres:
            if padre.email:
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [padre.email],
                    fail_silently=True,
                )


@shared_task
def enviar_alerta_pago_pendiente():
    """
    Envía email de alerta de pago pendiente de manutención.
    Se puede programar para que se ejecute diariamente.
    """
    hoy = date.today()
    pagos_pendientes = Pago.objects.filter(estado="pendiente", fecha__lte=hoy)

    if not pagos_pendientes.exists():
        return

    padres = User.objects.all()
    for pago in pagos_pendientes:
        asunto = "Alerta de pago pendiente"
        mensaje = (
            f"El pago de manutención de {pago.monto}€ con fecha {pago.fecha} "
            f"sigue pendiente."
        )
        for padre in padres:
            if padre.email:
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [padre.email],
                    fail_silently=True,
                )
