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

# Roles profesionales externos (médico, abogado, etc). Lista fija: para
# agregar uno nuevo se añade aquí una línea. Se usa para invitar profesionales
# (no tiene sentido "invitar" a alguien con rol "general").
ROLES_PROFESIONALES = [
    ("medico", "Médico"),
    ("psicologo", "Psicólogo"),
    ("abogado", "Abogado"),
    ("dentista", "Dentista"),
    ("asistenta_social", "Asistenta social"),
    ("profesor", "Profesor"),
    ("tutor", "Tutor legal"),
]

# Igual que ROLES_PROFESIONALES pero con "General" agregado: es la lista que
# usan los canales (CanalRol) y la subida de documentos, porque no todo
# archivo compartido pertenece a un profesional.
ROLES_CANAL = ROLES_PROFESIONALES + [("general", "General / Otros")]


# Invitación para que un profesional externo se una a un grupo coparental.
# La envía padre o madre; el acceso solo se activa cuando ambos aprueban
# (ver MiembroExterno.autorizado / aprobar_externo_padre / aprobar_externo_madre).
class InvitacionExterno(models.Model):
    grupo = models.ForeignKey(
        GrupoCoparental, on_delete=models.CASCADE, related_name="invitaciones_externos"
    )
    email = models.EmailField()
    rol = models.CharField(max_length=50, choices=ROLES_PROFESIONALES)
    invitado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="invitaciones_externos_enviadas"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    aceptada = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitación externa a {self.email} ({self.get_rol_display()}) para {self.grupo}"


# Clase para permitir acceso a profesionales externos
class MiembroExterno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoCoparental, on_delete=models.CASCADE, related_name="externos")

    ROLES = ROLES_PROFESIONALES

    rol = models.CharField(max_length=50, choices=ROLES)

    autorizado_por_padre = models.BooleanField(default=False)
    autorizado_por_madre = models.BooleanField(default=False)

    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    def autorizado(self):
        return self.autorizado_por_padre and self.autorizado_por_madre

    def __str__(self):
        return f"{self.user.username} ({self.get_rol_display})"


# Canal ALF: un espacio de mensajes + documentos por rol dentro de un grupo.
# Lo comparten los padres del grupo y los profesionales autorizados en ese rol.
class CanalRol(models.Model):
    grupo = models.ForeignKey(GrupoCoparental, on_delete=models.CASCADE, related_name="canales")
    rol = models.CharField(max_length=50, choices=ROLES_CANAL)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("grupo", "rol")

    def __str__(self):
        return f"Canal {self.get_rol_display()} - {self.grupo}"


class MensajeCanal(models.Model):
    canal = models.ForeignKey(CanalRol, on_delete=models.CASCADE, related_name="mensajes")
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensajes_canal")
    contenido = models.TextField("Contenido")
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    class Meta:
        ordering = ["fecha_creacion"]

    def __str__(self):
        return f"{self.autor}: {self.contenido[:30]}"


class DocumentoCanal(models.Model):
    canal = models.ForeignKey(CanalRol, on_delete=models.CASCADE, related_name="documentos")
    subido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="documentos_canal_subidos"
    )
    archivo = models.FileField("Archivo", upload_to="canales/documentos/%Y/%m/")
    titulo = models.CharField("Título", max_length=200)
    descripcion = models.TextField("Descripción", blank=True)
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.titulo} ({self.canal})"


def usuario_tiene_acceso_canal(user, canal):
    """True si el usuario es padre/madre del grupo del canal, o un profesional
    autorizado en ese mismo rol y grupo."""
    if Padre.objects.filter(user=user, grupo=canal.grupo).exists():
        return True
    externo = MiembroExterno.objects.filter(
        user=user, grupo=canal.grupo, rol=canal.rol
    ).first()
    return bool(externo and externo.autorizado())


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

    # Enviar notificación al grupo (si el usuario tiene perfil de padre y pertenece a uno)
    padre = Padre.objects.filter(user=usuario).first()

    if padre and padre.grupo:
        from core.tasks import enviar_notificacion_grupo

        mensaje = f"{usuario.username} realizó la acción: {accion}\n\n{descripcion}"
        enviar_notificacion_grupo.delay(padre.grupo.id, mensaje)

    return registro
