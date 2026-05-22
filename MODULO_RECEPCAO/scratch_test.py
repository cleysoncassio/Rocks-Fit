import flet as ft
print("has on_change:", "on_change" in ft.Dropdown.__init__.__code__.co_varnames)
