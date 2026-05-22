import flet as ft
try:
    p1 = ft.Padding(10, 6, 10, 6)
    p2 = ft.Padding(left=10, right=10, top=6, bottom=6)
    print("Padding 1:", p1)
    print("Padding 2:", p2)
except Exception as e:
    print("Error:", e)
