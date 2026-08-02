from functools import wraps
from core.models import RegistroActividad


def registrar_actividad(nombre_accion):
    """
    Decorador para registrar automáticamente acciones del usuario.
    Guarda en la tabla core_registroactividad:
    - usuario
    - acción
    - descripción
    - fecha
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            RegistroActividad.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                accion=nombre_accion,
                descripcion=f"Vista ejecutada: {func.__name__}",
            )
            return func(request, *args, **kwargs)

        return wrapper

    return decorator
