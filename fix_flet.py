import re

with open("MODULO_RECEPCAO/ponte_rocksfit_flet.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix page alignment and run()
content = content.replace("page.padding = 0", "page.padding = 0\n    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH")
content = content.replace("ft.app(target=main, view=ft.AppView.WEB_BROWSER)", "ft.run(target=main, view=ft.WEB_BROWSER)")

# 2. Update make_btn to support borders and match tkinter
make_btn_old = """    def make_btn(text, icon_str, bgcolor, text_color, on_click):
        return ft.Container(
            content=ft.Row([
                ft.Text(icon_str, size=16),
                ft.Text(text, color=text_color, weight="bold", size=14)
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=bgcolor, height=48, width=220, border_radius=8,
            on_click=on_click, ink=True
        )"""

make_btn_new = """    def make_btn(text, icon_str, bgcolor, text_color, on_click, border=None):
        return ft.Container(
            content=ft.Row([
                ft.Text(icon_str, size=16),
                ft.Text(text, color=text_color, weight="bold", size=14)
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=bgcolor, height=48, width=220, border_radius=12,
            border=border, on_click=on_click, ink=True
        )"""
content = content.replace(make_btn_old, make_btn_new)

# 3. Update the buttons to match tkinter styles
content = content.replace('make_btn("ATUALIZAR", "🔄", COR_CARD, COR_TEXTO, lambda _: carregar_alunos())',
                          'make_btn("ATUALIZAR", "🔄", COR_CARD, COR_TEXTO, lambda _: carregar_alunos(), border=ft.border.all(1, COR_CARD_HIGH))')
content = content.replace('make_btn("HISTÓRICO", "📑", COR_CARD, COR_TEXTO, lambda _: abrir_historico())',
                          'make_btn("HISTÓRICO", "📑", COR_CARD, COR_TEXTO, lambda _: abrir_historico(), border=ft.border.all(1, COR_CARD_HIGH))')
content = content.replace('make_btn("LOGS TXT", "📂", COR_CARD, COR_TEXTO, lambda _: abrir_pasta_logs())',
                          'make_btn("LOGS TXT", "📂", COR_CARD, COR_TEXTO, lambda _: abrir_pasta_logs(), border=ft.border.all(1, COR_CARD_HIGH))')
content = content.replace('make_btn("ENTRADA", "🔓", "#1a120b", COR_PRIMARY, lambda _: abrir_catraca("0"))',
                          'make_btn("ENTRADA", "🔓", "#1a120b", COR_PRIMARY, lambda _: abrir_catraca("0"), border=ft.border.all(1, COR_PRIMARY))')
content = content.replace('make_btn("SAÍDA", "🔒", "#121212", COR_TEXT_SEC, lambda _: abrir_catraca("1"))',
                          'make_btn("SAÍDA", "🔒", "#121212", COR_TEXT_SEC, lambda _: abrir_catraca("1"), border=ft.border.all(1, COR_CARD_HIGH))')

# 4. Fix btn_cam_lock
btn_cam_old = """    btn_cam_lock = ft.Container(
        content=ft.Row([
            ft.Text("📷", size=16),
            ft.Text("LIBERAR CÂMERA", color=COR_TEXTO, weight="bold", size=14)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=COR_CARD, height=48, width=220, border_radius=8,
        on_click=lambda _: toggle_cam(), ink=True
    )"""
btn_cam_new = """    btn_cam_lock = ft.Container(
        content=ft.Row([
            ft.Text("📷", size=16),
            ft.Text("LIBERAR CÂMERA", color=COR_TEXTO, weight="bold", size=14)
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=COR_CARD, height=48, width=220, border_radius=12,
        border=ft.border.all(1, COR_CARD_HIGH),
        on_click=lambda _: toggle_cam(), ink=True
    )"""
content = content.replace(btn_cam_old, btn_cam_new)

# 5. Fix TextField and list spacing
pesquisa_old = """    pesquisa_input = ft.TextField(
        hint_text="PESQUISAR CLIENTE ROCKS FIT...",
        bgcolor=COR_CARD,
        border_color=COR_CARD_HIGH,
        border_radius=15,
        prefix_icon="search",
        on_change=lambda e: render_lista(e.control.value)
    )"""
pesquisa_new = """    pesquisa_input = ft.TextField(
        hint_text="PESQUISAR CLIENTE ROCKS FIT...",
        bgcolor=COR_CARD,
        border_color=COR_CARD_HIGH,
        border_width=1,
        border_radius=15,
        prefix_icon=ft.icons.SEARCH,
        color=COR_TEXTO,
        height=65,
        content_padding=20,
        text_style=ft.TextStyle(font_family="Inter", size=15),
        on_change=lambda e: render_lista(e.control.value)
    )"""
content = content.replace(pesquisa_old, pesquisa_new)

# 6. Fix Logo image load path
content = content.replace('logo_path = os.path.join(BASE_DIR, "logo.png")', 'logo_path = os.path.join(BASE_DIR, "media", "logo.png")\n    if not os.path.exists(logo_path): logo_path = os.path.join(BASE_DIR, "media", "rkslogo.png")')

with open("MODULO_RECEPCAO/ponte_rocksfit_flet.py", "w", encoding="utf-8") as f:
    f.write(content)
print("File rewritten successfully.")
