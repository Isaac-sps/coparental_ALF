from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuración de la app core (usuarios, dashboard)."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

