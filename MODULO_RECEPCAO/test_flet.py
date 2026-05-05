import flet as ft

def main(page: ft.Page):
    btn_monitor = ft.Container(
        content=ft.Text("2ª Tela (Monitor)"),
        on_click=lambda _: page.launch_url("/monitor", web_window_name="_blank"),
    )
    page.add(btn_monitor)

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8551, route_url_strategy="path")
