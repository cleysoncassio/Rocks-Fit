import os
import sys

# Carrega dotenv bem no início para que as variáveis afetem as configurações do Flet
try:
    from dotenv import load_dotenv
    load_dotenv() # Carrega .env se existir
except:
    pass

import flet as ft
# --- POLYFILL PARA ICONES DESCONTINUADOS OU FALTANTES ---
for icon_name in ["FINGERPRINT", "LOCK_OPEN", "CLOSE", "REFRESH", "REMOVE", "CROP_SQUARE", "PEOPLE", "VIDEOCAM", "SYNC", "HISTORY", "TROUBLESHOOT", "SETTINGS", "CLOUD_DONE", "CHECK_CIRCLE", "SEARCH", "CALENDAR_MONTH", "PERSON", "LOCK", "ANALYTICS", "MEMORY", "ERROR", "REPLAY"]:
    if not hasattr(ft.icons, icon_name):
        setattr(ft.icons, icon_name, icon_name.lower())

import time
import subprocess
import threading
import requests
import json
import cv2
import base64
import numpy as np
from datetime import datetime
from biometria_fprint import BiometriaFPrint
import qrcode
import io

# --- FIX FLET 0.85 & WINDOWS RENDER OPTIMIZATION ---
os.environ["FLET_DISABLE_ACCESSIBILITY"] = os.getenv("FLET_DISABLE_ACCESSIBILITY", "1")
os.environ["FLET_FORCE_WEBVIEW_ACCESSIBILITY"] = os.getenv("FLET_FORCE_WEBVIEW_ACCESSIBILITY", "0")
# Configurações de renderização para Linux (Harden Industrial - Estabilidade Máxima)
os.environ["FLET_FORCE_SOFTWARE_RENDER"] = os.getenv("FLET_FORCE_SOFTWARE_RENDER", "0")
os.environ["FLET_WS_MAX_MESSAGE_SIZE"] = os.getenv("FLET_WS_MAX_MESSAGE_SIZE", "8000000")

PAGE_LOCK = threading.RLock()

# ==========================
# CONFIGURAÇÕES OFICIAIS ROCKS-FIT
# ==========================
SITE_URL = os.getenv("SITE_URL", "https://academiarocksfit.com.br")
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "Rocksfit@2024")
FACES_DIR = "BIOMETRIA_DATA/FACES"
HEADERS = {"Authorization": f"Token {SYNC_TOKEN}"}
CONFIG_PATH = "BIOMETRIA_DATA/config.json"
# --- CONFIGURAÇÕES DINÂMICAS ---
CONFIG_PATH = "BIOMETRIA_DATA/config.json"
THRESHOLD_FACIAL = 0.52
FACE_FRAME_SKIP = 5

