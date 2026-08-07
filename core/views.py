"""Vistas de la app core: dashboard y perfil."""

from datetime import date
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, FileResponse
from django.shortcuts import render, redirect

# ⭐ AGREGADO: Necesario para aceptar invitaciones y obtener objetos
from django.shortcuts import get_object_or_404

# ⭐ AGREGADO: Para mostrar mensajes al usuario
from django.contrib import messages

# ⭐ AGREGADO: Para manejar usuarios y login si lo necesitas en el futuro
from django.contrib.auth.models import User

from django.urls import reverse
from calendario.models import Evento
from finanzas.models import Pago, Gasto
from .forms import PadreForm, UsuarioForm, MensajeCanalForm, DocumentoCanalForm

# ⭐ AGREGADO: Nuevos modelos que creaste (GrupoCoparental + InvitacionCoparental)
from .models import (
    MiembroExterno,
    Padre,
    RegistroActividad,
    GrupoCoparental,
    InvitacionCoparental,
    InvitacionExterno,
    CanalRol,
    DocumentoCanal,
    MensajeCanal,
    ROLES_CANAL,
    usuario_tiene_acceso_canal,
)
from .models import registrar_actividad
from .tasks import enviar_invitacion_email, enviar_invitacion_externo_email
from .decorators import solo_padres


