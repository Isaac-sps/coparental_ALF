from celery import shared_task
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


@shared_task
def enviar_invitacion_email(email, token):
    enlace = f"{settings.SITE_URL}{reverse('core:aceptar_invitacion', args=[token])}"

    asunto = "Invitación para unirte al grupo coparental"
    mensaje = (
        "Has sido invitado a un grupo coparental.\n\n"
        f"Para unirte, haz clic en el siguiente enlace:\n{enlace}\n\n"
        "Si no esperabas este mensaje, puedes ignorarlo."
    )

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


@shared_task
def enviar_notificacion_grupo(grupo_id, mensaje):
    from core.models import GrupoCoparental

    grupo = GrupoCoparental.objects.get(id=grupo_id)
    emails = [padre.user.email for padre in grupo.miembros.all() if padre.user.email]

    if not emails:
        return

    send_mail(
        "Nueva actividad en el grupo coparental",
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        emails,
        fail_silently=False,
    )
