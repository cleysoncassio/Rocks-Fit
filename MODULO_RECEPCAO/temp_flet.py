import flet as ft
import os, sys

# Evitar travamentos do Flet no Linux (Wayland)
if sys.platform.startswith("linux"):
    os.environ["GDK_BACKEND"] = "x11"
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"

from datetime import datetime, timedelta
import random
import requests
import threading
import time
import base64
try:
    import cv2
    import numpy as np
except ImportError:
    pass

# --- CONFIGURAÇÕES ---
SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rocksfit@2024"
COR_BG = "#050505"
COR_PRIMARY = "#f27121"
COR_CARD = "#121212"
COR_CARD_HIGH = "#1e1e1e"
COR_TEXTO = "#ffffff"
COR_TEXT_SEC = "#888888"
COR_SUCCESS = "#2ecc71"
COR_WARNING = "#f39c12"
COR_ERROR = "#e74c3c"

# Dados mockados para demonstração
MOCK_ALUNOS = [
    {"nome": "Marcos Rogério Silva", "matricula": "1042", "status": "ativo", "vencimento": "2026-06-15", "dias_restantes": 46},
    {"nome": "Juliana Cavalcante Souza", "matricula": "0987", "status": "ativo", "vencimento": "2026-05-30", "dias_restantes": 30},
    {"nome": "Pedro Tavares Lima", "matricula": "1108", "status": "alerta", "vencimento": "2026-05-03", "dias_restantes": 3},
    {"nome": "Ana Flávia Ribeiro", "matricula": "0812", "status": "vencido", "vencimento": "2026-04-25", "dias_restantes": -5},
    {"nome": "Carlos Sousa Melo", "matricula": "1233", "status": "ativo", "vencimento": "2026-07-20", "dias_restantes": 81},
    {"nome": "Roberta Leal", "matricula": "1156", "status": "ativo", "vencimento": "2026-06-01", "dias_restantes": 32},
    {"nome": "Fernando Costa", "matricula": "0890", "status": "ativo", "vencimento": "2026-08-10", "dias_restantes": 102},
    {"nome": "Patrícia Mendes", "matricula": "0765", "status": "vencendo", "vencimento": "2026-05-10", "dias_restantes": 10},
]

MOCK_HISTORICO = [
    {"hora": "14:32:17", "nome": "Marcos Rogério", "status": "Liberado"},
    {"hora": "14:28:05", "nome": "Juliana Cavalcante", "status": "Liberado"},
    {"hora": "14:19:44", "nome": "Ana Flávia Ribeiro", "status": "Bloqueado"},
    {"hora": "14:11:02", "nome": "Carlos Sousa Melo", "status": "Liberado"},
    {"hora": "13:58:33", "nome": "Pedro Tavares", "status": "Liberado"},
    {"hora": "13:45:10", "nome": "Roberta Leal", "status": "Liberado"},
]


