import flet as ft
import os, sys

# Evitar travamentos do Flet no Linux (Wayland/X11)
if sys.platform.startswith("linux"):
    # os.environ["GDK_BACKEND"] = "x11" # Removido para permitir auto-detecção
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"

from datetime import datetime, timedelta
import random
import requests
import threading
import time
import base64
from flask import Flask, jsonify, request
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

try:
    from biometria_fprint import BiometriaFPrint
    FPRINT_DISPONIVEL = True
except ImportError:
    FPRINT_DISPONIVEL = False

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


# --- API BRIDGE PARA O CRM (FLASK) ---
api_app = Flask(__name__)
manager_global = None
BIOMETRIA_BUSY = False # Flag para evitar conflito entre Verificação e Cadastro
page_global = None

@api_app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@api_app.route('/api/enroll/<matricula>', methods=['GET', 'POST', 'OPTIONS'])
def api_enroll(matricula):
    global BIOMETRIA_BUSY
    if not manager_global:
        return jsonify({"success": False, "error": "Hardware não inicializado"}), 500
    
    # Notifica a UI do Flet para abrir o quadro
    if page_global:
        # Busca o aluno no cache global
        aluno = next((a for a in GLOBAL_ALUNOS if str(a.get("matricula")) == str(matricula)), {"matricula": matricula, "nome": "Aluno Externo"})
        page_global.pubsub.send_all({"type": "open_enroll", "aluno": aluno})
        
    return jsonify({"success": True, "message": "Quadro de captura aberto no terminal de recepção."})

def run_api():
    print("🌐 API Bridge iniciada em http://0.0.0.0:8553")
    api_app.run(host='0.0.0.0', port=8553, debug=False, threaded=True)

threading.Thread(target=run_api, daemon=True).start()


import getpass

def trigger_catraca(msg="Liberado"):
    import socket
    # Comando de abertura + comando de bip para a controladora RocksFit
    for pta in [1001, 3000, 5000]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                sock.connect(("192.168.1.100", pta))
                # Envia comando de liberação
                sock.sendall(f"lgu\x00{msg}".encode())
                time.sleep(0.1)
                # Envia comando de bip sonoro
                sock.sendall(b"bip\x00")
                return True
        except:
            pass
    return False

