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

try:
    import face_recognition as fr
    FR_DISPONIVEL = True
    print("✅ face_recognition carregado – reconhecimento neural ativo")
except ImportError:
    FR_DISPONIVEL = False
    print("⚠️ face_recognition não disponível – usando ORB")

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

# --- ESTADO GLOBAL (Compartilhado entre abas/sessões) ---
GLOBAL_ALUNOS = []
GLOBAL_PERFIS = {}
GLOBAL_HISTORICO = []
FR_LOCK = threading.Lock()
SYNC_LOCK = threading.Lock()
CAM_LOCK = threading.Lock()

# Dados iniciais vazios (serão preenchidos pelo CRM)
MOCK_ALUNOS = []
MOCK_HISTORICO = []


def main(page: ft.Page):
    page.title = "ROCKS FIT - RECEPÇÃO"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COR_BG
    page.window.width = 1400
    page.window.height = 900

    # Estado Local da Sessão
    state = {
        "alunos_data": GLOBAL_ALUNOS if GLOBAL_ALUNOS else [],
        "historico": GLOBAL_HISTORICO if GLOBAL_HISTORICO else [],
        "camera_on": False,
        "monitor_ativo": True,
        "alunos_perfis": GLOBAL_PERFIS
    }

    # Sistema de notificação entre abas
    def on_broadcast(msg):
        if msg == "sync_done":
            state["alunos_data"] = GLOBAL_ALUNOS
            render_alunos()
        elif msg == "new_access":
            state["historico"] = GLOBAL_HISTORICO
            # Se o modal estiver aberto, ele não atualiza automaticamente aqui, 
            # mas a lista interna estará pronta para a próxima abertura.

    page.pubsub.subscribe(on_broadcast)

    # ==========================
    # COMPONENTES DA SIDEBAR ESQUERDA
    # ==========================

    # Logo
    logo = ft.Row(
        [
            ft.Container(
                content=ft.Icon("fitness_center", color=COR_PRIMARY, size=32),
                width=48, height=48, border_radius=12, bgcolor=COR_PRIMARY + "20",
                alignment=ft.Alignment(0, 0)
            ),
            ft.Column(
                [
                    ft.Text("ROCKS", font_family="Space Grotesk", size=24, weight=ft.FontWeight.BOLD, color=COR_TEXTO),
                    ft.Text("FIT", font_family="Space Grotesk", size=24, weight=ft.FontWeight.BOLD, color=COR_PRIMARY),
                ],
                spacing=0, alignment=ft.MainAxisAlignment.CENTER
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER, spacing=10
    )

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
        if not SYNC_LOCK.acquire(blocking=False):
            print("⏳ Sync já em andamento...")
            return

        def _fetch():
            global GLOBAL_ALUNOS, GLOBAL_PERFIS
            try:
                print("📡 Sincronizando com o CRM...")
                r = requests.get(f"{SITE_URL}/api/catraca-sync/?token={SYNC_TOKEN}", timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    # Filtra apenas contatos válidos se necessário (ex: nome presente)
                    novos_alunos = [a for a in data.get('alunos', []) if a.get('nome')]
                    state["alunos_data"] = novos_alunos
                    GLOBAL_ALUNOS = novos_alunos 
                    print(f"✅ Sync Finalizado. {len(GLOBAL_ALUNOS)} alunos carregados.")
                    
                    # Notifica todas as abas abertas
                    page.pubsub.send_all("sync_done")
                    # Só atualiza lista no dashboard; no monitor a lista não existe na view
                    if "/monitor" not in page.route:
                        render_alunos()
                    
                    # Carregamento de perfis faciais
                    if "cv2" in sys.modules:
                        try:
                            com_foto = [a for a in state["alunos_data"] if a.get("foto_url")]
                            print(f"📸 Alunos com foto: {len(com_foto)} de {len(state['alunos_data'])}")
                            if not com_foto:
                                print("⚠️ Nenhum aluno tem foto_url – reconhecimento desativado")
                            else:
                                metodo = "face_recognition (neural)" if FR_DISPONIVEL else "ORB (keypoints)"
                                print(f"🔄 Gerando perfis biométricos [{metodo}]...")
                                NovosPerfis = {}
                                
                                for a in state["alunos_data"]:
                                    furl = a.get("foto_url")
                                    if not furl: continue
                                    if furl.startswith('/'): furl = f"{SITE_URL}{furl}"
                                    try:
                                        resp = requests.get(furl, timeout=5)
                                        if resp.status_code != 200:
                                            print(f"  ⚠ HTTP {resp.status_code}: {a.get('nome')}")
                                            continue
                                        nparr = np.frombuffer(resp.content, np.uint8)
                                        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                                        if img_bgr is None:
                                            print(f"  ⚠ Imagem inválida: {a.get('nome')}")
                                            continue

                                        if FR_DISPONIVEL:
                                            # ── face_recognition: embedding neural 128-D ──
                                            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                                            img_rgb = np.ascontiguousarray(img_rgb)
                                            
                                            with FR_LOCK:
                                                locs = fr.face_locations(img_rgb, model="hog")
                                                encs = fr.face_encodings(img_rgb, locs, num_jitters=0) if locs else fr.face_encodings(img_rgb, num_jitters=0)
                                            
                                            if encs:
                                                NovosPerfis[str(a['matricula'])] = {'encoding': encs[0], 'data': a}
                                                print(f"  ✔ Perfil neural: {a.get('nome')}")
                                            else:
                                                print(f"  ⚠ Rosto não detectado: {a.get('nome')}")
                                        else:
                                            # ── fallback ORB ──
                                            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                                            img_face = cv2.resize(gray, (200, 200))
                                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                                            img_face = clahe.apply(img_face)
                                            orb = cv2.ORB_create(700)
                                            _, des = orb.detectAndCompute(img_face, None)
                                            if des is not None:
                                                NovosPerfis[str(a['matricula'])] = {'des': des, 'img': img_face.copy(), 'data': a}
                                                print(f"  ✔ Perfil ORB: {a.get('nome')}")
                                    except Exception as fe:
                                        print(f"  ⚠ Erro {a.get('nome')}: {fe}")

                                # Atualização atômica do global
                                GLOBAL_PERFIS = NovosPerfis
                                print(f"✅ Perfis gerados: {len(GLOBAL_PERFIS)} rostos [{metodo}]")
                        except Exception as e:
                            print("⚠️ Erro ao gerar perfis:", e)
            except Exception as ex:
                print("❌ Erro ao sincronizar com CRM:", ex)
            finally:
                try: SYNC_LOCK.release()
                except: pass
        threading.Thread(target=_fetch, daemon=True).start()

    # Menu Sistema
    menu_sistema = ft.Column(
        [
            create_section_title("SISTEMA"),
            create_menu_item("Sincronizar", "sync", on_click=sync_crm),
            create_menu_item("Histórico de Acesso", "history", on_click=lambda e: abrir_historico(e)),
            create_menu_item("Diagnóstico", "settings", on_click=lambda e: abrir_diagnostico(e)),
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
                ft.Divider(height=30, color="transparent"),
                menu_monitoramento,
                ft.Divider(height=20, color="transparent"),
                menu_acesso,
                ft.Divider(height=20, color="transparent"),
                menu_sistema,
                ft.Divider(height=20, color="transparent"),
                ft.Container(expand=True),  # Spacer
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(width=8, height=8, border_radius=4, bgcolor=COR_WARNING),
                            ft.Text("Câmera aguardando", color=COR_TEXT_SEC, size=12),
                        ],
                        spacing=8
                    ),
                    padding=ft.padding.all(12),
                    border_radius=8,
                    bgcolor=COR_CARD,
                ),
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
        
        if not state["alunos_data"] and not GLOBAL_ALUNOS:
            lista_alunos_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.ProgressRing(color=COR_PRIMARY),
                        ft.Text("Sincronizando contatos...", color=COR_TEXT_SEC)
                    ], horizontal_alignment="center"),
                    padding=50, alignment=ft.alignment.center
                )
            )
            try: page.update()
            except: pass
            return

        if not state["alunos_data"]:
            lista_alunos_col.controls.append(
                ft.Container(
                    content=ft.Text("Nenhum aluno encontrado ou ativo no CRM.", color=COR_TEXT_SEC),
                    padding=50, alignment=ft.alignment.center
                )
            )
            try: page.update()
            except: pass
            return

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

    def abrir_diagnostico(e=None):
        def check_crm():
            try:
                r = requests.get(SITE_URL, timeout=3)
                return True if r.status_code == 200 else False
            except: return False

        def check_catraca():
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.5)
                    s.connect(("192.168.1.100", 1001))
                    return True
            except: return False

        def check_camera():
            if "cv2" not in sys.modules: return False
            for i in ["/dev/video0", 0, 1]:
                try:
                    c = cv2.VideoCapture(i)
                    if c.isOpened():
                        c.release(); return True
                except: pass
            return False

        def test_relay():
            import socket
            for pta in [1001, 3000, 5000]:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(2); sock.connect(("192.168.1.100", pta)); sock.sendall(b"lgu\x00Teste Diagnostico"); break
                except: pass
            btn_test.text = "COMANDO ENVIADO"; btn_test.disabled = True; page.update()

        status_crm = check_crm()
        status_cat = check_catraca()
        status_cam = check_camera()
        
        def diag_card(label, status, details, icon_name):
            cor = COR_SUCCESS if status else COR_ERROR
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon_name, color=cor, size=24),
                        ft.Text(label, weight="bold", size=16, color="#ffffff", expand=True),
                        ft.Container(
                            content=ft.Text("ONLINE" if status else "OFFLINE", color=cor, size=10, weight="bold"),
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border=ft.border.all(1, cor),
                            border_radius=4
                        )
                    ], alignment="spaceBetween"),
                    ft.Text(details if status else "Falha de comunicação ou hardware não detectado", color=COR_TEXT_SEC, size=12),
                ], spacing=8),
                padding=20,
                bgcolor=COR_CARD,
                border_radius=12,
                border=ft.border.all(1, COR_CARD_HIGH if status else COR_ERROR + "44")
            )

        btn_test = ft.ElevatedButton(
            "TESTAR ABERTURA MANUAL", 
            icon="vpn_key", 
            on_click=lambda _: test_relay(), 
            style=ft.ButtonStyle(
                bgcolor=COR_PRIMARY, 
                color="#ffffff", 
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=20
            )
        )

        dlg = ft.AlertDialog(
            title=ft.Text("DIAGNÓSTICO DO SISTEMA", font_family="Space Grotesk", weight="bold"),
            bgcolor=COR_BG,
            content=ft.Container(
                width=500,
                height=650,
                content=ft.Column([
                    ft.Text("STATUS DE CONEXÃO E HARDWARE", color=COR_TEXT_SEC, size=11, weight="bold", opacity=0.7),
                    diag_card("SERVIDOR CRM", status_crm, f"IP: academiarocksfit.com.br (Porta 443)", "cloud_done"),
                    diag_card("CATRACA (RELÉ)", status_cat, f"IP: 192.168.1.100 (Porta 1001)", "dashboard"),
                    diag_card("CÂMERA BIOMÉTRICA", status_cam, "Dispositivo USB /dev/video0 Ativo", "videocam"),
                    diag_card("MOTOR NEURAL", FR_DISPONIVEL, f"{len(GLOBAL_PERFIS)} alunos mapeados em memória", "memory"),
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("AÇÕES RÁPIDAS", color=COR_TEXT_SEC, size=11, weight="bold", opacity=0.7),
                    ft.Container(content=btn_test, alignment=ft.alignment.center)
                ], spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
            ),
            actions=[ft.TextButton("FECHAR", on_click=lambda _: (setattr(dlg, 'open', False), page.update()))],
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

    layout = ft.Row(
        [
            sidebar,
            center_panel,
        ],
        expand=True, spacing=0
    )

    # ==========================
    # ROTEAMENTO DE TELAS (DASHBOARD vs CÂMERA)
    # ==========================
    def route_change(route):
        page.views.clear()
        
        if "/monitor" in page.route:
            page.title = "Monitor - Rocks Fit"
            surf = "#0e0e0e"
            surf_low = "#131313"
            surf_high = "#201f1f"
            surf_highest = "#262626"
            primary = "#ff7a2f"
            
            titulo = ft.Row([
                ft.Text("BIOMETRIA ", size=36, font_family="Space Grotesk", weight="bold", italic=True, color="#ffffff"),
                ft.Text("ATIVA", size=36, font_family="Space Grotesk", weight="bold", italic=True, color=primary)
            ], spacing=0)
            subtitulo = ft.Text("APROXIME-SE PARA VALIDAR", size=14, color="#adaaaa", weight="w500")
            
            img_cam = ft.Image(
                src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
                fit=ft.ImageFit.CONTAIN,
                expand=True,
            )
            # Wrapper centralizado
            img_cam_wrapper = ft.Container(
                content=img_cam,
                expand=True,
                alignment=ft.Alignment(0, 0),
            )

            # Overlay: borda laranja sobre todo o quadro
            cam_overlay = ft.Container(
                bgcolor="transparent",
                border=ft.border.all(2, "#ff7a2f66"),
                border_radius=16,
                expand=True,
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
                margin=ft.padding.only(bottom=20)
            )

            cam_container = ft.Container(
                content=ft.Stack(
                    [
                        img_cam_wrapper,
                        cam_overlay,
                        ft.Container(content=badge_cam_status, alignment=ft.alignment.bottom_center),
                    ],
                    expand=True,
                ),
                expand=True,
                bgcolor=surf_highest,
                border_radius=16,
                margin=ft.padding.only(top=10),
                border=ft.border.all(1, "#ffffff10"),
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            )
            
            left_col = ft.Column(
                [titulo, subtitulo, cam_container],
                expand=True,
                spacing=4,
            )
            
            # PAINEL DIREITO: foto proeminente do aluno identificado
            lbl_nome = ft.Text(
                "AGUARDANDO", size=22, font_family="Space Grotesk",
                weight="bold", color="#ffffff", text_align=ft.TextAlign.CENTER
            )
            lbl_matricula = ft.Text(
                "Posicione-se em frente à câmera", size=13,
                color="#adaaaa", text_align=ft.TextAlign.CENTER
            )
            lbl_msg = ft.Text(
                "", size=13, color="#adaaaa", text_align=ft.TextAlign.CENTER
            )

            # Foto grande placeholder
            img_perfil = ft.Image(
                src="", width=180, height=180,
                border_radius=90, fit=ft.ImageFit.COVER,
                visible=False
            )
            icon_placeholder = ft.Container(
                content=ft.Icon("person", color="#555555", size=80),
                width=180, height=180, border_radius=90,
                bgcolor=surf_highest,
                border=ft.border.all(3, "#333333"),
                alignment=ft.Alignment(0, 0),
                visible=True,
            )
            foto_stack = ft.Stack(
                [icon_placeholder, img_perfil],
                width=180, height=180
            )

            lbl_status_tag = ft.Text("INATIVO", size=14, weight="bold", color="#ff7351")
            status_container = ft.Container(
                content=ft.Row([
                    ft.Container(width=10, height=10, border_radius=5, bgcolor="#ff7351"),
                    lbl_status_tag,
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#ff735133",
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                border_radius=20,
            )

            card_perfil = ft.Container(
                content=ft.Column([
                    ft.Container(content=foto_stack, alignment=ft.Alignment(0, 0), margin=ft.padding.only(bottom=20)),
                    ft.Container(content=lbl_nome, alignment=ft.Alignment(0, 0)),
                    ft.Container(content=lbl_matricula, alignment=ft.Alignment(0, 0), margin=ft.padding.only(bottom=16)),
                    ft.Container(content=status_container, alignment=ft.Alignment(0, 0)),
                    ft.Divider(color=surf_highest, height=28),
                    ft.Row([
                        ft.Text("UNIDADE", size=12, color="#adaaaa"),
                        ft.Text("ROCKS FIT #01", size=13, weight="bold", color="#ffffff")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(content=lbl_msg, alignment=ft.Alignment(0, 0), margin=ft.padding.only(top=8)),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                bgcolor=surf_high, padding=30, border_radius=20, expand=True,
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
                gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#ff9159", "#ff7a2f"]),
                padding=30, border_radius=20, margin=ft.padding.only(top=16)
            )

            right_col = ft.Container(content=ft.Column([card_perfil, card_capacidade], expand=True), width=380, margin=ft.padding.only(left=40))
            
            monitor_layout = ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Text("ROCKS FIT", size=24, font_family="Space Grotesk", weight="bold", italic=True, color=primary),
                            ft.Row([ft.Text("Biometria", color=primary, weight="bold"), ft.Text("Dashboard", color="#adaaaa"), ft.Text("Membros", color="#adaaaa")], spacing=30),
                            ft.Row([ft.Icon("sensors", color=primary), ft.Icon("notifications", color=primary)], spacing=15)
                        ], alignment="spaceBetween"), margin=ft.padding.only(bottom=16)
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
                        ], alignment="spaceBetween"), margin=ft.padding.only(top=10)
                    )
                ], expand=True), expand=True, padding=ft.padding.symmetric(horizontal=30, vertical=20), bgcolor=surf
            )
            
            # Para qualquer loop anterior antes de abrir um novo
            if hasattr(page, "_cam_estado") and page._cam_estado:
                page._cam_estado["rodando"] = False
                time.sleep(0.5) # Aumentado para garantir liberação do hardware
            camera_estado = {"rodando": True}
            page._cam_estado = camera_estado

            def _set_aguardando():
                lbl_nome.value = "AGUARDANDO"
                lbl_nome.color = "#ffffff"
                lbl_matricula.value = "Posicione-se em frente à câmera"
                lbl_msg.value = ""
                lbl_status_tag.value = "INATIVO"
                lbl_status_tag.color = "#ff7351"
                status_container.bgcolor = "#ff735133"
                status_container.content.controls[0].bgcolor = "#ff7351"
                img_perfil.visible = False
                icon_placeholder.visible = True
                lbl_cam_status.value = "AGUARDANDO..."
                badge_cam_status.bgcolor = primary
                try: page.update()
                except: pass

            def _set_identificado(data, liberado):
                nome = data.get("nome", "ALUNO").upper()
                mat = str(data.get("matricula", ""))
                furl = data.get("foto_url", "")
                lbl_nome.value = nome
                lbl_matricula.value = f"Matrícula: {mat}"
                if furl:
                    if furl.startswith("/"): furl = f"{SITE_URL}{furl}"
                    img_perfil.src = furl
                    img_perfil.visible = True
                    icon_placeholder.visible = False
                else:
                    img_perfil.visible = False
                    icon_placeholder.visible = True
                if liberado:
                    lbl_status_tag.value = "✔ LIBERADO"
                    lbl_status_tag.color = "#000000"
                    status_container.bgcolor = "#2ecc71"
                    status_container.content.controls[0].bgcolor = "#000000"
                    lbl_cam_status.value = "ACESSO PERMITIDO"
                    badge_cam_status.bgcolor = "#2ecc71"
                    lbl_nome.color = "#2ecc71"
                    lbl_msg.value = "✔ Acesso liberado"
                    lbl_msg.color = "#2ecc71"
                else:
                    lbl_status_tag.value = "✖ BLOQUEADO"
                    lbl_status_tag.color = "#000000"
                    status_container.bgcolor = "#e74c3c"
                    status_container.content.controls[0].bgcolor = "#000000"
                    lbl_cam_status.value = "ACESSO NEGADO"
                    badge_cam_status.bgcolor = "#e74c3c"
                    lbl_nome.color = "#e74c3c"
                    lbl_msg.value = "✖ Plano vencido ou bloqueado"
                    lbl_msg.color = "#e74c3c"
                try: page.update()
                except: pass

            def loop_camera():
                if "cv2" not in sys.modules:
                    print("⚠️ cv2 não disponível – câmera desativada")
                    return
                
                # Tenta travar o acesso à câmera (aguarda até 5s pela liberação de outra aba)
                if not CAM_LOCK.acquire(blocking=True, timeout=5.0):
                    print("📷 Câmera bloqueada por outra sessão.")
                    lbl_cam_status.value = "CÂMERA EM USO (AGUARDE...)"
                    badge_cam_status.bgcolor = "#f39c12"
                    try: page.update()
                    except: pass
                    return

                cap = None
                try:
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    cooldown = 0
                    votos = {}
                    voto_lider_anterior = None
                    frame_count = 0
                    last_fr_time = 0

                    for device in ["/dev/video0", "/dev/video1", 0, 1]:
                        # ... (keep existing device logic)
                        for backend in [cv2.CAP_V4L, cv2.CAP_FFMPEG, cv2.CAP_ANY]:
                            try:
                                c = cv2.VideoCapture(device, backend)
                                if c.isOpened():
                                    c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                    c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                    ret, frame = c.read()
                                    if ret and frame is not None:
                                        cap = c
                                        print(f"✅ Câmera aberta: {device} backend={backend}")
                                        break
                                    c.release()
                            except Exception: pass
                        if cap: break

                    if not cap:
                        print("⚠️ Nenhuma câmera disponível")
                        lbl_cam_status.value = "CÂMERA NÃO ENCONTRADA"
                        badge_cam_status.bgcolor = "#e74c3c"
                        try: page.update()
                        except: pass
                        return
                    
                    while camera_estado["rodando"] and cap.isOpened():
                        ret, frame = cap.read()
                        if not ret: break
                        
                        frame_count += 1
                        frame = cv2.flip(frame, 1)
                        
                        # Processa Haar apenas a cada 2 frames para economizar CPU
                        faces = []
                        if frame_count % 2 == 0:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                            
                        for (x,y,w,h) in faces:
                            cv2.rectangle(frame, (x,y), (x+w, y+h), (242, 113, 33), 2)
                            
                        # Reconhecimento Neural: apenas se houver rosto e após cooldown e delay entre verificações
                        now = time.time()
                        if len(faces) > 0 and cooldown <= 0 and (now - last_fr_time) > 1.0:
                            last_fr_time = now
                            (x,y,w,h) = faces[0]
                            perfis = GLOBAL_PERFIS
                            melhor_aluno = None

                            if not perfis:
                                lbl_cam_status.value = "SEM PERFIS"; badge_cam_status.bgcolor = "#e74c3c"
                                try: page.update()
                                except: pass
                                cooldown = 60
                            elif FR_DISPONIVEL:
                                # Reduz imagem para o neural ser instantâneo
                                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                                h_small, w_small = small_frame.shape[:2]
                                rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                                rgb_small = np.ascontiguousarray(rgb_small)
                                
                                # Escala e CLIP para evitar crash no dlib (coordenadas fora da imagem)
                                top = max(0, int(y/2))
                                right = min(w_small, int((x+w)/2))
                                bottom = min(h_small, int((y+h)/2))
                                left = max(0, int(x/2))
                                
                                # Garante que a área é válida
                                if right > left and bottom > top:
                                    with FR_LOCK:
                                        face_encs = fr.face_encodings(rgb_small, [(top, right, bottom, left)], num_jitters=0)
                                        if face_encs:
                                            encoding_webcam = face_encs[0]
                                            conhecidos_encs = [p['encoding'] for p in perfis.values() if 'encoding' in p]
                                            conhecidos_dados = [p['data'] for p in perfis.values() if 'encoding' in p]
                                            if conhecidos_encs:
                                                distancias = fr.face_distance(conhecidos_encs, encoding_webcam)
                                                min_idx = np.argmin(distancias)
                                                if distancias[min_idx] < 0.5:
                                                    melhor_aluno = conhecidos_dados[min_idx]
                                                    print(f"🧬 Neural: {melhor_aluno['nome']} (dist: {distancias[min_idx]:.3f})")
                            else:
                                # Fallback ORB (já otimizado)
                                margin = int(w * 0.2); x1, y1 = max(0, x - margin), max(0, y - margin); x2, y2 = min(frame.shape[1], x + w + margin), min(frame.shape[0], y + h + margin)
                                face_roi = frame[y1:y2, x1:x2]; gray_webcam = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(cv2.cvtColor(cv2.resize(face_roi, (200, 200)), cv2.COLOR_BGR2GRAY))
                                orb = cv2.ORB_create(700); _, des_webcam = orb.detectAndCompute(gray_webcam, None)
                                if des_webcam is not None:
                                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False); melhor_score = 0
                                    for mat, perfil in perfis.items():
                                        if 'des' not in perfil: continue
                                        matches = bf.knnMatch(des_webcam, perfil['des'], k=2)
                                        bons = [m for m, n in matches if m.distance < 0.75 * n.distance]
                                        if len(bons) > melhor_score: melhor_score = len(bons); melhor_aluno = perfil['data']
                                    if melhor_aluno and melhor_score >= 10:
                                        if str(melhor_aluno['matricula']) in perfis and 'img' in perfis[str(melhor_aluno['matricula'])]:
                                            res = cv2.matchTemplate(gray_webcam.astype('float32'), perfis[str(melhor_aluno['matricula'])]['img'].astype('float32'), cv2.TM_CCOEFF_NORMED)
                                            if res[0][0] < 0.35: melhor_aluno = None

                            if melhor_aluno:
                                mat_lider = str(melhor_aluno['matricula'])
                                if mat_lider != voto_lider_anterior: votos = {}; voto_lider_anterior = mat_lider
                                votos[mat_lider] = votos.get(mat_lider, 0) + 1
                                if votos[mat_lider] >= (2 if FR_DISPONIVEL else 10):
                                    print(f"✅ Identificado: {melhor_aluno['nome']}"); votos = {}; voto_lider_anterior = None
                                    try:
                                        r = requests.get(f"{SITE_URL}/api/catraca-check/{melhor_aluno['matricula']}/?token={SYNC_TOKEN}", timeout=3)
                                        data = r.json() if r.status_code == 200 else melhor_aluno
                                    except Exception: data = melhor_aluno
                                    liberado = data.get("status", "") in ["ativo", "liberado"]
                                    _set_identificado(data, liberado)
                                    if liberado:
                                        import socket
                                        for pta in [1001, 3000, 5000]:
                                            try:
                                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                                                    sock.settimeout(1); sock.connect(("192.168.1.100", pta)); sock.sendall(b"lgu\x00Liberou Entrada"); break
                                            except: pass
                                    cooldown = 120
                                    threading.Thread(target=lambda: (time.sleep(4), _set_aguardando()), daemon=True).start()

                        if cooldown > 0: cooldown -= 1
                        
                        # Atualiza UI apenas a cada 2 frames para reduzir banda
                        if frame_count % 2 == 0:
                            try:
                                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                                img_cam.src_base64 = base64.b64encode(buffer).decode('utf-8')
                                page.update()
                            except Exception:
                                # Se der erro no update, a aba pode ter sido fechada
                                pass
                        time.sleep(0.01)
                except Exception as e: print("Erro na câmera Flet:", e)
                finally:
                    if cap: cap.release()
                    try:
                        CAM_LOCK.release()
                    except:
                        pass

            threading.Thread(target=loop_camera, daemon=True).start()
            page.views.append(ft.View("/monitor", [monitor_layout], bgcolor=surf, padding=0))
        else:
            page.title = "ROCKS FIT - RECEPÇÃO"
            page.views.append(ft.View("/", [layout], padding=0, bgcolor=COR_BG))
        page.update()

    def view_pop(view):
        if "/monitor" in page.route: return
        page.views.clear(); page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    sync_crm()
    page.go(page.route or "/")

if __name__ == "__main__":
    # Força o uso do backend X11 no Linux para evitar conflitos com Wayland
    if sys.platform.startswith("linux"):
        os.environ["GDK_BACKEND"] = "x11"
        
    print("🚀 Iniciando Módulo de Recepção Rocks-Fit...")
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        port=8552, 
        route_url_strategy="path"
    )