@login_required
def dashboard(request):
    """Dashboard principal: calendario del mes, próximos eventos y alertas de pago
    del grupo del usuario (nunca de otro grupo)."""
    padre = Padre.objects.filter(user=request.user).first()
    if padre is None:
        if MiembroExterno.objects.filter(user=request.user).exists():
            return redirect("core:panel_profesional")
        return redirect("core:perfil")

    grupo = padre.grupo
    hoy = date.today()

    # Próximos eventos (visitas y vacaciones con fecha_inicio >= hoy, en orden)
    proximas_visitas = Evento.objects.filter(
        grupo=grupo, fecha_inicio__gte=hoy
    ).order_by("fecha_inicio")

    # Pagos pendientes (manutención)
    pagos_pendientes = Pago.objects.filter(
        grupo=grupo, estado="pendiente"
    ).order_by("fecha")

    # Gastos recientes
    gastos_recientes = Gasto.objects.filter(grupo=grupo).order_by("-fecha_creacion")[:5]

    context = {
        "hoy": hoy,
        "proximas_visitas": proximas_visitas,
        "pagos_pendientes": pagos_pendientes,
        "gastos_recientes": gastos_recientes,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def perfil(request):
    """Vista para editar el perfil del padre."""
    if not Padre.objects.filter(user=request.user).exists():
        if MiembroExterno.objects.filter(user=request.user).exists():
            return redirect("core:panel_profesional")

    padre, _ = Padre.objects.get_or_create(user=request.user)

    # ⭐ AGREGADO: Crear automáticamente un grupo coparental si no existe
    if padre.grupo is None:
        grupo = GrupoCoparental.objects.create(
            nombre=f"Grupo de {request.user.username}"
        )
        padre.grupo = grupo
        padre.save()

    if request.method == "POST":
        user_form = UsuarioForm(request.POST, instance=request.user)
        form = PadreForm(request.POST, request.FILES, instance=padre)
        if user_form.is_valid() and form.is_valid():
            user_form.save()
            form.save()
            registrar_actividad(request.user, "Perfil actualizado")
            return redirect(reverse("core:dashboard"))
    else:
        user_form = UsuarioForm(instance=request.user)
        form = PadreForm(instance=padre)

    otros_miembros = padre.grupo.miembros.exclude(id=padre.id)

    return render(
        request,
        "core/perfil.html",
        {
            "form": form,
            "user_form": user_form,
            "padre": padre,
            "otros_miembros": otros_miembros,
        },
    )


@login_required
def historial_actividad(request):
    """Muestra el historial de actividad del grupo coparental (ambos padres)."""
    if not Padre.objects.filter(user=request.user).exists():
        if MiembroExterno.objects.filter(user=request.user).exists():
            return redirect("core:panel_profesional")

    padre, _ = Padre.objects.get_or_create(user=request.user)

    if padre.grupo:
        actividades = RegistroActividad.objects.filter(
            usuario__perfil_padre__grupo=padre.grupo
        ).order_by("-fecha")
    else:
        actividades = RegistroActividad.objects.filter(usuario=request.user).order_by(
            "-fecha"
        )

    return render(
        request,
        "core/historial_actividad.html",
        {"actividades": actividades},
    )


# ⭐⭐⭐ NUEVO BLOQUE COMPLETO — INVITAR COPARENTAL ⭐⭐⭐
@solo_padres
def invitar_coparental(request):
    """Permite enviar una invitación al otro progenitor."""
    padre = Padre.objects.get(user=request.user)

    if padre.grupo is None:
        messages.error(request, "No tienes un grupo coparental asignado.")
        return redirect("core:perfil")

    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            messages.error(request, "Debes indicar un correo electrónico.")
        else:
            invitacion = InvitacionCoparental.objects.create(
                grupo=padre.grupo,
                email=email,
            )
            # ⭐ NUEVO
            enviar_invitacion_email.delay(email, str(invitacion.token))

            registrar_actividad(
                request.user, "Invitación enviada", f"Invitación enviada a {email}"
            )

            messages.success(request, "Invitación creada y enviada por email.")
            return redirect("core:dashboard")

    return render(request, "core/invitar_coparental.html")


# ⭐⭐⭐ NUEVO BLOQUE COMPLETO — ACEPTAR INVITACIÓN ⭐⭐⭐
def aceptar_invitacion(request, token):
    """Permite que el otro progenitor acepte la invitación y se una al grupo.

    No usa @login_required: si quien hace clic en el enlace del correo aún no
    tiene cuenta, lo mandamos a iniciar sesión / crear cuenta con el email de
    la invitación precargado y `next` apuntando de vuelta aquí, para que al
    terminar quede unido al grupo automáticamente sin tener que repetir el paso.
    """
    invitacion = get_object_or_404(InvitacionCoparental, token=token)

    if invitacion.aceptada:
        messages.info(request, "Esta invitación ya fue utilizada.")
        return redirect("core:dashboard" if request.user.is_authenticated else "account_login")

    if not request.user.is_authenticated:
        login_url = reverse("account_login")
        return redirect(f"{login_url}?next={request.path}&email={invitacion.email}")

    padre, _ = Padre.objects.get_or_create(user=request.user)
    padre.grupo = invitacion.grupo
    padre.save()

    invitacion.aceptada = True
    invitacion.save()

    if request.user.email and request.user.email.lower() != invitacion.email.lower():
        messages.info(
            request, f"Nota: esta invitación fue enviada originalmente a {invitacion.email}."
        )

    registrar_actividad(request.user, "Invitación aceptada")

    messages.success(request, "Te has unido al grupo coparental.")
    return redirect("core:dashboard")


# Creacion de vista del Panel del Grupo
@solo_padres
def panel_grupo(request):
    """Panel de administración del grupo coparental."""
    padre = Padre.objects.get(user=request.user)

    if padre.grupo is None:
        messages.error(request, "No tienes un grupo coparental asignado.")
        return redirect("core:perfil")

    grupo = padre.grupo

    miembros = grupo.miembros.all()
    invitaciones = grupo.invitaciones.all()
    historial = RegistroActividad.objects.filter(
        usuario__perfil_padre__grupo=grupo
    ).order_by("-fecha")

    context = {
        "grupo": grupo,
        "miembros": miembros,
        "invitaciones": invitaciones,
        "historial": historial,
    }

    return render(request, "core/panel_grupo.html", context)


# Creación de un Panel Externo para la visualización a los profesionales requeridos por sección módular
@solo_padres
def panel_externos(request):
    padre = Padre.objects.get(user=request.user)

    if padre.grupo is None:
        return HttpResponseForbidden()

    externos = list(padre.grupo.externos.all())
    invitaciones_externos = padre.grupo.invitaciones_externos.filter(aceptada=False)

    for externo in externos:
        if externo.autorizado():
            canal, _ = CanalRol.objects.get_or_create(
                grupo=padre.grupo, rol=externo.rol
            )
            externo.canal_id = canal.id

    return render(
        request,
        "core/panel_externos.html",
        {"externos": externos, "invitaciones_externos": invitaciones_externos},
    )


# Invitar a un profesional externo (médico, abogado, etc.) por correo
@solo_padres
def invitar_externo(request):
    """Permite a un padre/madre invitar a un profesional a un rol del grupo."""
    padre = Padre.objects.get(user=request.user)

    if padre.grupo is None:
        messages.error(request, "No tienes un grupo coparental asignado.")
        return redirect("core:perfil")

    if request.method == "POST":
        email = request.POST.get("email")
        rol = request.POST.get("rol")
        roles_validos = dict(MiembroExterno.ROLES)

        if not email or rol not in roles_validos:
            messages.error(request, "Debes indicar un correo y un rol válido.")
        else:
            invitacion = InvitacionExterno.objects.create(
                grupo=padre.grupo,
                email=email,
                rol=rol,
                invitado_por=request.user,
            )
            enviar_invitacion_externo_email.delay(
                email, str(invitacion.token), roles_validos[rol]
            )

            registrar_actividad(
                request.user,
                "Invitación a profesional enviada",
                f"Invitación enviada a {email} como {roles_validos[rol]}.",
            )

            messages.success(request, "Invitación creada y enviada por email.")
            return redirect("core:panel_externos")

    return render(
        request, "core/invitar_externo.html", {"roles": MiembroExterno.ROLES}
    )


def aceptar_invitacion_externo(request, token):
    """El profesional acepta la invitación; queda pendiente de aprobación de ambos padres."""
    invitacion = get_object_or_404(InvitacionExterno, token=token)

    if invitacion.aceptada:
        messages.info(request, "Esta invitación ya fue utilizada.")
        return redirect("core:dashboard" if request.user.is_authenticated else "account_login")

    if not request.user.is_authenticated:
        login_url = reverse("account_login")
        return redirect(f"{login_url}?next={request.path}&email={invitacion.email}")

    # Un usuario solo puede tener un rol externo activo a la vez (OneToOne).
    externo, _ = MiembroExterno.objects.update_or_create(
        user=request.user,
        defaults={
            "grupo": invitacion.grupo,
            "rol": invitacion.rol,
            "autorizado_por_padre": False,
            "autorizado_por_madre": False,
            "fecha_autorizacion": None,
        },
    )

    invitacion.aceptada = True
    invitacion.save()

    registrar_actividad(
        request.user,
        "Invitación de profesional aceptada",
        f"Se unió como {externo.get_rol_display()}, pendiente de aprobación.",
    )

    messages.success(
        request,
        "Has aceptado la invitación. El acceso se activará cuando ambos "
        "progenitores lo aprueben.",
    )
    return redirect("core:panel_profesional")


@login_required
def panel_profesional(request):
    """Vista de aterrizaje para un profesional externo: solo su propio canal de rol."""
    externo = get_object_or_404(MiembroExterno, user=request.user)

    if not externo.autorizado():
        return render(request, "core/panel_profesional.html", {"externo": externo})

    canal, _ = CanalRol.objects.get_or_create(grupo=externo.grupo, rol=externo.rol)
    return redirect("core:canal_rol", canal_id=canal.id)


@login_required
def canal_rol(request, canal_id):
    """Canal de mensajes + documentos de un rol: lo ven los padres del grupo y
    los profesionales autorizados en ese mismo rol."""
    canal = get_object_or_404(CanalRol, id=canal_id)

    if not usuario_tiene_acceso_canal(request.user, canal):
        return HttpResponseForbidden("No tienes acceso a este canal.")

    if request.method == "POST":
        form = MensajeCanalForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.canal = canal
            mensaje.autor = request.user
            mensaje.save()
            return redirect("core:canal_rol", canal_id=canal.id)
    else:
        form = MensajeCanalForm()

    context = {
        "canal": canal,
        "mensajes": canal.mensajes.select_related("autor"),
        "documentos": canal.documentos.select_related("subido_por"),
        "form": form,
        "documento_form": DocumentoCanalForm(),
    }
    return render(request, "core/canal_rol.html", context)


@login_required
def subir_documento_canal(request, canal_id):
    """Sube un documento/informe al canal de un rol."""
    canal = get_object_or_404(CanalRol, id=canal_id)

    if not usuario_tiene_acceso_canal(request.user, canal):
        return HttpResponseForbidden("No tienes acceso a este canal.")

    if request.method == "POST":
        form = DocumentoCanalForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.canal = canal
            documento.subido_por = request.user
            documento.save()

            # El comentario queda también en el historial de mensajes del
            # canal, junto al documento (no solo como descripción suelta).
            if documento.descripcion:
                MensajeCanal.objects.create(
                    canal=canal, autor=request.user, contenido=documento.descripcion
                )

            registrar_actividad(
                request.user,
                "Documento subido",
                f"{documento.titulo} en el canal de {canal.get_rol_display()}.",
            )
            messages.success(request, "Documento subido correctamente.")

    return redirect("core:canal_rol", canal_id=canal.id)


@solo_padres
def canal_alf(request):
    """Biblioteca de documentos y mensajes clasificados por rol (Canal ALF).
    Punto de entrada principal para padre/madre: acceso a todos los roles de
    su grupo, incluyendo "General" para lo que no es de ningún profesional."""
    canales = []
    for valor, etiqueta in ROLES_CANAL:
        canal, _ = CanalRol.objects.get_or_create(grupo=request.grupo, rol=valor)
        canales.append(canal)

    context = {
        "canales": canales,
        "roles": ROLES_CANAL,
    }
    return render(request, "core/canal_alf.html", context)


@solo_padres
def subir_documento_rol(request):
    """Subida rápida desde el hub de Canal ALF: se elige el rol destino aquí
    mismo, sin tener que entrar primero a ese canal."""
    if request.method == "POST":
        form = DocumentoCanalForm(request.POST, request.FILES)
        rol = request.POST.get("rol")
        roles_validos = dict(ROLES_CANAL)

        if rol not in roles_validos:
            messages.error(request, "Debes elegir un rol válido.")
            return redirect("core:canal_alf")

        canal, _ = CanalRol.objects.get_or_create(grupo=request.grupo, rol=rol)

        if form.is_valid():
            documento = form.save(commit=False)
            documento.canal = canal
            documento.subido_por = request.user
            documento.save()

            if documento.descripcion:
                MensajeCanal.objects.create(
                    canal=canal, autor=request.user, contenido=documento.descripcion
                )

            registrar_actividad(
                request.user,
                "Documento subido",
                f"{documento.titulo} en el canal de {canal.get_rol_display()}.",
            )
            messages.success(
                request, f"Documento guardado en {canal.get_rol_display()}."
            )
        else:
            messages.error(request, "Revisa el formulario: falta el título o el archivo.")

    return redirect("core:canal_alf")


@login_required
def descargar_documento_canal(request, doc_id):
    """Sirve el archivo de un documento solo si el usuario tiene acceso al canal."""
    documento = get_object_or_404(DocumentoCanal, id=doc_id)

    if not usuario_tiene_acceso_canal(request.user, documento.canal):
        return HttpResponseForbidden("No tienes acceso a este documento.")

    return FileResponse(
        documento.archivo.open("rb"),
        as_attachment=True,
        filename=documento.archivo.name.rsplit("/", 1)[-1],
    )


# Aprobación del Padre
@solo_padres
def aprobar_externo_padre(request, externo_id):
    """El padre aprueba la solicitud de acceso del profesional externo."""
    padre = Padre.objects.get(user=request.user)

    externo = get_object_or_404(MiembroExterno, id=externo_id)

    # Verificar que el padre pertenece al grupo del externo
    if externo.grupo != padre.grupo:
        return HttpResponseForbidden("No tienes permiso para aprobar esta solicitud.")

    # Marcar aprobación del padre
    externo.autorizado_por_padre = True
    externo.save()

    # Registrar actividad
    registrar_actividad(
        request.user,
        "Aprobación de acceso externo",
        f"Aprobaste el acceso de {externo.user.get_full_name()} como {externo.get_rol_display()}.",
    )

    # Notificar a la madre
    for admin in externo.grupo.miembros.all():
        if admin.user != request.user:
            registrar_actividad(
                admin.user,
                "Solicitud externa aprobada por el padre",
                f"El padre aprobó el acceso de {externo.user.get_full_name()}.",
            )

    messages.success(
        request, "Has aprobado la solicitud. Falta la aprobación de la madre."
    )
    return redirect("core:panel_externos")


# Aprobación de la Madre
@solo_padres
def aprobar_externo_madre(request, externo_id):
    """La madre aprueba la solicitud de acceso del profesional externo."""
    madre = Padre.objects.get(user=request.user)

    externo = get_object_or_404(MiembroExterno, id=externo_id)

    # Verificar que la madre pertenece al grupo del externo
    if externo.grupo != madre.grupo:
        return HttpResponseForbidden("No tienes permiso para aprobar esta solicitud.")

    # Marcar aprobación de la madre
    externo.autorizado_por_madre = True
    externo.save()

    # Registrar actividad
    registrar_actividad(
        request.user,
        "Aprobación de acceso externo",
        f"Aprobaste el acceso de {externo.user.get_full_name()} como {externo.get_rol_display()}.",
    )

    # Notificar al padre
    for admin in externo.grupo.miembros.all():
        if admin.user != request.user:
            registrar_actividad(
                admin.user,
                "Solicitud externa aprobada por la madre",
                f"La madre aprobó el acceso de {externo.user.get_full_name()}.",
            )

    # Si ambos aprobaron, activar acceso
    if externo.autorizado_por_padre and externo.autorizado_por_madre:
        externo.fecha_autorizacion = timezone.now()
        externo.save()

        registrar_actividad(
            request.user,
            "Acceso externo activado",
            f"{externo.user.get_full_name()} ahora tiene acceso como {externo.get_rol_display()}.",
        )

        for admin in externo.grupo.miembros.all():
            registrar_actividad(
                admin.user,
                "Acceso externo activado",
                f"{externo.user.get_full_name()} ha sido autorizado completamente.",
            )

        messages.success(
            request, "Has aprobado la solicitud. El acceso ha sido activado."
        )
        return redirect("core:panel_externos")

    messages.success(
        request, "Has aprobado la solicitud. Falta la aprobación del padre."
    )
    return redirect("core:panel_externos")


@solo_padres
def revocar_externo(request, externo_id):
    """Padre o madre revocan el acceso del profesional externo."""
    admin = Padre.objects.get(user=request.user)
    externo = get_object_or_404(MiembroExterno, id=externo_id)

    # Verificar que pertenece al grupo del administrador
    if externo.grupo != admin.grupo:
        return HttpResponseForbidden("No tienes permiso para revocar este acceso.")

    # Revocar acceso
    externo.autorizado_por_padre = False
    externo.autorizado_por_madre = False
    externo.fecha_autorizacion = None
    externo.save()

    # Registrar actividad
    registrar_actividad(
        request.user,
        "Acceso externo revocado",
        f"Has revocado el acceso de {externo.user.get_full_name()} ({externo.get_rol_display()}).",
    )

    # Notificar al otro administrador
    for miembro in externo.grupo.miembros.all():
        if miembro.user != request.user:
            registrar_actividad(
                miembro.user,
                "Acceso externo revocado",
                f"{request.user.get_full_name()} ha revocado el acceso de {externo.user.get_full_name()}.",
            )

    messages.success(
        request, "El acceso del profesional ha sido revocado correctamente."
    )
    return redirect("core:panel_externos")
