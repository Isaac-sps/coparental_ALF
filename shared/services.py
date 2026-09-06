from django.core.mail import send_mail

def enviar_notificacion_email(destinatario, asunto, mensaje):
    """
    Servicio centralizado para enviar emails.
    Permite que cualquier app del proyecto envíe notificaciones.
    """
    if not destinatario:
        return  # Evita errores si el usuario no tiene email

    send_mail(
        subject=asunto,
        message=mensaje,
        from_email="no-reply@coparental.com",
        recipient_list=[destinatario],
        fail_silently=False,
    )


# NOTIF: nuevo helper (2026-09) — punto único desde el que las vistas de
# interés (crear evento, crear gasto, subir comprobante de pago/deuda)
# disparan el correo al grupo. No se usa en vistas de solo lectura/edición.
def notificar_grupo(actor, asunto, mensaje):
    """
    Notifica por email a los demás miembros del grupo coparental del actor
    (no a él mismo) sobre una acción importante, respetando la preferencia
    individual Padre.notificaciones_email de cada destinatario.
    """
    from core.models import Padre
    from core.tasks import enviar_notificacion_grupo

    padre = Padre.objects.filter(user=actor).first()
    if not padre or not padre.grupo:
        return

    enviar_notificacion_grupo.delay(padre.grupo.id, asunto, mensaje, excluir_user_id=actor.id)
