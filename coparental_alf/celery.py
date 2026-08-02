"""Configuración de Celery para tareas en segundo plano."""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Establecemos el módulo de settings de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coparental_alf.settings")

app = Celery("coparental_alf")

# Cargamos configuración desde settings.py usando el namespace CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover para encontrar tasks.py en las apps instaladas
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Tarea de prueba para verificar Celery."""
    print(f"Debug task ejecutada: {self.request!r}")
