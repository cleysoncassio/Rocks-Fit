import flet as ft
try:
    icon = ft.Icon(name="sync")
    print("Icon name:", icon.name)
except Exception as e:
    print("Error string:", e)
    
try:
    icon2 = ft.Icon(name=ft.Icons.SYNC)
    print("Icon name enum:", icon2.name)
except Exception as e:
    print("Error enum:", e)
