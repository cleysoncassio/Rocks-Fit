import flet as ft
import threading, time

def window2(page: ft.Page):
    page.title = "Window 2"
    page.add(ft.Text("Hello from Window 2"))

def window1(page: ft.Page):
    page.title = "Window 1"
    page.add(ft.Text("Hello from Window 1"))
    def open_win2(e):
        threading.Thread(target=lambda: ft.app(target=window2)).start()
    page.add(ft.ElevatedButton("Open Window 2", on_click=open_win2))

ft.app(target=window1)
