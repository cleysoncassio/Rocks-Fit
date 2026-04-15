from django.urls import path

from . import views, api_views

urlpatterns = [
    path("", views.home, name="home"),
    path("programs/", views.programs, name="programs"),
    path("schedule/", views.schedule, name="schedule"),
    path("contact/", views.contact, name="contact"),
    path(
        "trainers/", views.trainers, name="trainers"
    ),  # Adicione a view 'trainers' se não estiver no seu projeto
    path("about/", views.about, name="about"),
    path("ferramentas/", views.tools, name="tools"),
    path("checkout/<int:plan_id>/", views.checkout_view, name="checkout"),
    path("api/process-payment/", views.process_payment_api, name="process_payment"),
    path("api/infinitepay-webhook/", views.infinitepay_webhook, name="infinitepay_webhook"),
    path("api/catraca-polling/", views.catraca_polling_api, name="catraca_polling"),
    path("api/catraca-sync/", views.catraca_sync_api, name="catraca_sync"),
    path("api/catraca-check/<str:id_tag>/", views.catraca_check_api, name="catraca_check"),
    path("api/aluno-list-full/", views.aluno_list_full_api, name="aluno_list_full"),
    path("api/aluno-update-data/", views.aluno_update_data_api, name="aluno_update_data"),
    path("api/dev/simular-pagamento/", views.dev_simular_pagamento, name="dev_simular_pagamento"),
    path("webhook/whatsapp/", views.whatsapp_webhook, name="whatsapp_webhook_blackhole"),

    # API para o App do Aluno
    path("api/app/login/", api_views.aluno_login, name="app_aluno_login"),
    path("api/app/schedule/", api_views.get_gym_schedule, name="app_gym_schedule"),
    path("api/app/profile/<int:aluno_id>/", api_views.aluno_profile, name="app_aluno_profile"),
]
