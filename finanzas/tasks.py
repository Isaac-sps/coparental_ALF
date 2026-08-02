from celery import shared_task
from django.utils import timezone
from shared.services import enviar_notificacion_email
from .models import Pago

@shared_task
def revisar_pagos_pendientes():
    """
    Revisa si hay pagos pendientes y envía notificaciones automáticas.
    """
    hoy = timezone.now().date()
    pendientes = Pago.objects.filter(estado="pendiente")

    for pago in pendientes:
        if pago.creado_por and pago.creado_por.email:
            enviar_notificacion_email(
                destinatario=pago.creado_por.email,
                asunto="Pago pendiente",
                mensaje=f"El pago del {pago.fecha} sigue pendiente."
            )