def load_local_config():
    global THRESHOLD_FACIAL, FACE_FRAME_SKIP
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                THRESHOLD_FACIAL = cfg.get("face_threshold", 0.52)
                # O monitor é otimizado para ser mais fluído que a ponte
                FACE_FRAME_SKIP = max(2, cfg.get("face_frame_skip", 10) // 2)
    except: pass

load_local_config()

# Cores Rocks-Fit
primary = "#ff7a2f"      # Laranja Oficial
success = "#2ecc71"      # Verde Liberação
error = "#e74c3c"        # Vermelho Bloqueio
exit_color = "#3498db"   # Azul Saída
surf = "#0a0a0a"         # Preto Profundo
surf_high = "#161616"    # Cinza Escuro
surf_highest = "#222222" # Cinza Médio

state = {
    "rodando": True,
    "identificando": False,
    "carregando": True,
    "alunos_data": [],
    "perfis_neurais": {},
    "conhecidos_encodings": [],
    "conhecidos_matriculas": []
}

GLOBAL_FRAME_BASE64 = ""
VISION_LOCK = threading.Lock()
GLOBAL_LOOP_STARTED = False

ACTIVE_SESSIONS = []
ACTIVE_SESSIONS_LOCK = threading.Lock()

os.makedirs(FACES_DIR, exist_ok=True)

# Detectores de Face
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

try:
    # Status da API DeepFace (substitui face_recognition local) - Timeout aumentado para 2s
    resp = requests.get("http://localhost:8000/api/biometria/verificar/", timeout=2.0)
    DEEPFACE_ONLINE = (resp.status_code == 200)
    if DEEPFACE_ONLINE:
        print("✅ [MONITOR] DeepFace API detectada e ativa.")
    else:
        print("⚠️ [MONITOR] DeepFace API retornou status inesperado.")
except:
    DEEPFACE_ONLINE = False
    print("⚠️ [MONITOR] DeepFace API indisponível. Usando apenas detecção básica.")

def get_whatsapp_qr_base64():
    try:
        import urllib.parse
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        msg = "Estou com problemas no meu acesso, pode verificar por favor?"
        url = f"https://wa.me/5584999470586?text={urllib.parse.quote(msg)}"
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except: return ""

QR_WPP_BASE64 = get_whatsapp_qr_base64()

def detectar_sentido_acesso(matricula):
    """
    Verifica se o aluno está entrando ou saindo baseado no log do dia (Toggle Inteligente)
    Implementa carência de 30 segundos entre reconhecimentos.
    Retorna: (sentido, allowed)
    """
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join("BIOMETRIA_DATA/LOGS", f"ACESSOS_{hoje}.csv")
        if not os.path.exists(log_path): 
            return "ENTRADA", True
        
        count = 0
        mat_str = str(matricula).strip().upper()
        ultimo_acesso = None
        
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[1:][-50:]: # Analisa os últimos 50 registros para ser rápido
                parts = line.strip().split(";")
                if len(parts) >= 3:
                    if parts[2].strip().upper() == mat_str:
                        count += 1
                        try:
                            dt_str = f"{parts[0]} {parts[1]}"
                            ultimo_acesso = datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
                        except: pass
        
        # Carência de 30 segundos
        if ultimo_acesso:
            delta = (datetime.now() - ultimo_acesso).total_seconds()
            if delta < 30:
                return "ENTRADA" if count % 2 == 0 else "SAÍDA", False

        sentido = "SAÍDA" if count % 2 != 0 else "ENTRADA"
        return sentido, True
    except:
        return "ENTRADA", True

def log_acesso_local(aluno, metodo, status, sentido):
    log_file = "BIOMETRIA_DATA/acessos_hoje.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp},{aluno.get('matricula')},{aluno.get('nome')},{metodo},{status},{sentido}\n"
    with open(log_file, "a") as f: f.write(line)

def registrar_acesso_crm(matricula, metodo):
    # Tenta via API (Online)
    try:
        resp = requests.get(
            f"{SITE_URL}/api/catraca-check/{matricula}/?token={SYNC_TOKEN}&log=1&metodo={metodo}",
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"📡 [MODO OFFLINE] Falha na conexão: {e}")

    # Fallback via Cache Local (Offline)
    print(f"📂 [MODO OFFLINE] Buscando matrícula {matricula} no cache local...")
    try:
        if state["alunos_data"]:
            aluno = next((a for a in state["alunos_data"] if str(a.get("matricula")) == str(matricula)), None)
            if aluno:
                # Retorna um objeto compatível com o CRM com dados completos
                return {
                    "nome": aluno.get("nome"),
                    "matricula": matricula,
                    "status": aluno.get("status", "ATIVO"),
                    "vencimento": aluno.get("vencimento", "OFFLINE"),
                    "foto_url": aluno.get("foto", aluno.get("foto_url"))
                }
    except: pass
    return None

def trigger_catraca(msg="Liberado", sentido="ENTRADA"):
    """Dispara o relé da catraca via socket industrial com alta resiliência"""
    # Carrega IP/Porta da configuração compartilhada (Industrial)
    config_path = "BIOMETRIA_DATA/config.json"
    ip = "169.254.37.150" # Fallback
    porta = 3000          # Fallback
    sentido_entrada = 0
    sentido_saida = 1
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
                ip = cfg.get("catraca_ip", ip)
                porta = int(cfg.get("catraca_porta", porta))
                sentido_entrada = cfg.get("catraca_sentido_entrada", 0)
                sentido_saida = cfg.get("catraca_sentido_saida", 1)
        except: pass

    cmd_code = sentido_entrada if sentido == "ENTRADA" else sentido_saida
    payload = b"lgu" + bytes([cmd_code]) + msg.encode('cp1252')
    
    import socket
    for attempt in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((ip, porta))
                s.sendall(b"mcg") # Wake-up
                time.sleep(0.1)
                s.sendall(payload)
                print(f"🔓 [HARDWARE] Comando {sentido} enviado via Monitor ({ip}:{porta})")
                return True
        except Exception as e:
            print(f"⚠️ [HARDWARE] Retentativa {attempt+1}/3: {e}")
            time.sleep(0.5)
    
    print(f"❌ [HARDWARE] Erro ao disparar catraca via Monitor: {ip}:{porta}")
    return False

def main(page: ft.Page):
    page.title = "ROCKS FIT - MONITOR DE ACESSO"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = surf
    
    page._engine_alive = True
    
    session_state = {
        "page": page,
        "active": True,
        "process_id_cb": None,
        "identificando": False
    }
    
    def on_close(e):
        session_state["active"] = False
        page._engine_alive = False
        with ACTIVE_SESSIONS_LOCK:
            if session_state in ACTIVE_SESSIONS:
                ACTIVE_SESSIONS.remove(session_state)
            
            # Só encerra os loops globais de hardware se for a ÚLTIMA sessão ativa no servidor
            if len(ACTIVE_SESSIONS) == 0:
                state["rodando"] = False
                print("🛑 [MONITOR] Nenhuma sessão ativa no servidor. Encerrando loops de hardware...")
            else:
                print(f"🛑 [MONITOR] Sessão de monitor fechada. Restam {len(ACTIVE_SESSIONS)} sessões ativas.")
        # Pausa maior para threads pararem antes de destruir a engine (Harden Linux)
        time.sleep(0.5)
    page.on_close = on_close
    

    def monitor_safe_update():
        if not page or not getattr(page, "_engine_alive", True): return
        
        with PAGE_LOCK:
            try:
                page.update()
            except BaseException as e:
                err = str(e).lower()
                print(f"⚠️ [MONITOR UPDATE ERR] {err}")
                # Se a engine sumiu ou o loop fechou, marcamos como morta
                if "engine" in err or "messenger" in err or "view" in err or "thread" in err or "loop" in err or "session" in err:
                    page._engine_alive = False
                    session_state["active"] = False
                    with ACTIVE_SESSIONS_LOCK:
                        if session_state in ACTIVE_SESSIONS:
                            ACTIVE_SESSIONS.remove(session_state)
                        if len(ACTIVE_SESSIONS) == 0:
                            state["rodando"] = False
                            print("🛑 [MONITOR] Todas as sessões falharam ou fecharam. Parando loops globais.")
    
    # UI Components
    dot_server = ft.Container(width=8, height=8, border_radius=4, bgcolor=success)
    dot_digital = ft.Container(width=8, height=8, border_radius=4, bgcolor=error)
    lbl_digital_status = ft.Text("SCANNER: ACTIVE", size=10, weight="bold", color="#adaaaa")
    
    # Pixel transparente para inicialização segura de componentes Image (agora em JPEG para compatibilidade com a câmera)
    transparent_pixel = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD+f+iiigD/2Q=="
    img_cam = ft.Image(src_base64=transparent_pixel, width=640, height=480, fit="fill", border_radius=12)
    lbl_cam_status = ft.Text("APROXIME-SE", size=20, weight="bold", color="#000000")
    badge_cam_status = ft.Container(content=lbl_cam_status, bgcolor=primary, border_radius=10, padding=ft.Padding(40, 15, 40, 15), margin=ft.Padding(0, 0, 0, 20))
    
    loading_overlay = ft.Container(
        content=ft.Column([
            ft.ProgressRing(color=primary),
            ft.Text("Sincronizando com o CRM...", size=16, color="#ffffff", weight="bold")
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
        bgcolor="#00000000", alignment=ft.Alignment(0, 0), visible=False
    )
    
    # Container da Câmera Responsivo - Posicionamento Atômico para evitar erro TransformLayer
    cam_stack = ft.Stack([
        ft.Container(content=img_cam, alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0),
        ft.Container(content=badge_cam_status, alignment=ft.Alignment(0, 1), bottom=20, left=0, right=0),
        loading_overlay
    ], expand=True)
    
    cam_container = ft.Container(
        content=cam_stack,
        bgcolor="#000000",
        border_radius=16,
        border=ft.Border(ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10")),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        expand=True
    )
    
    lbl_nome = ft.Text("AGUARDANDO", size=22, weight="bold", color="#ffffff", text_align="center")
    lbl_matricula = ft.Text("Posicione-se em frente à câmera", size=13, color="#adaaaa", text_align="center")
    lbl_msg = ft.Text("", size=22, weight="bold", color="#adaaaa", text_align="center")
    lbl_vencimento = ft.Text("", size=13, weight="bold", color="#ffffff")
    lbl_metodo_acesso = ft.Text("VIA FACE", size=10, weight="bold", color=primary, visible=False)
    
    qr_whatsapp_img = ft.Image(src_base64=transparent_pixel, width=120, height=120)
    img_perfil = ft.Image(src_base64=transparent_pixel, width=180, height=180, border_radius=90, fit="cover", visible=False)
    img_qr = ft.Image(src_base64=QR_WPP_BASE64, width=180, height=180, border_radius=12, visible=False)
    icon_placeholder = ft.Container(content=ft.Icon("person", color="#adaaaa", size=80), width=180, height=180, border_radius=90, bgcolor=surf_highest, border=ft.Border(ft.BorderSide(3, "#333333"), ft.BorderSide(3, "#333333"), ft.BorderSide(3, "#333333"), ft.BorderSide(3, "#333333")), alignment=ft.Alignment(0, 0))
    
    lbl_status_tag = ft.Text("INATIVO", size=14, weight="bold", color="#ff7351")
    status_container = ft.Container(content=ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor="#ff7351"), lbl_status_tag], spacing=8, alignment=ft.MainAxisAlignment.CENTER), bgcolor="#ff735133", padding=ft.Padding(20, 10, 20, 10), border_radius=20)
    
    card_perfil = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Stack([icon_placeholder, img_perfil, img_qr]), alignment=ft.Alignment(0, 0), margin=ft.Padding(0, 0, 0, 20)),
            lbl_nome,
            ft.Container(content=lbl_matricula, alignment=ft.Alignment(0, 0), margin=ft.Padding(0, 0, 0, 5)),
            ft.Container(content=lbl_metodo_acesso, alignment=ft.Alignment(0, 0), margin=ft.Padding(0, 0, 0, 16)),
            status_container,
            ft.Divider(color=surf_highest, height=28),
            ft.Row([ft.Text("UNIDADE", size=12, color="#adaaaa"), ft.Text("ROCKS FIT #01", size=13, weight="bold")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("VENCIMENTO", size=12, color="#adaaaa"), lbl_vencimento], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(content=lbl_msg, alignment=ft.Alignment(0, 0), margin=ft.Padding(0, 15, 0, 10))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
        bgcolor="#161616cc", 
        padding=30, 
        border_radius=20, 
        expand=True,
        # blur=ft.Blur(15, 15), # Desativado temporariamente para estabilidade Linux
        border=ft.Border(ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10"), ft.BorderSide(1, "#ffffff10")),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#00000080"),
        animate=ft.Animation(400, "decelerate")
    )
    
    card_capacidade = ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("CAPACIDADE", size=18, weight="bold", italic=True, color="#000000"), ft.Icon("people", color="#000000")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("74%", size=48, weight="bold", color="#000000"), ft.Text("LOTADO", size=12, weight="bold", color="#000000")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.ProgressBar(value=0.74, color="#000000", bgcolor="#ffffff40", height=8)
        ]),
        gradient=ft.LinearGradient(colors=["#ff9159", "#ff7a2f"]), padding=30, border_radius=20, margin=ft.Padding(0, 16, 0, 0)
    )

    page.add(
        ft.Container(
            content=ft.Column([
                # Top Bar
                ft.Row([
                    ft.Image(src="media/imagens/rkslogo.png", height=70),
                    ft.Row([
                        ft.Icon("wifi", color=primary),
                        ft.Icon("info", color=primary)
                    ], spacing=15)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                # Main Content (Responsive)
                ft.ResponsiveRow([
                    # Camera Column
                    ft.Column([
                        ft.Text("BIOMETRIA ATIVA", size=32, italic=True, weight="bold", color=primary),
                        ft.Text("APROXIME-SE PARA VALIDAR", color="#adaaaa"),
                        cam_container
                    ], col={"sm": 12, "md": 7, "lg": 8}),
                    
                    # Sidebar
                    ft.Column([
                        card_perfil,
                        card_capacidade
                    ], col={"sm": 12, "md": 5, "lg": 4})
                ], expand=True, spacing=20, run_spacing=20),
                
                # Bottom Bar
                ft.Row([
                    ft.Row([
                        dot_server, 
                        ft.Text("SERVER: ONLINE", size=10, color="#adaaaa"),
                        ft.Container(width=20),
                        dot_digital,
                        lbl_digital_status
                    ]),
                    ft.Text("SÃO PAULO, BR", size=10, color="#adaaaa")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], expand=True),
            padding=30, expand=True, bgcolor=surf
        )
    )

    def _set_aguardando():
        if not getattr(page, "_engine_alive", True): return
        try:
            with PAGE_LOCK:
                session_state["identificando"] = False
                state["identificando"] = False
                lbl_nome.value = "AGUARDANDO"; lbl_nome.color = "#ffffff"
                lbl_matricula.value = "Posicione-se em frente à câmera"
                lbl_metodo_acesso.visible = False; lbl_msg.value = ""
                lbl_status_tag.value = "INATIVO"; lbl_status_tag.color = "#ff7351"
                status_container.bgcolor = "#ff735133"
                img_perfil.src_base64 = transparent_pixel
                img_perfil.visible = False
                img_qr.visible = False; icon_placeholder.visible = True
                lbl_cam_status.value = "APROXIME-SE"; badge_cam_status.bgcolor = primary
                lbl_vencimento.value = ""
                monitor_safe_update()
        except (RuntimeError, Exception):
            page._engine_alive = False

    def _process_identification(matricula, metodo="FACIAL", sentido_forcado=None, aluno_data=None):
        if not getattr(page, "_engine_alive", True): return
        if session_state["identificando"]: return
        session_state["identificando"] = True
        state["identificando"] = True
        print(f"🔍 [IDENTIFICANDO] Matricula: {matricula} via {metodo}")
        
        try:
            with PAGE_LOCK:
                # Feedback visual imediato
                lbl_nome.value = "IDENTIFICANDO..."; lbl_nome.color = primary
                monitor_safe_update()
            
            # Busca dados no CRM (ou usa aluno_data ou cache local se offline)
            data = aluno_data
            if not data:
                data = registrar_acesso_crm(matricula, metodo)
                
            if not data:
                print(f"⚠️ [CRM] Sem resposta para matricula {matricula}")
                return

            status_raw = str(data.get("status", "")).lower()
            liberado = status_raw in ["ativo", "liberado", "pago", "adimplente", "ok"]
            
            # Usa o sentido enviado pela ponte se disponível, senão calcula localmente
            if sentido_forcado:
                sentido = sentido_forcado
                allowed = True
            else:
                sentido, allowed = detectar_sentido_acesso(matricula)
            
            if not allowed:
                print(f"⏳ [MONITOR] Carência de 30s activa para {matricula}")
                return

            with PAGE_LOCK:
                lbl_nome.value = data.get("nome", "ALUNO").upper()
                lbl_matricula.value = f"MATRÍCULA: {matricula}"
                lbl_metodo_acesso.value = f"VIA {metodo}"; lbl_metodo_acesso.visible = True
            
                # Foto do perfil
                furl = data.get("foto", data.get("foto_url", ""))
                has_local_photo = False
                if furl:
                    nome_arquivo = furl.split('/')[-1]
                    # Caminhos físicos no disco para checagem de existência da foto
                    possiveis_caminhos = [
                        os.path.join("/home/ccs/Modelos/Rocks-Fit/media/alunos/fotos", nome_arquivo),
                        os.path.join("../media/alunos/fotos", nome_arquivo),
                        os.path.join("media/alunos/fotos", nome_arquivo),
                        furl.lstrip('/')
                    ]
                    caminho_existente = None
                    for cp in possiveis_caminhos:
                        if os.path.exists(cp):
                            caminho_existente = cp
                            break
                    
                    if caminho_existente:
                        try:
                            # Otimização de velocidade: converte a foto do disco em Base64
                            # para o Flet renderizar de forma instantânea na memória
                            with open(caminho_existente, "rb") as image_file:
                                img_perfil.src_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                            img_perfil.src = None
                        except Exception as ex:
                            print(f"⚠️ [MONITOR] Erro base64: {ex}")
                            img_perfil.src = f"/media/alunos/fotos/{nome_arquivo}"
                            img_perfil.src_base64 = None
                        has_local_photo = True
                    elif furl.startswith("http"):
                        img_perfil.src = furl
                        img_perfil.src_base64 = None
                        has_local_photo = True
                    elif not data.get("vencimento") == "OFFLINE":
                        if furl.startswith("/"): furl = f"{SITE_URL}{furl}"
                        img_perfil.src = furl
                        img_perfil.src_base64 = None
                        has_local_photo = True
                    
                if has_local_photo:
                    img_perfil.visible = True; icon_placeholder.visible = False
                else:
                    img_perfil.src_base64 = transparent_pixel
                    img_perfil.visible = False; icon_placeholder.visible = True

                if liberado:
                    lbl_status_tag.value = f"✔ {sentido}"; status_container.bgcolor = success
                    lbl_vencimento.value = f"VENCIMENTO: {data.get('vencimento', 'N/D')}"
                    lbl_vencimento.color = "#ffffff"
                    if sentido == "ENTRADA":
                        lbl_cam_status.value = "Olá, bom treino"; lbl_msg.value = "BOM TREINO!"
                    else:
                        lbl_cam_status.value = "Até amanhã"; lbl_msg.value = "ATÉ AMANHÃ!"
                    
                    badge_cam_status.bgcolor = success; lbl_msg.color = success
                else:
                    lbl_status_tag.value = "✖ BLOQUEADO"; status_container.bgcolor = error
                    lbl_vencimento.value = f"VENCIMENTO: {data.get('vencimento', 'PENDENTE')}"
                    lbl_vencimento.color = error
                    lbl_cam_status.value = "ACESSO NEGADO"; badge_cam_status.bgcolor = error
                    lbl_msg.value = "FALE CONOSCO"; lbl_msg.color = error
                    img_perfil.visible = False; icon_placeholder.visible = False; img_qr.visible = True
                    lbl_matricula.value = "Escaneie o QR Code para suporte"
                    
                venc = data.get("vencimento", "")
                if venc: lbl_vencimento.value = venc
                    
                monitor_safe_update()
            
            # Notifica a Ponte Bridge para atualizar o Monitor de Acesso (Handshake Industrial)
            # Executado FORA do PAGE_LOCK para não congelar o vídeo!
            try:
                with open("BIOMETRIA_DATA/bridge_event.json", "w") as f:
                    json.dump({
                        "matricula": matricula, 
                        "metodo": metodo, 
                        "sentido": sentido,
                        "timestamp": time.time()
                    }, f)
            except: pass
            
            # Disparo de rede assíncrono (não-bloqueante) em segundo plano
            # para não travar a UI, a renderização do vídeo e a liberação de novos acessos
            if liberado:
                threading.Thread(target=trigger_catraca, kwargs={"sentido": sentido}, daemon=True).start()
            
            # Delay de visualização de 5 segundos do perfil antes de resetar para standby
            time.sleep(5)
        except Exception as e:
            print(f"❌ [IDENTIFY ERROR] {e}")
        finally:
            try:
                _set_aguardando()
            except: pass

    session_state["process_id_cb"] = _process_identification

    def load_data_background():
        try:
            if os.path.exists("ALUNOS_SYNC.json"):
                print("📂 [MONITOR] Carregando ALUNOS_SYNC.json...")
                with open("ALUNOS_SYNC.json", "r") as f: state["alunos_data"] = json.load(f)
            
            if DEEPFACE_ONLINE:
                for i, aluno in enumerate(state["alunos_data"]):
                    if not state["rodando"]: return
                    mat = aluno["matricula"]; cache_path = os.path.join(FACES_DIR, f"{mat}.npy"); encoding = None
                    if os.path.exists(cache_path):
                        try: encoding = np.load(cache_path)
                        except: pass
                    
                    if encoding is None:
                        # O Monitor do aluno NÃO deve calcular encodings (trabalho pesado)
                        # Ele deve apenas usar os perfis já gerados pela ponte.
                        continue
                    
                    if encoding is not None:
                        if not any(np.array_equal(encoding, e) for e in state["conhecidos_encodings"]):
                            state["conhecidos_encodings"].append(encoding)
                            state["conhecidos_matriculas"].append(mat)
                    
                    if i == 1 or (i > 0 and i % 5 == 0):
                        loading_overlay.visible = False; state["carregando"] = False; monitor_safe_update()
            
            # Pequeno delay para garantir que a UI do Flet esteja pronta para receber o comando de ocultar
            time.sleep(1.0)
            loading_overlay.visible = False; state["carregando"] = False; monitor_safe_update()
            print(f"✅ [MONITOR] {len(state['conhecidos_encodings'])} perfis neurais carregados.")
        except Exception as e:
            print(f"⚠️ [MONITOR LOAD] {e}")
            loading_overlay.visible = False; state["carregando"] = False; monitor_safe_update()

    def loop_camera():
        state["camera_disponivel"] = True
        cap = None
        shared_frame_path = "BIOMETRIA_DATA/shared_frame.jpg"
        is_shared = True # Prioridade Industrial: Shared Frame

        # 1. Verifica se o Shared Frame Service está ativo (Ponte rodando)
        # Aguarda até 5 segundos pelo primeiro frame da ponte para evitar abrir a câmera física por engano
        for _ in range(10):
            if os.path.exists(shared_frame_path):
                print("🔗 [MONITOR] Shared Frame Service detectado. Usando feed da ponte.")
                is_shared = True
                break
            time.sleep(0.5)

        if not is_shared:
            # Fallback para câmera física se a ponte não estiver exportando frames
            # AVISO: Isso pode causar conflito se a ponte estiver usando a câmera
            print("⚠️ [MONITOR] Shared Frame não encontrado após espera. Tentando câmera física...")
            dispositivos_reais = [0, 2, 4, 1]
            if sys.platform.startswith("linux"):
                try:
                    import glob
                    video_devs = glob.glob("/dev/video*")
                    for dev in sorted(video_devs):
                        try:
                            idx = int(dev.replace("/dev/video", ""))
                            if idx % 2 == 0: dispositivos_reais.append(idx)
                        except: pass
                except: pass
            
            for idx in dispositivos_reais:
                try:
                    # Tenta abrir com backend V4L2 explicitamente no Linux para ser mais rápido
                    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
                    temp_cap = cv2.VideoCapture(idx, backend)
                    if temp_cap.isOpened():
                        # Configurações leves para evitar sobrecarga no fallback
                        temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                        temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                        cap = temp_cap
                        is_shared = False
                        print(f"✅ [MONITOR] Câmera física encontrada no índice {idx}")
                        break
                    if temp_cap: temp_cap.release()
                except: pass

        if is_shared:
            print("🔗 [SISTEMA] Modo de Vídeo: SERVICE (Shared Frame via Ponte)")
        else:
            print("📷 [SISTEMA] Modo de Vídeo: DIRECT (Acesso direto ao hardware)")

        if not cap and not is_shared:
            print("❌ [MONITOR] Falha crítica: Nenhuma fonte de vídeo disponível.")
            return

        if is_shared and not os.path.exists(shared_frame_path):
            try:
                os.makedirs("BIOMETRIA_DATA", exist_ok=True)
                black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.imwrite(shared_frame_path, black_frame)
            except: pass

        fc = 0
        last_faces = [] 
        first_frame_seen = False
        while state["rodando"]:
            if is_shared:
                # 1. Lê do arquivo compartilhado pela ponte (Shared Frame Service)
                if os.path.exists(shared_frame_path):
                    try:
                        with open(shared_frame_path, "rb") as f:
                            raw = f.read()
                        if not raw: continue
                        nparr = np.frombuffer(raw, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is None: continue
                        ret = True
                        if not first_frame_seen:
                            print(f"📸 [MONITOR] Primeiro frame recebido (Tamanho: {len(raw)} bytes)")
                            first_frame_seen = True
                    except Exception as e: 
                        print(f"⚠️ [MONITOR] Erro ao ler shared_frame: {e}")
                        time.sleep(0.05)
                        continue
                else:
                    # Se o arquivo sumiu, aguarda
                    time.sleep(0.1)
                    continue
                
                # 2. Lê Metadados de Visão da Ponte (Shared Vision HUD)
                try:
                    meta_path = "BIOMETRIA_DATA/faces_detected.json"
                    if os.path.exists(meta_path):
                        with open(meta_path, "r") as f:
                            meta = json.load(f)
                        last_faces = meta.get("faces", [])
                except: pass

            else:
                if cap is None or not cap.isOpened():
                    time.sleep(1)
                    continue
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue
            
            fc += 1

            # ── Desenho do HUD Sincronizado (Industrial) ──────────────────────────
            if last_faces:
                for (top, right, bottom, left) in last_faces:
                    # Desenho estético para o aluno (Escala corrigida)
                    x1, y1 = left*2, top*2
                    x2, y2 = right*2, bottom*2
                    w, h = x2 - x1, y2 - y1
                    
                    cor = (0, 255, 120) # Verde Rocks-Fit
                    label = "VALIDANDO..." if state["identificando"] else "IDENTIFICANDO"
                    
                    # Moldura de cantos
                    corner = min(30, w // 4, h // 4)
                    cv2.line(frame, (x1, y1), (x1+corner, y1), cor, 2)
                    cv2.line(frame, (x1, y1), (x1, y1+corner), cor, 2)
                    cv2.line(frame, (x2, y1), (x2-corner, y1), cor, 2)
                    cv2.line(frame, (x2, y1), (x2, y1+corner), cor, 2)
                    cv2.line(frame, (x1, y2), (x1+corner, y2), cor, 2)
                    cv2.line(frame, (x1, y2), (x1, y2-corner), cor, 2)
                    cv2.line(frame, (x2, y2), (x2-corner, y2), cor, 2)
                    cv2.line(frame, (x2, y2), (x2, y2-corner), cor, 2)
                    
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1, cv2.LINE_AA)

            try:
                # Qualidade reduzida para fluidez máxima na interface
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 35])
                if success and buffer is not None:
                    img_data = base64.b64encode(buffer).decode('utf-8')
                    with VISION_LOCK:
                        global GLOBAL_FRAME_BASE64
                        GLOBAL_FRAME_BASE64 = img_data
            except Exception as e:
                pass
            
            # FPS controlado para estabilidade industrial no Flet/Linux
            # Evita o erro TransformLayer e garante fluidez visual
            time.sleep(0.06) # ~16 FPS
        
        if cap: cap.release()

    def loop_eventos_externos():
        """Monitora arquivos de evento da ponte principal (ex: digital e status do scanner)"""
        last_event_time = 0
        while state["rodando"]:
            try:
                # 1. Checa eventos de identificação
                event_path = "BIOMETRIA_DATA/monitor_event.json"
                if os.path.exists(event_path):
                    with open(event_path, "r") as f:
                        ev = json.load(f)
                    ev_time = ev.get("timestamp", 0)
                    # Processa se for mais recente que o último evento processado E tiver ocorrido nos últimos 15 segundos
                    if ev_time > last_event_time and (time.time() - ev_time) < 15.0 and not state["identificando"]:
                        last_event_time = ev_time
                        mat = ev.get("matricula")
                        metodo = ev.get("metodo", "SISTEMA")
                        aluno_data = ev.get("aluno_data")
                        if mat:
                            sentido_ev = ev.get("sentido")
                            print(f"📡 [EVENTO EXTERNO] Identificando matrícula {mat} via {metodo} (Sentido: {sentido_ev})")
                            with ACTIVE_SESSIONS_LOCK:
                                for sess in list(ACTIVE_SESSIONS):
                                    if sess.get("active") and sess.get("process_id_cb"):
                                        try:
                                            threading.Thread(
                                                target=sess["process_id_cb"],
                                                args=(mat, metodo, sentido_ev, aluno_data),
                                                daemon=True
                                            ).start()
                                        except Exception as ex:
                                            print(f"⚠️ [MONITOR] Falha ao disparar identificação na sessão ativa: {ex}")
                
                # 2. Checa status do scanner (Handover Industrial)
                status_path = "BIOMETRIA_DATA/scanner_status.json"
                if os.path.exists(status_path):
                    with open(status_path, "r") as f:
                        stat = json.load(f)
                    current_status = stat.get("status", "ACTIVE")
                    if current_status == "ACTIVE":
                        dot_digital.bgcolor = success
                        lbl_digital_status.value = "SCANNER: PRONTO (ACESSO)"
                        lbl_digital_status.color = success
                    else:
                        dot_digital.bgcolor = primary
                        lbl_digital_status.value = "SCANNER: OCUPADO (CADASTRO)"
                        lbl_digital_status.color = primary
                    monitor_safe_update()
            except: pass
            time.sleep(0.5)

    def session_feed_loop():
        print("📺 [UI] Monitorando feed de câmera do aluno...")
        last_frame = ""
        fc_session = 0
        while getattr(page, "_engine_alive", True) and state["rodando"]:
            try:
                if not getattr(page, "_engine_alive", True): break
                
                with VISION_LOCK:
                    current_frame = GLOBAL_FRAME_BASE64
                
                if current_frame and current_frame != last_frame:
                    if len(current_frame) > 128:
                        with PAGE_LOCK:
                            if not getattr(page, "_engine_alive", True): break
                            img_cam.src_base64 = current_frame
                            last_frame = current_frame
                            
                            # Força a remoção do overlay de carregamento assim que o primeiro frame real chegar
                            if loading_overlay.visible:
                                loading_overlay.visible = False
                                state["carregando"] = False
                                try:
                                    cam_stack.controls.remove(loading_overlay)
                                except: pass
                            
                            try:
                                img_cam.update()
                            except: pass
                            
                            fc_session += 1
                            if fc_session < 10 or fc_session % 2 == 0:
                                monitor_safe_update()
            except BaseException as e:
                pass
            time.sleep(0.06) # ~16 FPS para sincronizar perfeitamente com a captura

    def start_loops():
        global GLOBAL_LOOP_STARTED
        
        # Registra a sessão ativa antes de iniciar os loops (Multi-Tab robusto)
        with ACTIVE_SESSIONS_LOCK:
            if session_state not in ACTIVE_SESSIONS:
                ACTIVE_SESSIONS.append(session_state)
                print(f"📡 [MONITOR] Nova sessão conectada. Total de sessões ativas: {len(ACTIVE_SESSIONS)}")
        
        # Sempre inicia o feed loop específico desta sessão
        threading.Thread(target=session_feed_loop, daemon=True).start()
        
        if GLOBAL_LOOP_STARTED:
            print("📡 [MONITOR] Loops de hardware globais já estão ativos. Evitando duplicidade.")
            return
        GLOBAL_LOOP_STARTED = True
        
        # Delay inicial para garantir que o Flet já abriu a janela antes de disparar threads
        time.sleep(2.0)
        threading.Thread(target=load_data_background, daemon=True).start()
        threading.Thread(target=loop_camera, daemon=True).start()
        threading.Thread(target=loop_eventos_externos, daemon=True).start()

    threading.Thread(target=start_loops, daemon=True).start()

if __name__ == "__main__":
    try:
        # Configuração flexível de visualização (Harden Linux)
        # Permite forçar o modo web via .env (FLET_VIEW_MODE=WEB_BROWSER) ou argumento '--web'
        forced_web = os.getenv("FLET_VIEW_MODE") == "WEB_BROWSER" or "--web" in sys.argv
        
        if forced_web:
            print("🌐 [FLET] Inicializando em modo WEB_BROWSER (Navegador) para evitar tela preta...")
            view_mode = getattr(getattr(ft, "AppView", None), "WEB_BROWSER", getattr(ft, "WEB_BROWSER", "web_browser"))
        else:
            # Compatibilidade entre versões do Flet (Moderno vs Legado)
            view_mode = getattr(ft, "FLET_APP", getattr(ft, "AppView", None))
            if hasattr(view_mode, "FLET_APP"): 
                view_mode = view_mode.FLET_APP
            elif hasattr(ft, "AppView") and hasattr(ft.AppView, "FLET_APP"):
                view_mode = ft.AppView.FLET_APP
            else:
                view_mode = "flet_app" # Fallback string literal
            print(f"🖥️ [FLET] Inicializando em modo Desktop nativo (View: {view_mode})...")
            
        # Limpa qualquer processo órfão escutando na porta 8554 (Linux)
        if sys.platform.startswith("linux"):
            try:
                res = subprocess.run("lsof -t -i :8554", shell=True, capture_output=True, text=True)
                pids = res.stdout.strip().split()
                my_pid = str(os.getpid())
                for pid in pids:
                    if pid != my_pid:
                        print(f"🧹 [SISTEMA] Liberando porta 8554. Finalizando processo órfão {pid}...")
                        subprocess.run(["kill", "-9", pid], capture_output=True)
                        time.sleep(0.5)
            except Exception as ex:
                print(f"⚠️ [SISTEMA] Falha ao limpar porta 8554: {ex}")
            
        print("🚀 [SISTEMA] Iniciando Monitor de Acesso Rocks-Fit...")
        
        # Calcula caminho absoluto da raiz do projeto para servir fotos locais como assets do Flet
        assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Usa porta diferente da ponte (8552) para evitar conflitos de barramento
        if hasattr(ft, "run"):
            ft.run(main, view=view_mode, port=8554, assets_dir=assets_path)
        else:
            ft.app(target=main, view=view_mode, port=8554, assets_dir=assets_path)
    except Exception as e:
        print(f"⚠️ [FLET] Falha ao iniciar Monitor: {e}")