def abrir_cadastro_digital(aluno, page, biometria_manager, render_main_content, state):
    global BIOMETRIA_BUSY
    if BIOMETRIA_BUSY:
        return
    
    BIOMETRIA_BUSY = True
    nome = aluno.get("nome", "Membro").upper()
    matricula = str(aluno.get("matricula"))
    
    # Cores Industrial RKS
    COR_GLASS = "#ffffff08"
    COR_ACCENT = COR_PRIMARY
    
    status_captura = ft.Text("AGUARDANDO SELEÇÃO", color=COR_TEXT_SEC, size=12, weight="bold")
    log_messages = ft.ListView(expand=True, spacing=3, padding=5)

    def add_log(msg, color=COR_TEXT_SEC):
        timestamp = time.strftime("%H:%M:%S")
        log_messages.controls.append(
            ft.Text(f"[{timestamp}] {msg}", color=color, size=11, font_family="monospace")
        )
        if len(log_messages.controls) > 15:
            log_messages.controls.pop(0)
        page.update()

    def sync_to_crm():
        try:
            add_log("Sincronizando com servidor CRM...", COR_ACCENT)
            resp = requests.post(f"{SITE_URL}/api/biometria-save/{matricula}/", timeout=8)
            if resp.status_code == 200:
                add_log("✔ Sucesso: Digital vinculada no CRM.", COR_SUCCESS)
            else:
                add_log(f"⚠ Erro CRM: {resp.status_code}", COR_ERROR)
        except:
            add_log("✖ Falha de rede na sincronia.", COR_ERROR)

    def process_enroll(finger, label):
        if not biometria_manager:
            add_log("Hardware biométrico não configurado.", COR_ERROR)
            return

        # Verifica se já existe e pergunta qual ação tomar
        if biometria_manager.check_exists(matricula, finger):
            def handle_action(action):
                page.overlay.remove(confirm_dlg)
                safe_update()
                
                if action == "enroll":
                    _start_enroll_thread(finger, label)
                elif action == "delete":
                    if biometria_manager.apagar_digital_local(matricula, finger):
                        add_log(f"🗑️ Registro do {label} removido.", COR_WARNING)
                        # Remove da lista local para atualizar UI imediatamente
                        if finger in enrolled_fingers:
                            enrolled_fingers.remove(finger)
                        update_fingers_ui()
                    else:
                        add_log("Erro ao remover registro.", COR_ERROR)

            confirm_dlg = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.SETTINGS, color=COR_ACCENT), ft.Text("Gestão de Digital")]),
                content=ft.Text(f"O {label} já possui um registro. O que deseja fazer?"),
                actions=[
                    ft.ElevatedButton("Recadastrar", icon=ft.Icons.REFRESH, on_click=lambda _: handle_action("enroll"), bgcolor="#FF8C00", color="white"),
                    ft.ElevatedButton("Apagar", icon=ft.Icons.DELETE_FOREVER, on_click=lambda _: handle_action("delete"), bgcolor="#CC0000", color="white"),
                    ft.TextButton("Cancelar", on_click=lambda _: (page.overlay.remove(confirm_dlg), safe_update()))
                ],
                actions_alignment="end"
            )
            page.overlay.append(confirm_dlg)
            confirm_dlg.open = True
            safe_update()
        else:
            _start_enroll_thread(finger, label)

    def _start_enroll_thread(finger, label):
        status_captura.value = f"CAPTURA ATIVA: {label.upper()}"
        status_captura.color = COR_ACCENT
        add_log(f"Posicione o {label} no sensor agora...", COR_ACCENT)
        page.update()

        def _thread():
            proc = biometria_manager.enroll(matricula, finger)
            if proc:
                try:
                    # O fprintd-enroll emite várias mensagens durante os toques
                    while True:
                        line = proc.stdout.readline()
                        if not line: break
                        line = line.strip().lower()
                        if "enroll-stage-passed" in line:
                            add_log("✔ Toque capturado. Continue...", COR_SUCCESS)
                        elif "enroll-retry-scan" in line:
                            add_log("⚠ Falha no toque. Tente novamente.", COR_WARNING)
                        elif "enroll-completed" in line:
                            biometria_manager.guardar_arquivo_local(matricula, finger)
                            add_log(f"✅ FINALIZADO: {label} cadastrado com sucesso!", COR_SUCCESS)
                            sync_to_crm()
                            update_fingers_ui()
                            render_main_content()
                            break
                    
                    proc.wait(timeout=5)
                    if proc.returncode != 0 and "enroll-completed" not in status_captura.value:
                        add_log(f"⚠ Processo interrompido ou falhou (cod {proc.returncode}).", COR_ERROR)
                except Exception as e:
                    add_log(f"✖ Erro técnico: {str(e)}", COR_ERROR)
                finally:
                    status_captura.value = "PRONTO PARA NOVA CAPTURA"
                    status_captura.color = COR_SUCCESS
                    page.update()
            else:
                add_log("Falha ao inicializar driver fprintd.", COR_ERROR)
        
        threading.Thread(target=_thread, daemon=True).start()

    def delete_finger(finger, label):
        if biometria_manager.apagar_digital_local(matricula, finger):
            add_log(f"🗑️ Registro do {label} removido.", COR_WARNING)
            update_fingers_ui()
            render_main_content()
        else:
            add_log("Erro ao remover registro.", COR_ERROR)

    def create_finger_box(finger, label, x, y):
        is_enrolled = finger in biometria_manager.get_enrolled_fingers(matricula)
        
        return ft.Container(
            content=ft.Stack([
                # Botão Principal
                ft.Container(
                    content=ft.Icon(
                        "fingerprint" if not is_enrolled else "check_circle",
                        color="#ffffff" if not is_enrolled else COR_SUCCESS, 
                        size=24
                    ),
                    width=54, height=54,
                    border_radius=27,
                    bgcolor=COR_CARD_HIGH if not is_enrolled else "#2ecc7122",
                    border=ft.border.all(2, COR_ACCENT if not is_enrolled else COR_SUCCESS),
                    animate=ft.Animation(300, "decelerate"),
                    on_click=lambda _: process_enroll(finger, label),
                    tooltip=f"Cadastrar {label}",
                    alignment=ft.alignment.center
                ),
                # Botão Deletar
                ft.IconButton(
                    icon="cancel", icon_color=COR_ERROR, icon_size=18,
                    width=24, height=24,
                    left=38, top=-5,
                    on_click=lambda _: delete_finger(finger, label),
                    visible=is_enrolled,
                    padding=0,
                    tooltip="Excluir biometria"
                ),
                # Label
                ft.Container(
                    content=ft.Text(label, size=8, weight="bold", color=COR_TEXTO),
                    bgcolor="#000000aa",
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=4,
                    left=-5, top=58,
                    width=64,
                    alignment=ft.alignment.center
                )
            ]),
            left=x,
            top=y,
            width=70, height=80
        )

    FINGERS_MAPPING = [
        {"id": "left-pinky",   "label": "Mínimo E",   "left": 350, "top": 300},
        {"id": "left-ring-finger",   "label": "Anelar E",   "left": 402, "top": 264},
        {"id": "left-middle-finger",    "label": "Médio E",    "left": 440, "top": 251},
        {"id": "left-index-finger","label": "Indic. E",   "left": 490, "top": 263},
        {"id": "left-thumb",  "label": "Polegar E",  "left": 544, "top": 358},
        
        {"id": "right-thumb",  "label": "Polegar D",  "left": 625, "top": 361},
        {"id": "right-index-finger","label": "Indic. D",   "left": 687, "top": 265},
        {"id": "right-middle-finger",    "label": "Médio D",    "left": 774, "top": 266},
        {"id": "right-ring-finger",   "label": "Anelar D",   "left": 731, "top": 250},
        {"id": "right-pinky",   "label": "Mínimo D",   "left": 808, "top": 313},
    ]

    # Pre-busca os dedos cadastrados para evitar 10 acessos ao disco no loop
    enrolled_fingers = biometria_manager_global.get_enrolled_fingers(aluno['matricula']) if biometria_manager_global else []

    LEFT_HAND_SVG = """<svg viewBox="0 0 260 420" xmlns="http://www.w3.org/2000/svg" width="260" height="420"><defs><filter id="glow"><feGaussianBlur stdDeviation="2.5" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><path d="M 40 260 Q 20 320 30 390 Q 50 420 130 415 Q 200 412 220 390 Q 240 360 235 290 Q 230 250 220 230 L 200 210 L 170 215 L 140 212 L 115 215 L 85 212 L 55 225 Z" fill="none" stroke="#FF8C00" stroke-width="1" opacity="0.4" filter="url(#glow)"/><path d="M 40 225 Q 28 200 22 165 Q 18 140 25 120 Q 30 108 42 110 Q 54 112 58 128 Q 62 148 60 175 Q 58 200 60 225 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 70 220 Q 60 185 58 145 Q 57 110 62 90 Q 67 76 80 76 Q 93 76 97 92 Q 101 112 100 148 Q 98 182 95 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 105 215 Q 97 175 96 130 Q 96 92 100 72 Q 105 58 118 57 Q 131 57 136 72 Q 141 90 140 132 Q 138 175 135 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 145 215 Q 140 178 140 138 Q 141 100 145 82 Q 150 68 162 68 Q 175 68 179 83 Q 183 100 182 138 Q 180 178 175 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 195 260 Q 215 245 228 225 Q 238 208 235 290 Q 232 310 220 310 Q 208 310 200 295 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 195 260 Q 205 240 218 220 Q 230 200 240 195 Q 252 192 255 205 Q 258 220 248 240 Q 237 260 222 275 Q 210 285 200 282 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/></svg>"""
    RIGHT_HAND_SVG = """<svg viewBox="0 0 260 420" xmlns="http://www.w3.org/2000/svg" width="260" height="420"><defs><filter id="glow"><feGaussianBlur stdDeviation="2.5" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><path d="M 220 260 Q 240 320 230 390 Q 210 420 130 415 Q 60 412 40 390 Q 20 360 25 290 Q 30 250 40 230 L 60 210 L 90 215 L 120 212 L 145 215 L 175 212 L 205 225 Z" fill="none" stroke="#FF8C00" stroke-width="1" opacity="0.4" filter="url(#glow)"/><path d="M 220 225 Q 232 200 238 165 Q 242 140 235 120 Q 230 108 218 110 Q 206 112 202 128 Q 198 148 200 175 Q 202 200 200 225 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 190 220 Q 200 185 202 145 Q 203 110 198 90 Q 193 76 180 76 Q 167 76 163 92 Q 159 112 160 148 Q 162 182 165 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 155 215 Q 163 175 164 130 Q 164 92 160 72 Q 155 58 142 57 Q 129 57 124 72 Q 119 90 120 132 Q 122 175 125 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 115 215 Q 120 178 120 138 Q 119 100 115 82 Q 110 68 98 68 Q 85 68 81 83 Q 77 100 78 138 Q 80 178 85 215 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 65 260 Q 45 245 32 225 Q 22 208 25 290 Q 28 310 40 310 Q 52 310 60 295 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/><path d="M 65 260 Q 55 240 42 220 Q 30 200 20 195 Q 8 192 5 205 Q 2 220 12 240 Q 23 260 38 275 Q 50 285 60 282 Z" fill="none" stroke="#FF8C00" stroke-width="1.5" opacity="0.6" filter="url(#glow)"/></svg>"""

    def finger_button(finger: dict) -> ft.GestureDetector:
        """Botão circular que pode ser arrastado para calibração de posição."""
        id_dedo = finger["id"]
        possuo_digital = id_dedo in enrolled_fingers
        
        # Container do botão (Fundo)
        btn_circle = ft.Container(
            width=30, height=30,
            border_radius=15,
            bgcolor="#151515" if not possuo_digital else "#FF8C0020",
            border=ft.border.all(1.5, COR_ACCENT if not possuo_digital else "#00FF00"),
            content=ft.Icon(
                ft.Icons.FINGERPRINT, 
                color=COR_ACCENT if not possuo_digital else "#00FF00", 
                size=16
            ),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=COR_ACCENT + "40" if not possuo_digital else "#00FF0040")
        )

        # Label externa para orientação
        btn_content = ft.Column([
            btn_circle,
            ft.Text(finger["label"], size=8, color="#ffffff", weight="bold")
        ], horizontal_alignment="center", spacing=2)

        def on_pan_update(e: ft.DragUpdateEvent):
            gd.top = max(0, gd.top + e.delta_y)
            gd.left = max(0, gd.left + e.delta_x)
            gd.update()
            print(f"📍 CALIBRAÇÃO: '{id_dedo}' -> left: {int(gd.left)}, top: {int(gd.top)}")

        gd = ft.GestureDetector(
            content=btn_content,
            key=f"finger_{id_dedo}", 
            left=finger["left"],
            top=finger["top"],
            on_pan_update=on_pan_update,
            on_tap=lambda _: process_enroll(id_dedo, finger["label"]),
            mouse_cursor=ft.MouseCursor.MOVE
        )
        return gd

    # Criação ESTÁTICA para garantir os 10 botões
    controls_list = [
        ft.Image(src="media/imagens/rocksfit_hand_schematic.png", width=1200, height=650, fit="contain", opacity=0.9, gapless_playback=True),
    ]
    
    finger_controls = {}
    for f in FINGERS_MAPPING:
        btn = finger_button(f)
        finger_controls[f["id"]] = btn
        controls_list.append(btn)

    hands_stack = ft.Stack(controls_list, width=1200, height=650)

    def update_fingers_ui():
        """Atualiza apenas o estado visual dos botões existentes, sem recriá-los (EVITA CRASH)"""
        try:
            for fid, btn in finger_controls.items():
                exists = biometria_manager_global.check_exists(matricula, fid)
                # Navega na árvore: GestureDetector -> Column -> Container
                circle = btn.content.controls[0]
                circle.bgcolor = "#151515" if not exists else "#FF8C0020"
                circle.border = ft.border.all(1.5, COR_ACCENT if not exists else "#00FF00")
                circle.content.color = COR_ACCENT if not exists else "#00FF00"
                circle.shadow.color = COR_ACCENT + "40" if not exists else "#00FF0040"
            
            hands_stack.update()
        except Exception as e:
            print(f"⚠️ Erro ao atualizar UI dedos: {e}")

    def fechar_dlg(e):
        global BIOMETRIA_BUSY
        BIOMETRIA_BUSY = False
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        bgcolor="transparent",
        content_padding=0,
        content=ft.Container(
            width=1200, height=850,
            bgcolor=COR_BG,
            border_radius=24,
            border=ft.border.all(1, "#ffffff10"),
            padding=30,
            content=ft.Column([
                # Header
                ft.Row([
                    ft.Column([
                        ft.Text("MÓDULO DE CADASTRO BIOMÉTRICO", size=12, weight="bold", color=COR_ACCENT),
                        ft.Text(nome, size=38, weight="black", font_family="Space Grotesk"),
                    ], spacing=2, expand=True),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("MATRÍCULA", size=10, color=COR_TEXT_SEC, weight="bold"),
                            ft.Text(matricula, size=24, weight="bold", font_family="monospace", color=COR_ACCENT),
                        ], spacing=0, horizontal_alignment="center"),
                        padding=15, bgcolor=COR_CARD, border_radius=12, border=ft.border.all(1, "#ffffff08")
                    ),
                    ft.IconButton(ft.Icons.CLOSE, on_click=fechar_dlg, icon_color=COR_TEXT_SEC)
                ], alignment="spaceBetween"),
                
                ft.Divider(height=40, color="#ffffff08"),
                
                # Área de interação
                ft.Row([
                    # Coluna Esquerda: Log e Status
                    ft.Column([
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon("sensors", color=COR_ACCENT, size=20),
                                    status_captura,
                                ], spacing=10),
                                ft.Text("Selecione um dedo para iniciar", size=11, color=COR_TEXT_SEC),
                            ]),
                            bgcolor=COR_GLASS, padding=20, border_radius=16, border=ft.border.all(1, "#ffffff05")
                        ),
                        ft.Container(height=20), # Espaçador
                ft.Text("LOG DE OPERAÇÃO", size=10, weight="bold", color=COR_TEXT_SEC),
                        ft.Container(
                            expand=True, bgcolor="#000000", border_radius=16, padding=15,
                            border=ft.border.all(1, "#ffffff05"),
                            content=log_messages
                        ),
                        ft.ElevatedButton(
                            "CONCLUIR CADASTRO", 
                            on_click=fechar_dlg,
                            width=300, height=50,
                            style=ft.ButtonStyle(
                                bgcolor=COR_ACCENT, color="#ffffff",
                                shape=ft.RoundedRectangleBorder(radius=12)
                            )
                        )
                    ], width=350, spacing=10),
                    
                    # Coluna Direita: Foto Mãos (COM SCROLL PARA GARANTIR OS 10)
                    ft.Container(
                        expand=True,
                        bgcolor="#080808",
                        border_radius=20,
                        border=ft.border.all(1, "#ffffff05"),
                        content=ft.Row([hands_stack], scroll=ft.ScrollMode.ALWAYS),
                        alignment=ft.alignment.center
                    )
                ], expand=True, spacing=20)
            ], spacing=10)
        )
    )
    
    def safe_update():
        try: page.update()
        except: pass

    page.overlay.append(dlg)
    dlg.open = True
    safe_update()

