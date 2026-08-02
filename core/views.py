"""Vistas de la app core: dashboard y perfil."""

from datetime import date, timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
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
from .forms import PadreForm, UsuarioForm

# ⭐ AGREGADO: Nuevos modelos que creaste (GrupoCoparental + InvitacionCoparental)
from .models import (
    MiembroExterno,
    Padre,
    RegistroActividad,
    GrupoCoparental,
    InvitacionCoparental,
)
from .models import registrar_actividad
from .tasks import enviar_invitacion_email


@login_required
def dashboard(request):
    """Dashboard principal: calendario del mes, próximos eventos y alertas de pago."""
    hoy = date.today()

    # Próximos eventos (visitas y vacaciones con fecha_inicio >= hoy, en orden)
    proximas_visitas = Evento.objects.filter(fecha_inicio__gte=hoy).order_by(
        "fecha_inicio"
    )

    # Pagos pendientes (manutención)
    pagos_pendientes = Pago.objects.filter(estado="pendiente").order_by("fecha")

    # Gastos recientes
    gastos_recientes = Gasto.objects.order_by("-fecha_creacion")[:5]

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
@login_required
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
@login_required
def aceptar_invitacion(request, token):
    """Permite que el otro progenitor acepte la invitación y se una al grupo."""
    invitacion = get_object_or_404(InvitacionCoparental, token=token, aceptada=False)

    padre, _ = Padre.objects.get_or_create(user=request.user)
    padre.grupo = invitacion.grupo
    padre.save()

    invitacion.aceptada = True
    invitacion.save()

    registrar_actividad(request.user, "Invitación aceptada")

    messages.success(request, "Te has unido al grupo coparental.")
    return redirect("core:dashboard")


# Creacion de vista del Panel del Grupo
@login_required
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
@login_required
def panel_externos(request):
    padre = Padre.objects.get(user=request.user)

    if padre.grupo is None:
        return HttpResponseForbidden()

    externos = padre.grupo.externos.all()

    return render(request, "core/panel_externos.html", {"externos": externos})


# Proceso de solicitud para un acceso de caracter externo
@login_required
def solicitar_acceso_externo(request):
    """Vista para que un profesional externo solicite acceso al grupo coparental."""
    padre = Padre.objects.filter(user=request.user).first()

    # Si el usuario ya es padre/madre, no puede solicitar acceso externo
    if padre:
        messages.error(
            request, "Los administradores del grupo no pueden solicitar acceso externo."
        )
        return redirect("core:dashboard")

    if request.method == "POST":
        rol = request.POST.get("rol")
        grupo_id = request.POST.get("grupo_id")

        grupo = GrupoCoparental.objects.get(id=grupo_id)

        # Crear solicitud
        externo = MiembroExterno.objects.create(
            user=request.user,
            grupo=grupo,
            rol=rol,
            autorizado_por_padre=False,
            autorizado_por_madre=False,
        )

        # Registrar actividad
        registrar_actividad(
            request.user,
            "Solicitud de acceso externo",
            f"Solicitud enviada para acceder al grupo {grupo.nombre} como {rol}.",
        )

        # Notificar a los administradores
        for admin in grupo.miembros.all():
            registrar_actividad(
                admin.user,
                "Nueva solicitud externa",
                f"{request.user.get_full_name()} solicita acceso como {rol}.",
            )

        messages.success(
            request, "Tu solicitud ha sido enviada y está pendiente de aprobación."
        )
        return redirect("core:dashboard")

    grupos = GrupoCoparental.objects.all()  # En producción se filtra según invitación

    return render(request, "core/solicitar_acceso_externo.html", {"grupos": grupos})


# Aprobación del Padre
@login_required
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
@login_required
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


@login_required
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
