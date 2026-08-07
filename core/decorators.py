"""Decoradores de control de acceso compartidos entre apps."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden

from .models import Padre


def solo_padres(view_func):
    """Restringe una vista a quienes tienen perfil de Padre (madre/padre del
    grupo). Los profesionales externos (MiembroExterno) no tienen acceso:
    su información familiar solo vive en su canal de rol.

    Deja el grupo del usuario en `request.grupo` para que la vista no tenga
    que volver a consultarlo — es también el límite de aislamiento: cada
    grupo coparental es un espacio cerrado, nunca ve contenido de otro."""

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        padre = Padre.objects.filter(user=request.user).first()
        if padre is None:
            return HttpResponseForbidden(
                "Esta sección es solo para los administradores del grupo coparental."
            )
        request.grupo = padre.grupo
        return view_func(request, *args, **kwargs)

    return wrapper


class SoloPadresMixin(LoginRequiredMixin):
    """Igual que `solo_padres` pero para class-based views. Deja el grupo en
    `self.grupo` / `request.grupo`."""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        padre = Padre.objects.filter(user=request.user).first() if request.user.is_authenticated else None
        self.grupo = padre.grupo if padre else None
        request.grupo = self.grupo

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and self.grupo is None:
            return HttpResponseForbidden(
                "Esta sección es solo para los administradores del grupo coparental."
            )
        return super().dispatch(request, *args, **kwargs)