# Inicialização Global da Biometria
biometria_manager_global = BiometriaFPrint(SITE_URL, SYNC_TOKEN) if FPRINT_DISPONIVEL else None
manager_global = biometria_manager_global

def main(page: ft.Page):
    page.title = "ROCKS FIT - RECEPÇÃO"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COR_BG
    page.window.width = 1400
    page.window.height = 900
    page.window.min_width = 1200
    page.window.min_height = 800
    page.window.maximizable = True
    page.window.minimizable = True
    page.window.resizable = True
    page.window.title_bar_hidden = True  # Oculta a barra do sistema para o visual premium
    page.window.title_bar_buttons_hidden = True
    page.window.center()

    # Garantir diretórios de persistência local
    os.makedirs("BIOMETRIA_DATA/ALUNOS", exist_ok=True)

    # Estado Local da Sessão
    state = {
        "alunos_data": GLOBAL_ALUNOS if GLOBAL_ALUNOS else [],
        "historico": GLOBAL_HISTORICO if GLOBAL_HISTORICO else [],
        "camera_on": False,
        "monitor_ativo": True,
        "alunos_perfis": GLOBAL_PERFIS,
        "current_view": "clientes"
    }

    global page_global
    page_global = page
    
    # Sistema de notificação entre abas
    def on_broadcast(msg):
        if isinstance(msg, dict) and msg.get("type") == "open_enroll":
            aluno = msg.get("aluno")
            abrir_cadastro_digital(aluno, page, biometria_manager_global, render_main_content, state)
        elif msg == "sync_done":
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
    def switch_view(view_name):
        state["current_view"] = view_name
        render_main_content()
        page.update()

    menu_monitoramento = ft.Column(
        [
            create_section_title("MONITORAMENTO"),
            create_menu_item("Clientes", "people", active=state["current_view"] == "clientes", on_click=lambda _: switch_view("clientes")),
            create_menu_item("Biometria", "fingerprint", active=state["current_view"] == "biometria", on_click=lambda _: switch_view("biometria")),
            create_menu_item("Monitor Câmera", "videocam", on_click=lambda _: page.go("/monitor")),
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
        on_click=lambda _: page.go("/monitor"),
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

            # Botão de Digital
            btn_digital = ft.IconButton(
                icon="fingerprint",
                icon_color=COR_PRIMARY,
                tooltip="Cadastrar Digital",
                on_click=lambda e, a=aluno: abrir_cadastro_digital(a, page, biometria_manager_global, render_main_content, state)
            )

            # Card do aluno
            card = ft.Container(
                content=ft.Row(
                    [
                        ft.Row(
                            [avatar_com_indicador, info],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Row([badge, btn_digital], spacing=8),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                bgcolor=COR_CARD,
                border_radius=16,
                padding=ft.padding.all(16),
                on_click=lambda e, a=aluno: abrir_cadastro_digital(a, page, biometria_manager_global, render_main_content, state),
                ink=True,
            )

            lista_alunos_col.controls.append(card)

        if page.views:
            page.update()


    def render_biometria_view():
        biometria_col = ft.ListView(expand=True, spacing=8, padding=ft.padding.only(top=10))
        
        # Filtra alunos que não têm digital (segundo o cache local)
        path_digital = "BIOMETRIA_DATA/ALUNOS"
        os.makedirs(path_digital, exist_ok=True)
        digital_locais = [f.split(".")[0] for f in os.listdir(path_digital) if f.endswith(".finger")]
        
        alunos_pendentes = [a for a in state["alunos_data"] if str(a.get("matricula")) not in digital_locais]
        alunos_cadastrados = [a for a in state["alunos_data"] if str(a.get("matricula")) in digital_locais]
        
        def create_biometria_item(aluno, cadastrado=False):
            nome = str(aluno.get("nome", "ALUNO"))
            mat = str(aluno.get("matricula", "N/D"))
            
            return ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon("fingerprint", color=COR_SUCCESS if cadastrado else COR_WARNING),
                        ft.Column([
                            ft.Text(nome, color=COR_TEXTO, size=14, weight="bold"),
                            ft.Text(f"Matrícula: {mat}", color=COR_TEXT_SEC, size=12),
                        ], spacing=2)
                    ], spacing=15),
                    ft.ElevatedButton(
                        "RECADASTRE" if cadastrado else "CADASTRAR AGORA",
                        icon="sensors",
                        bgcolor=COR_CARD_HIGH,
                        color=COR_PRIMARY,
                        on_click=lambda e, a=aluno: abrir_cadastro_digital(a, page, biometria_manager_global, render_main_content, state)
                    )
                ], alignment="spaceBetween"),
                padding=15, bgcolor=COR_CARD, border_radius=12,
                border=ft.border.all(1, COR_SUCCESS + "40" if cadastrado else COR_WARNING + "40")
            )

        biometria_col.controls.append(create_section_title("PENDENTES DE BIOMETRIA"))
        if not alunos_pendentes:
            biometria_col.controls.append(ft.Text("Todos os alunos sincronizados possuem biometria local.", color=COR_TEXT_SEC, size=13))
        else:
            for a in alunos_pendentes:
                biometria_col.controls.append(create_biometria_item(a, False))
        
        biometria_col.controls.append(ft.Divider(height=30, color="transparent"))
        biometria_col.controls.append(create_section_title("BIOMETRIAS CADASTRADAS LOCALMENTE"))
        for a in alunos_cadastrados:
            biometria_col.controls.append(create_biometria_item(a, True))
            
        return ft.Column([
            ft.Text("GESTOR DE BIOMETRIA", size=24, weight="bold", font_family="Space Grotesk"),
            ft.Text("Gerencie as digitais salvas localmente neste módulo.", color=COR_TEXT_SEC, size=13),
            ft.Divider(height=20, color=COR_CARD_HIGH),
            biometria_col
        ], expand=True)

    def render_main_content():
        # Atualiza menu ativo no sidebar com segurança
        for item in menu_monitoramento.controls:
            if isinstance(item, ft.Container) and hasattr(item, "content") and isinstance(item.content, ft.Row):
                try:
                    # O texto está dentro de Row -> Container
                    text_obj = item.content.controls[1]
                    icon_obj = item.content.controls[0]
                    is_active = (text_obj.value == "Clientes" and state["current_view"] == "clientes") or \
                               (text_obj.value == "Biometria" and state["current_view"] == "biometria")
                    
                    item.bgcolor = COR_CARD if is_active else None
                    icon_obj.color = COR_PRIMARY if is_active else COR_TEXT_SEC
                    text_obj.color = COR_TEXTO if is_active else COR_TEXT_SEC
                except (IndexError, AttributeError):
                    pass

        if state["current_view"] == "clientes":
            center_panel.content = center_content
            render_alunos()
        else:
            center_panel.content = render_biometria_view()
        
        try: page.update()
        except: pass

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
    
    # Inicializa o conteúdo principal
    render_main_content()

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
            indices = [0, 1, 2] if os.name == "nt" else ["/dev/video0", 0, 1]
            for i in indices:
                try:
                    c = cv2.VideoCapture(i)
                    if c.isOpened():
                        c.release(); return True
                except: pass
            return False

        def check_biometria():
            try:
                user = getpass.getuser()
                res = subprocess.run(["fprintd-list", user], capture_output=True, text=True, timeout=2)
                return "found" in res.stdout.lower() or "device" in res.stdout.lower()
            except: return False

        def test_relay():
            if trigger_catraca("Teste Diagnostico"):
                btn_test.text = "COMANDO ENVIADO"
            else:
                btn_test.text = "FALHA CONEXÃO"
            btn_test.disabled = True
            page.update()

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
                    diag_card("LEITOR DIGITAL", check_biometria(), "Scanner fprintd detectado no barramento USB", "fingerprint"),
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
    # BARRA DE TÍTULO CUSTOMIZADA (PREMIUM) - FUNÇÃO GERADORA
    # ==========================
    def create_title_bar(title_text="ROCKS FIT - SISTEMA DE RECEPÇÃO"):
        def close_app(e): page.window.close()
        def minimize_app(e): page.window.minimized = True
        def maximize_app(e): 
            page.window.maximized = not page.window.maximized
            page.update()

        return ft.Container(
            content=ft.Row(
                [
                    ft.WindowDragArea(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Image(src="assets/rkslogo.png", height=20) if os.path.exists("assets/rkslogo.png") else ft.Icon("fitness_center", color=COR_PRIMARY, size=20),
                                ft.Text(title_text, size=11, weight="bold", color=COR_TEXT_SEC, font_family="Space Grotesk"),
                            ], spacing=10),
                            padding=ft.padding.only(left=20),
                        ),
                        expand=True,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(ft.Icons.REMOVE, icon_size=16, icon_color=COR_TEXT_SEC, on_click=minimize_app),
                            ft.IconButton(ft.Icons.CROP_SQUARE, icon_size=16, icon_color=COR_TEXT_SEC, on_click=maximize_app),
                            ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color="#e74c3c", on_click=close_app),
                        ],
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#0a0a0a",
            height=32,
        )

    # ==========================
    # LAYOUT PRINCIPAL
    # ==========================

    main_container = ft.Container(
        content=ft.Row(
            [
                sidebar,
                center_panel,
            ],
            expand=True, spacing=0
        ),
        expand=True
    )

    # Layouts iniciais (instâncias únicas)
    layout = ft.Column([create_title_bar(), main_container], expand=True, spacing=0)


    # ==========================
    # ROTEAMENTO DE TELAS (DASHBOARD vs CÂMERA)
    # ==========================
    def route_change(e):
        # Limpa callbacks de UI da rota anterior para evitar "instabilidade" e erros de memória
        state["_ui_identificado_cb"] = None
        state["_ui_aguardando_cb"] = None
        
        route = e.route if hasattr(e, "route") else page.route
        print(f"🛣️ Mudança de rota: {route}")
        
        # Evita limpar se já estiver na rota (ajuda na estabilidade do Desktop)
        if len(page.views) > 0 and page.views[-1].route == route:
            return

        page.views.clear()
        
        if "/monitor" in route:
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

            state["_ui_identificado_cb"] = _set_identificado
            state["_ui_aguardando_cb"] = _set_aguardando
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
                                        trigger_catraca(f"Face: {melhor_aluno['nome']}")
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

            def loop_digital():
                global BIOMETRIA_BUSY
                if not biometria_manager_global: return
                print("☝️ [FPRINT] Loop de biometria digital iniciado")
                
                while camera_estado["rodando"]:
                    if BIOMETRIA_BUSY:
                        time.sleep(1)
                        continue
                    
                    path_digital = "BIOMETRIA_DATA/ALUNOS"
                    if not os.path.exists(path_digital):
                        os.makedirs(path_digital, exist_ok=True)
                    
                    # Lista arquivos no formato {matricula}_{dedo}.finger
                    files = [f for f in os.listdir(path_digital) if f.endswith(".finger")]
                    
                    if not files:
                        time.sleep(2)
                        continue
                    
                    # Filtra apenas alunos sincronizados para evitar checar registros órfãos
                    matriculas_validas = [str(a.get("matricula")) for a in state["alunos_data"]]
                    
                    biometrias = []
                    for f in files:
                        name = f.replace(".finger", "")
                        if "_" in name:
                            parts = name.split("_")
                            mat = parts[0]
                            if mat in matriculas_validas:
                                biometrias.append((mat, parts[1]))
                        else:
                            mat = name
                            if mat in matriculas_validas:
                                biometrias.append((mat, "right-index-finger"))

                    # Otimização: A verificação por fprintd-verify é lenta. 
                    # Idealmente fprintd deveria gerenciar isso, mas como estamos emulando 1:N
                    # vamos tentar agrupar por dedo ou reduzir a frequência.
                    for mat, finger in biometrias:
                        if not camera_estado["rodando"] or BIOMETRIA_BUSY: break
                        
                        # Chama a verificação bloqueante (com timeout interno na classe)
                        if biometria_manager_global.verify(mat, finger):
                            print(f"✅ [FPRINT] Correspondência: {mat} ({finger})")
                            aluno_data = next((a for a in state["alunos_data"] if str(a.get("matricula")) == mat), None)
                            if aluno_data:
                                try:
                                    # Valida no CRM antes de liberar
                                    r = requests.get(f"{SITE_URL}/api/catraca-check/{mat}/?token={SYNC_TOKEN}", timeout=3)
                                    data = r.json() if r.status_code == 200 else aluno_data
                                except: data = aluno_data
                                
                                liberado = data.get("status", "") in ["ativo", "liberado"]
                                _set_identificado(data, liberado)
                                if liberado:
                                    trigger_catraca(f"Digital: {data.get('nome', mat)}")
                                
                                time.sleep(4) # Cooldown após sucesso
                                _set_aguardando()
                                break
                    
                    time.sleep(0.1) # Breve pausa entre ciclos completos

            threading.Thread(target=loop_camera, daemon=True).start()
            # Combinamos a barra (nova instância) com o layout do monitor
            monitor_with_bar = ft.Column([create_title_bar("MONITOR DE ACESSO - ROCKS FIT"), monitor_layout], expand=True, spacing=0)
            page.views.append(ft.View("/monitor", [monitor_with_bar], bgcolor=surf, padding=0))
        else:
            page.title = "ROCKS FIT - RECEPÇÃO"
            # O layout principal também recebe uma barra nova a cada mudança de rota para garantir estabilidade
            layout_final = ft.Column([create_title_bar(), main_container], expand=True, spacing=0)
            page.views.append(ft.View("/", [layout_final], padding=0, bgcolor=COR_BG))
        
        page.update()

    # Vinculamos o estado da sessão atual para que o loop global saiba como atualizar a UI
    state["_ui_identificado_cb"] = None
    state["_ui_aguardando_cb"] = None
    GLOBAL_SESSION_STATES.append(state)

    def view_pop(view):
        if "/monitor" in page.route: return
        page.views.clear(); page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Força a primeira renderização manualmente para evitar tela preta
    route_change(ft.RouteChangeEvent(route=page.route or "/"))
    
    # Sincroniza em segundo plano
    threading.Thread(target=sync_crm, daemon=True).start()

