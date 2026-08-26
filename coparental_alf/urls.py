"""alf URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""Enrutado principal del proyecto."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import ensure_csrf_cookie
from allauth.account.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path( "accounts/login/", ensure_csrf_cookie(LoginView.as_view()), name="account_login",),
    path("accounts/", include("allauth.urls")),  # login/registro allauth
    path("", include("core.urls")),
    path("calendario/", include("calendario.urls")),
    path("finanzas/", include("finanzas.urls")),
    path("comunicacion/", include("comunicacion.urls")),
]

# Servir media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

