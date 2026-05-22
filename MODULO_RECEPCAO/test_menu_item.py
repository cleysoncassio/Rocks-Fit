import flet as ft
import time

def main(page: ft.Page):
    try:
        container = ft.Container(
            content=ft.Row(
                [
                    ft.Icon("people", color="#cccccc", size=20),
                    ft.Text("Clientes", color="#cccccc", size=14, weight="normal"),
                ],
                spacing=12, alignment=ft.MainAxisAlignment.START
            ),
            padding=ft.Padding(16, 12, 16, 12),
            border_radius=12,
            bgcolor="#1a1a1a"
        )
        page.add(container)
        print("Page added")
    except Exception as e:
        print("Error:", e)
    
    time.sleep(2)
    page.window_close()

ft.app(target=main)