def main(page: ft.Page):
    page.title = "ROCKS FIT - RECEPÇÃO"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COR_BG
    page.window.width = 1400
    page.window.height = 900

    # Estado
    state = {
        "alunos_data": MOCK_ALUNOS.copy(),
        "historico": MOCK_HISTORICO.copy(),
        "camera_on": False,
        "monitor_ativo": True,
    }

    # ==========================
    # COMPONENTES DA SIDEBAR ESQUERDA
    # ==========================

    # Logo
    logo = ft.Text("LOGO")

    def create_menu_item(text, icon, active=False, on_click=None):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=COR_PRIMARY if active else COR_TEXT_SEC, size=20),
                    ft.Text(text, color=COR_TEXTO if active else COR_TEXT_SEC, size=14, weight=ft.FontWeight.W_500),
                ],
                spacing=12, alignment=ft.MainAxisAlignment.START
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=12,
            bgcolor=COR_CARD if active else None,
            on_click=on_click,
            ink=True,
        )

    def create_section_title(text):
        return ft.Text(text, color=COR_TEXT_SEC, size=11, weight=ft.FontWeight.BOLD, opacity=0.7)

    # Menu Monitoramento
    menu_monitoramento = ft.Column(
        [
            create_section_title("MONITORAMENTO"),
            create_menu_item("Clientes", "people", active=True),
            create_menu_item("Monitor Câmera", "videocam"),
        ],
        spacing=4
    )

    # Menu Acesso
    btn_entrada = ft.Container(
        content=ft.Row(
            [
                ft.Icon("lock_open", color=COR_PRIMARY, size=18),
                ft.Text("Liberar entrada", color=COR_TEXTO, size=14, weight=ft.FontWeight.BOLD),
            ],
            spacing=10, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_PRIMARY,
        height=48,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=20),
        ink=True,
        on_click=lambda _: None,
    )

    btn_saida = ft.Container(
        content=ft.Row(
            [
                ft.Icon("lock", color=COR_ERROR, size=18),
                ft.Text("Liberar saída", color=COR_ERROR, size=14, weight=ft.FontWeight.BOLD),
            ],
            spacing=10, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_CARD,
        height=48,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=20),
        border=ft.border.all(1, COR_ERROR + "40"),
        ink=True,
        on_click=lambda _: None,
    )

    btn_monitor = ft.Container(
        content=ft.Row(
            [
                ft.Icon("desktop_windows", color="#ffffff", size=18),
                ft.Text("2ª Tela (Monitor)", color="#ffffff", size=14, weight=ft.FontWeight.BOLD),
            ],
            spacing=10, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_PRIMARY,
        height=48,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=20),
        ink=True,
        on_click=lambda _: page.launch_url("/monitor", web_window_name="_blank"),
    )

    menu_acesso = ft.Column(
        [
            create_section_title("ACESSO"),
            btn_monitor,
            btn_entrada,
            btn_saida,
        ],
        spacing=8
    )

    def sync_crm(e=None):
        pass

    # Menu Sistema
    menu_sistema = ft.Column(
        [
            create_section_title("SISTEMA"),
            create_menu_item("Sincronizar", "sync", on_click=sync_crm),
            create_menu_item("Histórico de Acesso", "history", on_click=lambda e: abrir_historico(e)),
            create_menu_item("Diagnóstico", "settings"),
        ],
        spacing=4
    )

    sidebar = ft.Container(
        width=260,
        bgcolor=COR_BG,
        padding=ft.padding.all(20),
        border=ft.border.only(right=ft.BorderSide(1, COR_CARD_HIGH)),
        content=ft.Column(
            [
                logo,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    # ==========================
    # COMPONENTES DO CENTRO
    # ==========================

    # Barra superior
    status_online = ft.Container(
        content=ft.Row(
            [
                ft.Icon("cloud_done", color=COR_SUCCESS, size=16),
                ft.Text("Online: ", color=COR_TEXT_SEC, size=13),
                ft.Text("CRM", color=COR_SUCCESS, size=13, weight=ft.FontWeight.BOLD),
                ft.Icon("check_circle", color=COR_SUCCESS, size=14),
            ],
            spacing=4
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        border_radius=20,
        bgcolor=COR_CARD,
    )

    status_camera = ft.Container(
        content=ft.Row(
            [
                ft.Text("Câmera: ", color=COR_TEXT_SEC, size=13),
                ft.Text("OFF", color=COR_ERROR, size=13, weight=ft.FontWeight.BOLD),
            ],
            spacing=4
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        border_radius=20,
        bgcolor=COR_CARD,
    )

    search_field = ft.TextField(
        hint_text="Pesquisar aluno por nome ou matrícula...",
        prefix_icon="search",
        bgcolor=COR_CARD,
        border_color="transparent",
        focused_border_color=COR_PRIMARY,
        color=COR_TEXTO,
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=15, vertical=10),
        text_size=14,
        expand=True,
        on_change=lambda e: render_alunos(),
    )

    top_bar = ft.Row(
        [
            search_field,
            status_online,
            status_camera,
        ],
        spacing=12, alignment=ft.MainAxisAlignment.START
    )

    # Cards de estatísticas
    def create_stat_card(title, value, color):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, color=COR_TEXT_SEC, size=13, weight=ft.FontWeight.W_500),
                    ft.Text(str(value), color=color, size=36, weight=ft.FontWeight.BOLD, 
                           font_family="Space Grotesk"),
                ],
                spacing=4, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=140, height=100,
            bgcolor=COR_CARD,
            border_radius=16,
            alignment=ft.Alignment(0, 0),
            padding=ft.padding.all(16),
        )

    stats_row = ft.Row(
        [
            create_stat_card("Ativos", 142, COR_SUCCESS),
            create_stat_card("Vencendo", 17, COR_WARNING),
            create_stat_card("Vencidos", 8, COR_ERROR),
        ],
        spacing=12, alignment=ft.MainAxisAlignment.START
    )

    # Lista de alunos
    lista_alunos_col = ft.ListView(expand=True, spacing=8, padding=ft.padding.only(top=10))

    def get_status_color(status):
        status = str(status).lower()
        if status in ["ativo", "liberado"]:
            return COR_SUCCESS
        elif status in ["alerta", "vencendo"]:
            return COR_WARNING
        else:
            return COR_ERROR

    def get_status_badge(status, dias):
        status = str(status).lower()
        if status == "vencido":
            return ft.Container(
                content=ft.Text(f"Vencido há {abs(dias)} dias", color=COR_ERROR, size=11, weight=ft.FontWeight.BOLD),
                bgcolor=COR_ERROR + "15",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
            )
        elif status == "alerta" or dias <= 3:
            return ft.Container(
                content=ft.Text(f"Vence em {dias} dias", color=COR_WARNING, size=11, weight=ft.FontWeight.BOLD),
                bgcolor=COR_WARNING + "15",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
            )
        else:
            return ft.Container(
                content=ft.Text(f"Vence {dias} dias", color=COR_SUCCESS, size=11, weight=ft.FontWeight.BOLD),
                bgcolor=COR_SUCCESS + "15",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
            )

    def render_alunos():
        lista_alunos_col.controls.clear()
        
        filter_text = search_field.value.lower() if search_field.value else ""

        for aluno in state["alunos_data"]:
            nome = str(aluno.get("nome", "ALUNO"))
            matricula = str(aluno.get("matricula", "N/D"))
            status = str(aluno.get("status", "ativo"))
            dias = int(aluno.get("dias_restantes", 0))
            
            if filter_text and filter_text not in nome.lower() and filter_text not in matricula:
                continue

            # Avatar com iniciais
            iniciais = "".join([p[0] for p in nome.split()[:2]]).upper()
            cor_status = get_status_color(status)

            avatar = ft.Container(
                content=ft.Text(iniciais, color=cor_status, size=16, weight=ft.FontWeight.BOLD),
                width=50, height=50,
                border_radius=25,
                bgcolor=COR_CARD_HIGH,
                border=ft.border.all(2, cor_status),
                alignment=ft.Alignment(0, 0),
            )

            # Indicador de status online
            indicador = ft.Container(
                width=10, height=10, border_radius=5,
                bgcolor=cor_status,
                border=ft.border.all(2, COR_CARD),
            )

            avatar_com_indicador = ft.Stack(
                [
                    avatar,
                    ft.Container(content=indicador, right=0, bottom=0),
                ],
                width=52, height=52,
            )

            # Info do aluno
            info = ft.Column(
                [
                    ft.Text(nome[:20] + "..." if len(nome) > 20 else nome, 
                           color=COR_TEXTO, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Mat. {matricula}", color=COR_TEXT_SEC, size=12),
                ],
                spacing=2, alignment=ft.MainAxisAlignment.CENTER
            )

            # Badge de status
            badge = get_status_badge(status, dias)

            # Card do aluno
            card = ft.Container(
                content=ft.Row(
                    [
                        ft.Row(
                            [avatar_com_indicador, info],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        badge,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                bgcolor=COR_CARD,
                border_radius=16,
                padding=ft.padding.all(16),
                ink=True,
            )

            lista_alunos_col.controls.append(card)

        if page.views:
            page.update()

    center_content = ft.Column(
        [
            top_bar,
            ft.Divider(height=20, color="transparent"),
            stats_row,
            ft.Divider(height=20, color="transparent"),
            lista_alunos_col,
        ],
        expand=True, spacing=0
    )

    center_panel = ft.Container(
        expand=True,
        bgcolor=COR_BG,
        padding=ft.padding.all(30),
        content=center_content,
    )

    # ==========================
    # MODAL DE HISTÓRICO E LOTAÇÃO
    # ==========================

    historico_lista = ft.ListView(expand=True, spacing=0, padding=ft.padding.only(top=10))

    def render_historico():
        historico_lista.controls.clear()
        for reg in state["historico"]:
            cor = COR_SUCCESS if reg["status"] == "Liberado" else COR_ERROR
            item = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(reg["hora"], color=COR_TEXT_SEC, size=11),
                        ft.Text(reg["nome"], color=COR_TEXTO, size=14, weight=ft.FontWeight.W_500),
                        ft.Row(
                            [
                                ft.Container(width=6, height=6, border_radius=3, bgcolor=cor),
                                ft.Text(reg["status"], color=cor, size=12, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                    ],
                    spacing=4
                ),
                padding=ft.padding.symmetric(vertical=12, horizontal=15),
                border=ft.border.only(bottom=ft.BorderSide(1, COR_CARD_HIGH)),
            )
            historico_lista.controls.append(item)
        if page.views:
            try:
                page.update()
            except Exception:
                pass

    def abrir_historico(e=None):
        render_historico()
        
        # Simulação de lotação baseada nos acessos ou fixa
        lotacao_porcentagem = 45
        capacidade_maxima = 100
        lotacao_atual = int((lotacao_porcentagem / 100) * capacidade_maxima)
        
        dlg = ft.AlertDialog(
            title=ft.Text("MONITOR DE ACESSOS", font_family="Space Grotesk", weight="bold"),
            content=ft.Container(
                width=500,
                height=600,
                content=ft.Column(
                    [
                        ft.Text("LOTAÇÃO ATUAL", color=COR_TEXT_SEC, size=11, weight="bold", opacity=0.7),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"{lotacao_porcentagem}%", size=32, font_family="Space Grotesk", weight="bold", color=COR_PRIMARY),
                                    ft.Text(f"{lotacao_atual} de {capacidade_maxima} pessoas", color=COR_TEXT_SEC, size=12)
                                ], alignment="spaceBetween", vertical_alignment="end"),
                                ft.ProgressBar(value=lotacao_porcentagem/100, color=COR_PRIMARY, bgcolor=COR_CARD_HIGH, height=12),
                            ]),
                            padding=20, bgcolor=COR_CARD, border_radius=12, margin=ft.padding.only(bottom=20)
                        ),
                        ft.Text("HISTÓRICO RECENTE", color=COR_TEXT_SEC, size=11, weight="bold", opacity=0.7),
                        ft.Container(
                            content=historico_lista,
                            expand=True, bgcolor=COR_CARD, border_radius=12, padding=5, border=ft.border.all(1, COR_CARD_HIGH)
                        )
                    ]
                )
            ),
            bgcolor=COR_BG,
            actions=[ft.TextButton("FECHAR", on_click=lambda e: fechar_historico(dlg))]
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def fechar_historico(dlg):
        dlg.open = False
        if dlg in page.overlay:
            page.overlay.remove(dlg)
        page.update()

    # ==========================
    # LAYOUT PRINCIPAL
    # ==========================

    layout = ft.Row([sidebar], expand=True, spacing=0)

    # ==========================
    # ROTEAMENTO DE TELAS (DASHBOARD vs CÂMERA)
    # ==========================
    def route_change(route):
        page.views.clear()
        
        # Base View
        page.views.append(
            ft.View(
                page.route or "/",
                [layout],
                padding=0,
                bgcolor=COR_BG
            )
        )
        
        if "/monitor" in page.route:
            page.title = "Monitor - Rocks Fit"
            surf = "#0e0e0e"
            surf_low = "#131313"
            surf_high = "#201f1f"
            surf_highest = "#262626"
            primary = "#ff7a2f"
            
            titulo = ft.Row([
                ft.Text("BIOMETRIA ", size=56, font_family="Space Grotesk", weight="bold", italic=True, color="#ffffff"),
                ft.Text("ATIVA", size=56, font_family="Space Grotesk", weight="bold", italic=True, color=primary)
            ], spacing=0)
            subtitulo = ft.Text("APROXIME-SE PARA VALIDAR", size=18, color="#adaaaa", weight="w500")
            
            img_cam = ft.Image(src_base64="", fit="cover", expand=True, border_radius=16)
            
            cam_overlay = ft.Container(
                content=ft.Container(
                    bgcolor="#ff7a2f22",
                    border=ft.border.all(2, "#ff7a2f44"),
                    border_radius=12,
                    width=250, height=250,
                    alignment=ft.Alignment(0,0),
                    content=ft.Icon("face", color=primary, size=48, opacity=0.8)
                ),
                alignment=ft.Alignment(0,0)
            )
            
            lbl_cam_status = ft.Text("AGUARDANDO...", size=14, weight="bold", color="#000000")
            badge_cam_status = ft.Container(
                content=ft.Row([
                    ft.Container(width=12, height=12, border_radius=6, bgcolor="#000000"),
                    lbl_cam_status
                ], alignment="center", spacing=8),
                bgcolor=primary,
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=24, vertical=10),
                margin=ft.padding.only(bottom=30)
            )
            
            cam_container = ft.Container(
                content=ft.Stack([
                    img_cam,
                    cam_overlay,
                    ft.Container(content=badge_cam_status, alignment=ft.alignment.bottom_center)
                ]),
                expand=True,
                bgcolor=surf_highest,
                border_radius=16,
                margin=ft.padding.only(top=20),
                border=ft.border.all(1, "#ffffff10")
            )
            
            left_col = ft.Column([titulo, subtitulo, cam_container], expand=True)
            
            lbl_nome = ft.Text("ACESSO RESTRITO", size=24, font_family="Space Grotesk", weight="bold", color="#ffffff", text_align="center")
            lbl_msg = ft.Text("Posicione-se em frente à câmera para identificação automática", size=14, color="#adaaaa", text_align="center")
            img_perfil = ft.Image(src="https://via.placeholder.com/150", width=120, height=120, border_radius=60, fit="cover", opacity=0.3)
            
            lbl_status_tag = ft.Text("INATIVO", size=12, weight="bold", color="#ff7351")
            status_container = ft.Container(
                content=lbl_status_tag,
                bgcolor="#ff735133",
                padding=ft.padding.symmetric(horizontal=12, vertical=4),
                border_radius=12
            )
            
            card_perfil = ft.Container(
                content=ft.Column([
                    ft.Container(content=img_perfil, alignment=ft.Alignment(0,0), margin=ft.padding.only(bottom=20)),
                    ft.Container(content=lbl_nome, alignment=ft.Alignment(0,0)),
                    ft.Container(content=lbl_msg, alignment=ft.Alignment(0,0), margin=ft.padding.only(bottom=30)),
                    ft.Row([
                        ft.Text("STATUS", size=12, color="#adaaaa"),
                        status_container
                    ], alignment="spaceBetween"),
                    ft.Divider(color=surf_highest, height=30),
                    ft.Row([
                        ft.Text("UNIDADE", size=12, color="#adaaaa"),
                        ft.Text("ROCKS FIT #01", size=14, weight="bold", color="#ffffff")
                    ], alignment="spaceBetween"),
                ]),
                bgcolor=surf_high,
                padding=30,
                border_radius=20,
            )
            
            card_capacidade = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("CAPACIDADE", size=18, font_family="Space Grotesk", weight="bold", italic=True, color="#000000"),
                        ft.Icon("people", color="#000000")
                    ], alignment="spaceBetween"),
                    ft.Row([
                        ft.Text("74%", size=48, font_family="Space Grotesk", weight="bold", color="#000000"),
                        ft.Text("LOTADO", size=12, weight="bold", color="#000000")
                    ], alignment="spaceBetween", vertical_alignment="end"),
                    ft.ProgressBar(value=0.74, color="#000000", bgcolor="#ffffff40", height=8)
                ]),
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=["#ff9159", "#ff7a2f"]
                ),
                padding=30,
                border_radius=20,
                margin=ft.padding.only(top=20)
            )
            
            right_col = ft.Container(
                content=ft.Column([card_perfil, card_capacidade]),
                width=360,
                margin=ft.padding.only(left=40)
            )
            
            monitor_layout = ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Text("ROCKS FIT", size=24, font_family="Space Grotesk", weight="bold", italic=True, color=primary),
                            ft.Row([
                                ft.Text("Biometria", color=primary, weight="bold"),
                                ft.Text("Dashboard", color="#adaaaa"),
                                ft.Text("Membros", color="#adaaaa")
                            ], spacing=30),
                            ft.Row([ft.Icon("sensors", color=primary), ft.Icon("notifications", color=primary)], spacing=15)
                        ], alignment="spaceBetween"),
                        margin=ft.padding.only(bottom=40)
                    ),
                    ft.Row([left_col, right_col], expand=True),
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Container(width=8, height=8, border_radius=4, bgcolor=primary),
                                ft.Text("SERVER: ONLINE", size=10, weight="bold", color="#adaaaa"),
                                ft.Container(width=8, height=8, border_radius=4, bgcolor=primary, margin=ft.padding.only(left=20)),
                                ft.Text("SCANNER: ACTIVE", size=10, weight="bold", color="#adaaaa"),
                            ]),
                            ft.Text("SÃO PAULO, BR", size=10, color="#adaaaa")
                        ], alignment="spaceBetween"),
                        margin=ft.padding.only(top=20)
                    )
                ], expand=True),
                expand=True,
                padding=50,
                bgcolor=surf
            )
            
            camera_estado = {"rodando": True}
            
            def loop_camera():
                pass

            page.views.append(
                ft.View(
                    "/monitor",
                    [monitor_layout],
                    bgcolor=surf,
                    padding=0
                )
            )
        else:
            page.title = "ROCKS FIT - RECEPÇÃO"
            
        page.update()

    def view_pop(view):
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Inicializar estado e dados ANTES de montar as views
    render_alunos()
    render_historico()
    sync_crm()
    
    # Finalmente dispara o roteamento inicial
    page.go(page.route or "/")




if __name__ == "__main__":
    try:
        if sys.platform.startswith("linux"):
            ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, route_url_strategy="path")
        else:
            ft.app(target=main, port=8550, route_url_strategy="path")
    except Exception as e:
        print(f"Erro ao iniciar: {e}")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550)