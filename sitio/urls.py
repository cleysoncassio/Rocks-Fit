"""
URL configuration for sitio project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from blog import views

urlpatterns = [
    path("7becomb/", admin.site.urls),
    path("admin/", views.fake_admin, name="fake_admin"),
    path("", include("blog.urls_auth")), # Novas rotas de Autenticação (Login, 2FA, Reset)
    path("reparar-banco-de-dados-privilegiado/", views.crm_reparar_banco, name="reparar_banco"),
    path("fix/", views.crm_reparar_banco, name="fix_db"),
    path("", include("blog.urls")),
]

# Servir arquivos de mídia em desenvolvimento e produção
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
