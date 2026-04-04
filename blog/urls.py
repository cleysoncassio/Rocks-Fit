from django.urls import path

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
    path("checkout/<int:plan_id>/", views.checkout_view, name="checkout"),
    path("api/process-payment/", views.process_payment_api, name="process_payment"),
    path("api/infinitepay-webhook/", views.infinitepay_webhook, name="infinitepay_webhook"),
    path("api/catraca-polling/", views.catraca_polling_api, name="catraca_polling"),
    path("api/catraca-sync/", views.catraca_sync_api, name="catraca_sync"),
    path("api/catraca-check/<str:id_tag>/", views.catraca_check_api, name="catraca_check"),
    path("api/aluno-list-full/", views.aluno_list_full_api, name="aluno_list_full"),
    path("api/aluno-update-data/", views.aluno_update_data_api, name="aluno_update_data"),
    path("api/dev/simular-pagamento/", views.dev_simular_pagamento, name="dev_simular_pagamento"),
    path("webhook/whatsapp/", views.whatsapp_webhook, name="whatsapp_webhook"),
]
