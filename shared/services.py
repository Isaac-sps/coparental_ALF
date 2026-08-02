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
