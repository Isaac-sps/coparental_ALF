from celery import shared_task
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


@shared_task
def enviar_invitacion_email(email, token):
    enlace = f"{settings.SITE_URL}{reverse('core:aceptar_invitacion', args=[token])}"

    asunto = "Invitación a tu grupo coparental · CoparentaL ALF"
    mensaje = (
        "Has sido invitado a unirte a un grupo coparental en CoparentaL ALF, "
        "la herramienta para organizar el calendario, los gastos compartidos "
        "y la comunicación de la coparentalidad.\n\n"
        f"Para unirte, abre este enlace desde tu celular, tablet o computador "
        f"(con este mismo correo abierto no hace falta nada más):\n{enlace}\n\n"
        "Si aún no tienes cuenta, el enlace te llevará a crear una en segundos. "
        "Si ya tienes cuenta, solo inicia sesión y quedarás unido al grupo automáticamente.\n\n"
        "Si no esperabas este mensaje, puedes ignorarlo con confianza.\n\n"
        "— El equipo de CoparentaL ALF"
    )

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


@shared_task
def enviar_invitacion_externo_email(email, token, rol_display):
    enlace = f"{settings.SITE_URL}{reverse('core:aceptar_invitacion_externo', args=[token])}"

    asunto = f"Invitación como {rol_display} · CoparentaL ALF"
    mensaje = (
        f"Has sido invitado/a a colaborar como {rol_display} en un grupo "
        "coparental de CoparentaL ALF.\n\n"
        f"Al aceptar tendrás tu propio canal de {rol_display}: mensajes e "
        "informes/documentos relacionados con tu rol, separados del resto "
        "del grupo. El acceso se activa una vez que ambos progenitores lo "
        "aprueben.\n\n"
        f"Para unirte, abre este enlace desde tu celular, tablet o computador:\n{enlace}\n\n"
        "Si aún no tienes cuenta, el enlace te llevará a crear una en segundos.\n\n"
        "Si no esperabas este mensaje, puedes ignorarlo con confianza.\n\n"
        "— El equipo de CoparentaL ALF"
    )

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


# NOTIF: firma cambiada de (grupo_id, mensaje) a (grupo_id, asunto, mensaje,
# excluir_user_id) para poder: 1) mandar un asunto propio por tipo de evento
# (antes era fijo "Nueva actividad..."), 2) filtrar destinatarios por su
# preferencia Padre.notificaciones_email, y 3) excluir a quien hizo la acción
# (antes se notificaba también a sí mismo).
@shared_task
def enviar_notificacion_grupo(grupo_id, asunto, mensaje, excluir_user_id=None):
    from core.models import GrupoCoparental

    grupo = GrupoCoparental.objects.get(id=grupo_id)
    miembros = grupo.miembros.filter(notificaciones_email=True)  # NOTIF: respeta el opt-out
    if excluir_user_id:
        miembros = miembros.exclude(user_id=excluir_user_id)  # NOTIF: no notificar al actor

    emails = [padre.user.email for padre in miembros if padre.user.email]

    if not emails:
        return

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        emails,
        fail_silently=False,
    )
