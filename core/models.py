"""Modelos principales de usuarios y niños."""

from django.db import models
from django.contrib.auth.models import User
import uuid


# 1. se para crear grupos coparental "llevar un historial conjunto de los procesos"
# GrupoCoparental(nombre="Grupo de X", padre.grupo = ese grupo
class GrupoCoparental(models.Model):
    nombre = models.CharField(max_length=100)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# 2. Invitación Coparental
class InvitacionCoparental(models.Model):
    grupo = models.ForeignKey(
        GrupoCoparental, on_delete=models.CASCADE, related_name="invitaciones"
    )
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    aceptada = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitación a {self.email} para {self.grupo}"


# Clase Padre
class Padre(models.Model):
    """Modelo que representa a cada padre/madre en el sistema."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="perfil_padre"
    )
    grupo = models.ForeignKey(
        GrupoCoparental,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="miembros",
    )
    telefono = models.CharField("Teléfono", max_length=20, blank=True)
    domicilio = models.CharField("Domicilio", max_length=255, blank=True)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    foto = models.ImageField(
        "Foto de perfil", upload_to="perfiles/", null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

# Clase para permitir acceso a profesionales externos
class MiembroExterno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoCoparental, on_delete=models.CASCADE, related_name="externos")

    ROLES = [
        ("medico", "Médico"),
        ("psicologo", "Psicólogo"),
        ("abogado", "Abogado"),
        ("tutor", "Tutor"),
        ("profesor", "Profesor"),
    ]

    rol = models.CharField(max_length=50, choices=ROLES)

    autorizado_por_padre = models.BooleanField(default=False)
    autorizado_por_madre = models.BooleanField(default=False)

    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    def autorizado(self):
        return self.autorizado_por_padre and self.autorizado_por_madre

    def __str__(self):
        return f"{self.user.username} ({self.get_rol_display})"


# Clase nino
class Nino(models.Model):
    """Modelo para los niños del sistema coparental."""

    nombre = models.CharField("Nombre", max_length=100)
    fecha_nacimiento = models.DateField("Fecha de nacimiento")

    def __str__(self):
        return self.nombre


# Modelo nuevo para registrar actividades "Historial"
class RegistroActividad(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accion} - {self.usuario}"


def registrar_actividad(usuario, accion, descripcion=""):
    """
    Registra una actividad en el historial y envía notificación al grupo.
    Esta función se usa desde las vistas.
    """

    # Crear registro en la base de datos
    registro = RegistroActividad.objects.create(
        usuario=usuario,
        accion=accion,
        descripcion=descripcion,
    )

    # Enviar notificación al grupo (si el usuario pertenece a uno)
    padre = Padre.objects.get(user=usuario)

    if padre.grupo:
        from core.tasks import enviar_notificacion_grupo

        mensaje = f"{usuario.username} realizó la acción: {accion}\n\n{descripcion}"
        enviar_notificacion_grupo.delay(padre.grupo.id, mensaje)

    return registro
