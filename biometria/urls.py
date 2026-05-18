from django.urls import path
from .views import verificar_biometria

urlpatterns = [
    path('verificar/', verificar_biometria, name='biometria-verificar'),
]
