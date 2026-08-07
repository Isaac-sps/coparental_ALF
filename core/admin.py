from django.contrib import admin

from .models import (
    GrupoCoparental,
    InvitacionCoparental,
    Padre,
    MiembroExterno,
    InvitacionExterno,
    CanalRol,
    MensajeCanal,
    DocumentoCanal,
)


@admin.register(GrupoCoparental)
class GrupoCoparentalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "creado_en")


@admin.register(InvitacionCoparental)
class InvitacionCoparentalAdmin(admin.ModelAdmin):
    list_display = ("email", "grupo", "aceptada", "creada_en")
    list_filter = ("aceptada",)


@admin.register(Padre)
class PadreAdmin(admin.ModelAdmin):
    list_display = ("user", "grupo", "telefono")


@admin.register(MiembroExterno)
class MiembroExternoAdmin(admin.ModelAdmin):
    list_display = ("user", "grupo", "rol", "autorizado_por_padre", "autorizado_por_madre")
    list_filter = ("rol",)


@admin.register(InvitacionExterno)
class InvitacionExternoAdmin(admin.ModelAdmin):
    list_display = ("email", "rol", "grupo", "invitado_por", "aceptada", "creada_en")
    list_filter = ("rol", "aceptada")


@admin.register(CanalRol)
class CanalRolAdmin(admin.ModelAdmin):
    list_display = ("rol", "grupo", "creado_en")
    list_filter = ("rol",)


@admin.register(MensajeCanal)
class MensajeCanalAdmin(admin.ModelAdmin):
    list_display = ("canal", "autor", "fecha_creacion")


@admin.register(DocumentoCanal)
class DocumentoCanalAdmin(admin.ModelAdmin):
    list_display = ("titulo", "canal", "subido_por", "fecha_creacion")