GLOBAL_SESSION_STATES = []
GLOBAL_LOOP_STARTED = False

def global_loop_digital():
    if not biometria_manager_global: return
    print("☝️ [FPRINT] Loop Global de Biometria Iniciado")
    while True:
        if BIOMETRIA_BUSY:
            time.sleep(1); continue
        
        # Carrega digitais locais
        path_digital = "BIOMETRIA_DATA/ALUNOS"
        if not os.path.exists(path_digital): time.sleep(2); continue
        files = [f for f in os.listdir(path_digital) if f.endswith(".finger")]
        if not files: time.sleep(2); continue
        
        # Alunos válidos
        matriculas_validas = [str(a.get("matricula")) for a in GLOBAL_ALUNOS]
        
        for f in files:
            if BIOMETRIA_BUSY: break
            name = f.replace(".finger", "")
            mat = name.split("_")[0] if "_" in name else name
            finger = name.split("_")[1] if "_" in name else "right-index-finger"
            
            if mat in matriculas_validas:
                if biometria_manager_global.verify(mat, finger):
                    print(f"✅ [FPRINT GLOBAL] Identificado: {mat}")
                    aluno = next((a for a in GLOBAL_ALUNOS if str(a.get("matricula")) == mat), None)
                    if aluno:
                        try:
                            r = requests.get(f"{SITE_URL}/api/catraca-check/{mat}/?token={SYNC_TOKEN}", timeout=3)
                            data = r.json() if r.status_code == 200 else aluno
                        except: data = aluno
                        
                        liberado = data.get("status", "") in ["ativo", "liberado"]
                        
                        # Notifica todas as sessões ativas
                        for s_state in GLOBAL_SESSION_STATES:
                            if s_state.get("_ui_identificado_cb"):
                                s_state["_ui_identificado_cb"](data, liberado)
                        
                        if liberado:
                            trigger_catraca(f"Digital: {data.get('nome', mat)}")
                        
                        time.sleep(5)
                        for s_state in GLOBAL_SESSION_STATES:
                            if s_state.get("_ui_aguardando_cb"):
                                s_state["_ui_aguardando_cb"]()
                        break
        time.sleep(0.5)

if __name__ == "__main__":
    if not GLOBAL_LOOP_STARTED:
        threading.Thread(target=global_loop_digital, daemon=True).start()
        GLOBAL_LOOP_STARTED = True

    # Força o uso do backend X11 no Linux para evitar conflitos com Wayland
    if sys.platform.startswith("linux"):
        os.environ["GDK_BACKEND"] = "x11"
        
    print("🚀 Iniciando Módulo de Recepção Rocks-Fit...")
    ft.app(
        target=main, 
        view=ft.AppView.FLET_APP, 
        assets_dir="assets"
    )