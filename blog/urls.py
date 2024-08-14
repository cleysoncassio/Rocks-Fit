from django.urls import path
from .views import index
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("programs/", views.programs, name="programs"),
    path("schedule/", views.schedule, name="schedule"),
    path("contact/", views.contact, name="contact"),
    path(
        "trainers/", views.trainers, name="trainers"
    ),  # Adicione a view 'trainers' se não estiver no seu projeto
    path("about/", views.about, name="about"),
    path("index/", index, name="index"),
]
