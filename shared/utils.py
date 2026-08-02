from core.models import MiembroExterno, Padre


def validar_rol(usuario, grupo, rol_permitido):
    """
    Verifica si un profesional externo tiene permiso para acceder a una sección.
    """
    externo = MiembroExterno.objects.filter(user=usuario, grupo=grupo).first()

    # Si es padre/madre, tiene acceso total
    if Padre.objects.filter(user=usuario, grupo=grupo).exists():
        return True

    # Si no es miembro externo, no tiene acceso
    if not externo:
        return False

    # Si no está autorizado por ambos, no tiene acceso
    if not (externo.autorizado_por_padre and externo.autorizado_por_madre):
        return False

    # Si su rol no coincide con el rol permitido, no tiene acceso
    return externo.rol == rol_permitido
