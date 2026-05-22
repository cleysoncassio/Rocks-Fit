import flet as ft
import time

def main(page: ft.Page):
    try:
        icon1 = ft.Icon("sync")
        icon2 = ft.Icon(ft.Icons.SYNC)
        page.add(ft.Column([ft.Text("Test string icon"), icon1, ft.Text("Test enum icon"), icon2]))
        print("Page added")
    except Exception as e:
        print("Error:", e)
    
    time.sleep(2)
    page.window_close()

ft.app(target=main)
