# Inicialización del paquete principal del proyecto.
# Aquí conectamos Celery para que se cargue junto con Django.

from .celery import app as celery_app

__all__ = ("celery_app",)
