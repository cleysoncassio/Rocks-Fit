# -*- coding: utf-8 -*-
import os
import sys
import time

# Garante que o diretório de trabalho é o do próprio script (MODULO_RECEPCAO)
# Isso resolve erros de arquivo não encontrado (como imagens e bancos de dados SQLite)
# ao iniciar o script de diretórios de trabalho diferentes.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR:
    os.chdir(SCRIPT_DIR)
    print(f"📂 [DIRETÓRIO] Pasta de trabalho definida para: {os.getcwd()}")

# Carrega dotenv bem no início para que as variáveis afetem as configurações do Flet
try:
    from dotenv import load_dotenv
    load_dotenv() # Carrega .env se existir
except:
    pass

# --- CONFIGURAÇÕES DE AMBIENTE (FLET 0.85 & ESTABILIDADE) ---
# Desativa acessibilidade que causa crashes em loops de identificação rápida
os.environ["FLET_DISABLE_ACCESSIBILITY"] = os.getenv("FLET_DISABLE_ACCESSIBILITY", "1")
os.environ["FLET_FORCE_WEBVIEW_ACCESSIBILITY"] = os.getenv("FLET_FORCE_WEBVIEW_ACCESSIBILITY", "0")
# Aumenta o buffer de mensagens WebSocket para suportar frames de vídeo e fotos em alta resolução
os.environ["FLET_WS_MAX_MESSAGE_SIZE"] = os.getenv("FLET_WS_MAX_MESSAGE_SIZE", "8000000")

# Otimização de renderização para Linux (Harden Industrial)
if sys.platform.startswith("linux"):
    # Permite customizar via .env, padrão "0" (hardware render) ou "1" (software render se der tela preta)
    os.environ["FLET_FORCE_SOFTWARE_RENDER"] = os.getenv("FLET_FORCE_SOFTWARE_RENDER", "0")

import flet as ft
from datetime import datetime, timedelta
import random
import requests
import threading
import qrcode
import io
import base64
import json
import subprocess

# --- POLYFILL PARA ICONES DESCONTINUADOS OU FALTANTES ---
print("Applying Icon Polyfill...")
for icon_name in ["FINGERPRINT", "LOCK_OPEN", "CLOSE", "REFRESH", "REMOVE", "CROP_SQUARE", "PEOPLE", "VIDEOCAM", "SYNC", "HISTORY", "TROUBLESHOOT", "SETTINGS", "CLOUD_DONE", "CHECK_CIRCLE", "SEARCH", "CALENDAR_MONTH", "PERSON", "PERSON_OUTLINE", "LOCK", "ANALYTICS", "MEMORY", "ERROR", "REPLAY"]:
    if not hasattr(ft.Icons, icon_name):
        setattr(ft.Icons, icon_name, icon_name.lower())
print("Polyfill Applied.")

from flask import Flask, jsonify, request

try:
    import cv2
    import numpy as np
except ImportError:
    pass

def nuclear_cleanup():
    """Limpeza agressiva de hardware e processos para destravar o sistema."""
    me = os.getpid()
    try:
        # Limpa drivers e processos de hardware (APENAS LINUX)
        if sys.platform.startswith("linux"):
            subprocess.run(["pkill", "-9", "fprintd"], capture_output=True)
            subprocess.run(["pkill", "-9", "fprintd-verify"], capture_output=True)
            subprocess.run(["pkill", "-9", "fprintd-enroll"], capture_output=True)
            
            # Força o reinício do serviço para resetar o barramento USB do sensor
            # No Linux, pkill -9 fprintd já faz o serviço ser reiniciado pelo systemd se configurado.
            # Removemos o sudo para evitar prompts de senha que travam o startup.
            try: subprocess.run(["pkill", "-9", "fprintd"], capture_output=True)
            except: pass
            
            # Limpa APENAS os daemons biométricos para evitar travar o barramento
            subprocess.run(["pkill", "-9", "fprintd-verify"], capture_output=True)
            subprocess.run(["pkill", "-9", "fprintd-enroll"], capture_output=True)
            subprocess.run(["pkill", "-9", "fprintd"], capture_output=True)

            # Libera dispositivos de vídeo travados (Apenas processos do usuário atual)
            try:
                # Busca PIDs de processos do usuário que estão usando /dev/video*
                res = subprocess.run("lsof -t /dev/video*", shell=True, capture_output=True, text=True)
                pids = res.stdout.strip().split()
                for pid in pids:
                    if pid != str(me):
                        subprocess.run(["kill", "-9", pid], capture_output=True)
            except: pass
            
            print("☢️ [NUCLEAR] Barramento biométrico, câmeras e processos zumbis limpos (Linux).")
        else:
            # No Windows, a limpeza é menos agressiva para evitar matar processos do sistema
            # O Flet gerencia bem suas janelas no Windows
            print("☢️ [NUCLEAR] Modo Windows: Limpeza de hardware simplificada.")
    except Exception as e:
        print(f"⚠️ [NUCLEAR] Falha na limpeza: {e}")

try:
    # DeepFace API Status - Aumentado timeout para 2s para evitar falso negativo em carga
    resp_check = requests.get("http://localhost:8000/api/biometria/verificar/", timeout=2.0)
    DEEPFACE_ONLINE = (resp_check.status_code == 200)
except:
    DEEPFACE_ONLINE = False

print(f"🚀 [SISTEMA] Arquitetura Industrial: {'DeepFace API Online' if DEEPFACE_ONLINE else 'DeepFace API Offline (Usando Fallback Local)'}")

# --- CONFIGURAÇÕES ---
try:
    from dotenv import load_dotenv
    load_dotenv() # Carrega .env se existir
except ImportError:
    pass

SITE_URL = os.getenv("SITE_URL", "https://academiarocksfit.com.br")
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "Rocksfit@2024")
COR_BG = "#0a0a0a" 
COR_PRIMARY = "#f27121"
COR_CARD = "#1a1a1a"
COR_CARD_HIGH = "#252525"
COR_TEXTO = "#ffffff"
COR_TEXT_SEC = "#b0b0b0" # Aumentando contraste do texto secundário
COR_SUCCESS = "#2ecc71"
COR_WARNING = "#f39c12"
COR_ERROR = "#e74c3c"

# Constant used to avoid Flet Image must have 'src' specified error
TRANSPARENT_PIXEL = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oAMBAAIRAxEAPwD+f+iiigD/2Q=="


try:
    # A biometria fprintd é apenas para Linux
    if sys.platform.startswith("linux"):
        from biometria_fprint import BiometriaFPrint
        FPRINT_DISPONIVEL = True
        biometria_manager_global = BiometriaFPrint(SITE_URL, SYNC_TOKEN)
    else:
        FPRINT_DISPONIVEL = False
        biometria_manager_global = None
except ImportError:
    FPRINT_DISPONIVEL = False
    biometria_manager_global = None

# --- MAPA DE DEDOS (Global para evitar recriação) ---
FINGERS_MAPPING = [
    {"id": "left-little-finger",   "label": "Mínimo E",   "left": 106, "top": 263},
    {"id": "left-ring-finger",   "label": "Anelar E",   "left": 158, "top": 219},
    {"id": "left-middle-finger",    "label": "Médio E",    "left": 212, "top": 208},
    {"id": "left-index-finger","label": "Indic. E",   "left": 273, "top": 221},
    {"id": "left-thumb",  "label": "Polegar E",  "left": 343, "top": 305},
    
    {"id": "right-thumb",  "label": "Polegar D",  "left": 442, "top": 306},
    {"id": "right-index-finger","label": "Indic. D",   "left": 515, "top": 224},
    {"id": "right-middle-finger",    "label": "Médio D",    "left": 580, "top": 212},
    {"id": "right-ring-finger",   "label": "Anelar D",   "left": 626, "top": 226},
    {"id": "right-little-finger",   "label": "Mínimo D",   "left": 677, "top": 265},
]

# --- ESTADO GLOBAL (Compartilhado entre abas/sessões) ---
GLOBAL_ALUNOS = []
GLOBAL_EMBEDDINGS_CACHE = {}
GLOBAL_PERFIS = {}
GLOBAL_HISTORICO = []
BIOMETRIA_BUSY = False
PAUSE_BIOMETRIA = False 
ENROLLMENT_ACTIVE = False
BIOMETRIA_MAPPING_CACHE = {} 

# --- SISTEMA DE VISÃO (GLOBAL & INDUSTRIAL) ---
try:
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except:
    FACE_CASCADE = None
SYNC_LOCK = threading.Lock()
CAM_LOCK = threading.Lock()
VISION_LOCK = threading.Lock()
INFERENCE_LOCK = threading.Lock()
GLOBAL_FRAME_COUNT = 0
LAST_INFERENCE_DATA = {"status": "idle", "mat": None}
UI_LOCK = threading.Lock()
PAGE_LOCK = threading.RLock()
MATCH_PROCESSING_LOCK = threading.Lock()
GLOBAL_FRAME_BASE64 = ""
GLOBAL_LAST_FACES = []
NEURAL_WORKER_BUSY = False
GLOBAL_FACE_STREAK = {"mat": None, "count": 0}
IS_PROCESSING_MATCH = False
GLOBAL_PRIORITY_MATRICULA = None 
current_face_streak = {"mat": None, "count": 0}

# --- PERSISTÊNCIA DE CONFIGURAÇÕES ---
CONFIG_FILE = "BIOMETRIA_DATA/config.json"
DEFAULT_CONFIG = {
    "face_threshold": 0.45,
    "face_streak": 3,
    "face_fusion_threshold": 0.38,
    "face_frame_skip": 3,
    "face_model": "hog",
    "face_scale": 0.5,
    "catraca_ip": "169.254.37.150",
    "catraca_porta": 3000,
    "catraca_sentido_entrada": 0,
    "catraca_sentido_saida": 1,
    "camera_enabled": True,
    "fprint_timeout": 30,
    "fprint_retries": 3,
    "cooldown_facial": 30
}

def load_settings():
    os.makedirs("BIOMETRIA_DATA", exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except: return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_settings(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except: pass

def sync_ponte_catraca(key, value):
    """Sincroniza alterações de IP/Porta com o script ponte_catraca.py"""
    try:
        ponte_file = "ponte_catraca.py"
        import os
        if not os.path.exists(ponte_file): return
            
        with open(ponte_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        target = "CATRACA_IP =" if key == "catraca_ip" else "CATRACA_PORTA ="
        new_val = f'"{value}"' if key == "catraca_ip" else f"{value}"
        
        for line in lines:
            if line.strip().startswith(target):
                new_lines.append(f"{target} {new_val} \n")
            else:
                new_lines.append(line)
                
        with open(ponte_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"🔄 [SYNC] {ponte_file} atualizado: {key} -> {value}")
    except Exception as e:
        print(f"⚠️ [SYNC] Erro ao sincronizar ponte_catraca.py: {e}")

CONFIG = load_settings()

# Variáveis globais baseadas na CONFIG (para acesso rápido)
FACE_STRICT_THRESHOLD = CONFIG["face_threshold"]
FACE_FUSION_THRESHOLD = CONFIG["face_fusion_threshold"]
FACE_STREAK_REQUIRED = CONFIG["face_streak"]
FACE_MODEL = CONFIG.get("face_model", "hog")
FACE_SCALE = CONFIG.get("face_scale", 0.5)

def update_global_from_config():
    global FACE_STRICT_THRESHOLD, FACE_FUSION_THRESHOLD, FACE_STREAK_REQUIRED, FACE_MODEL, FACE_SCALE
    FACE_STRICT_THRESHOLD = CONFIG["face_threshold"]
    FACE_FUSION_THRESHOLD = CONFIG["face_fusion_threshold"]
    FACE_STREAK_REQUIRED = CONFIG["face_streak"]
    FACE_MODEL = CONFIG.get("face_model", "hog")
    FACE_SCALE = CONFIG.get("face_scale", 0.5)

# Controle de vazão de updates para evitar saturação do motor Flutter no Linux
LAST_UPDATE_TIME = 0
UI_LOCK = threading.Lock()
# Variáveis de Estado Global
last_access_info = None
last_id_time = 0
PAUSE_BIOMETRIA = False

# Flag global para sinalizar se a engine Flutter ainda está viva
_ENGINE_ALIVE = True

def safe_update(page):
    """Atualização segura da UI com proteção contra crash de engine por sessão"""
    if not page: return
    if not hasattr(page, "_engine_alive"):
        page._engine_alive = True
    
    if not page._engine_alive:
        return

    with PAGE_LOCK:
        try:
            page.update()
        except BaseException as e:
            err = str(e).lower()
            # Se a engine sumiu ou o loop fechou, marcamos como morta para parar loops de thread
            if "engine" in err or "messenger" in err or "view" in err or "thread" in err or "loop" in err or "session" in err:
                page._engine_alive = False
            else:
                pass

def rocksfit_core_update(page, control=None):
    """Garante atualização segura em ambiente multi-thread."""
    safe_update(page)

import sqlite3

# --- ARQUITETURA OFFLINE-FIRST (DATABASE LOCAL) ---
DB_PATH = "BIOMETRIA_DATA/rocksfit_local.db"

def init_local_db():
    """Inicializa o banco de dados local para operação offline."""
    os.makedirs("BIOMETRIA_DATA", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabela de Alunos (Cache do CRM)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            matricula TEXT PRIMARY KEY,
            nome TEXT,
            status TEXT,
            foto_url TEXT,
            vencimento TEXT,
            dias_restantes INTEGER,
            finger_mapping TEXT, -- JSON com os dedos cadastrados
            last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tabela de Digitais (Mapeamento Dedo -> Aluno)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS biometria_map (
            finger_id TEXT,
            matricula TEXT,
            PRIMARY KEY (finger_id, matricula)
        )
    ''')

    # MIGRAÇÃO: Adiciona colunas se não existirem
    try:
        cursor.execute("ALTER TABLE alunos ADD COLUMN vencimento TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE alunos ADD COLUMN dias_restantes INTEGER")
    except: pass
    # Tabela de Logs de Acesso (Buffer para upload posterior)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_acesso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            metodo TEXT,
            sentido TEXT,
            sincronizado INTEGER DEFAULT 0
        )
    ''')
    
    # --- CAMADA DE MIGRAÇÃO (JSON -> SQLITE) ---
    cursor.execute("SELECT count(*) FROM biometria_map")
    if cursor.fetchone()[0] == 0:
        print("🚚 [MIGRAÇÃO] Importando mapeamentos legados para SQLite...")
        PATH_B = "BIOMETRIA_DATA/ALUNOS"
        if os.path.exists(PATH_B):
            for f in os.listdir(PATH_B):
                if f.endswith(".finger"):
                    try:
                        if "_" in f:
                            mat, resto = f.split("_", 1)
                            dedo = resto.replace(".finger", "")
                        else:
                            mat = f.replace(".finger", "")
                            dedo = "right-index-finger"
                        cursor.execute("INSERT OR IGNORE INTO biometria_map (finger_id, matricula) VALUES (?, ?)", (dedo, str(mat)))
                    except: pass
    
    conn.commit()
    conn.close()
    print("🗄️ [DB] Banco de dados local inicializado/sincronizado.")

def salvar_aluno_local(aluno):
    """Persiste ou atualiza um aluno no banco offline."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO alunos (matricula, nome, status, foto_url, vencimento, dias_restantes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (str(aluno.get("matricula")), aluno.get("nome"), aluno.get("status"), aluno.get("foto_url"), aluno.get("vencimento"), aluno.get("dias_restantes")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ [DB] Erro ao salvar aluno: {e}")

def carregar_cache_local():
    """Carrega dados do SQLite e embeddings faciais (.npy) offline para a memória para performance máxima."""
    global GLOBAL_ALUNOS, BIOMETRIA_MAPPING_CACHE, GLOBAL_EMBEDDINGS_CACHE
    try:
        init_local_db()
        
        # --- OTIMIZAÇÃO INDUSTRIAL: AUTO-SINCRONIZAÇÃO OFFLINE (JSON -> SQLITE) ---
        sync_file = "ALUNOS_SYNC.json"
        if os.path.exists(sync_file):
            try:
                with open(sync_file, "r", encoding="utf-8") as sf:
                    sync_data = json.load(sf)
                if isinstance(sync_data, list) and len(sync_data) > 0:
                    conn_sync = sqlite3.connect(DB_PATH)
                    cur_sync = conn_sync.cursor()
                    for item in sync_data:
                        cur_sync.execute('''
                            INSERT OR REPLACE INTO alunos (matricula, nome, status, foto_url, vencimento, dias_restantes)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            str(item.get("matricula")),
                            item.get("nome"),
                            item.get("status"),
                            item.get("foto_url"),
                            item.get("vencimento"),
                            item.get("dias_restantes", 0)
                        ))
                    conn_sync.commit()
                    conn_sync.close()
            except Exception as ex_sync:
                print(f"⚠️ [DB] Falha ao sincronizar ALUNOS_SYNC.json com SQLite: {ex_sync}")
        
        # Carrega os dados atualizados do SQLite para o cache em memória
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Carrega Alunos
        cursor.execute("SELECT * FROM alunos")
        rows = cursor.fetchall()
        GLOBAL_ALUNOS = [dict(r) for r in rows]
        
        # Carrega Mapeamento Biométrico
        cursor.execute("SELECT * FROM biometria_map")
        map_rows = cursor.fetchall()
        BIOMETRIA_MAPPING_CACHE = {}
        for r in map_rows:
            f_id = r["finger_id"]
            if f_id not in BIOMETRIA_MAPPING_CACHE: BIOMETRIA_MAPPING_CACHE[f_id] = []
            BIOMETRIA_MAPPING_CACHE[f_id].append(str(r["matricula"]))
            
        conn.close()
        
        # OTIMIZAÇÃO INDUSTRIAL: Carrega os templates faciais (.npy) em memória
        GLOBAL_EMBEDDINGS_CACHE = {}
        faces_dir = "BIOMETRIA_DATA/faces"
        if os.path.exists(faces_dir):
            import numpy as np
            for f in os.listdir(faces_dir):
                if f.endswith(".npy"):
                    matricula = f.replace(".npy", "")
                    try:
                        GLOBAL_EMBEDDINGS_CACHE[str(matricula)] = np.load(os.path.join(faces_dir, f))
                    except: pass
        print(f"📦 [CACHE] {len(GLOBAL_ALUNOS)} alunos, {len(map_rows)} mapeamentos digitais e {len(GLOBAL_EMBEDDINGS_CACHE)} templates faciais (.npy) carregados em memória.")
        
        def prewarm_deepface():
            try:
                print("🧠 [VISION PRE-WARM] Pré-carregando DeepFace/ArcFace em segundo plano...")
                from deepface import DeepFace
                import numpy as np
                dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
                DeepFace.represent(
                    img_path=dummy_frame,
                    model_name="ArcFace",
                    enforce_detection=False,
                    detector_backend="skip"
                )
                print("🧠 [VISION PRE-WARM] DeepFace/ArcFace carregado com sucesso em memória e pronto para uso instantâneo!")
            except Exception as e:
                print(f"⚠️ [VISION PRE-WARM] Falha ao pré-carregar DeepFace: {e}")
        
        threading.Thread(target=prewarm_deepface, daemon=True).start()
    except Exception as e:
        print(f"⚠️ [CACHE] Falha ao carregar banco local: {e}")

def atualizar_mapping_local(matricula, finger_id, acao="ADD"):
    """Sincroniza o mapeamento de digital no banco local."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if acao == "ADD":
            cursor.execute("INSERT OR REPLACE INTO biometria_map (finger_id, matricula) VALUES (?, ?)", (finger_id, str(matricula)))
        else:
            cursor.execute("DELETE FROM biometria_map WHERE finger_id = ? AND matricula = ?", (finger_id, str(matricula)))
        conn.commit()
        conn.close()
        # Recarrega cache em memória
        carregar_cache_local()
    except Exception as e:
        print(f"⚠️ [DB] Erro ao atualizar mapping: {e}")

def registrar_acesso_local(matricula, metodo, sentido):
    """Loga o acesso localmente para auditoria e sincronização futura (Industrial)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Forçamos o uso de datetime('now', 'localtime') para garantir precisão industrial
        cursor.execute('''
            INSERT INTO logs_acesso (matricula, metodo, sentido, timestamp)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        ''', (str(matricula), metodo, sentido))
        conn.commit()
        conn.close()
        print(f"📝 [LOG] Acesso registrado localmente (SQLite): {matricula}")
    except Exception as e:
        print(f"⚠️ [LOG] Falha ao registrar acesso local: {e}")

def salvar_cache_local():
    """Fallback: Salva também em JSON, mas prioriza SQLite."""
    global GLOBAL_ALUNOS
    try:
        # Salva no SQLite
        for aluno in GLOBAL_ALUNOS:
            salvar_aluno_local(aluno)
    except: pass

# Dados iniciais vazios (serão preenchidos pelo CRM)
MOCK_ALUNOS = []
MOCK_HISTORICO = []

def atualizar_cache_digital(matricula, dedo, acao="ADD"):
    """Sincroniza o mapeamento de digital no banco local e na memória."""
    global BIOMETRIA_MAPPING_CACHE
    
    # Persistência em SQLite (Nova Arquitetura)
    atualizar_mapping_local(matricula, dedo, acao)
    
    # Sincronização em tempo real da memória (Garante reconhecimento imediato)
    if acao == "ADD":
        if dedo not in BIOMETRIA_MAPPING_CACHE:
            BIOMETRIA_MAPPING_CACHE[dedo] = []
        if matricula not in BIOMETRIA_MAPPING_CACHE[dedo]:
            BIOMETRIA_MAPPING_CACHE[dedo].append(matricula)
    elif acao == "DEL":
        if dedo in BIOMETRIA_MAPPING_CACHE and matricula in BIOMETRIA_MAPPING_CACHE[dedo]:
            BIOMETRIA_MAPPING_CACHE[dedo].remove(matricula)
            if not BIOMETRIA_MAPPING_CACHE[dedo]: del BIOMETRIA_MAPPING_CACHE[dedo]

    # Logs para auditoria local
    print(f"📊 [DB] Mapeamento atualizado: {matricula} | {dedo} | Ação: {acao}")

def safe_pubsub_send(msg):
    global page_global
    if page_global:
        try:
            page_global.pubsub.send_all(msg)
        except Exception:
            pass

def trigger_catraca(direcao="ENTRADA"):
    """Dispara o relé da catraca via socket industrial com lógica de retentativa"""
    ip = CONFIG.get("catraca_ip", "169.254.37.150")
    porta = int(CONFIG.get("catraca_porta", 1001))
    
    # Lógica de Rotação Baseada em Configuração
    if direcao == "ENTRADA":
        cmd_code = CONFIG.get("catraca_sentido_entrada", 0)
        msg = "Liberou Entrada"
    elif direcao == "SAIDA":
        cmd_code = CONFIG.get("catraca_sentido_saida", 1)
        msg = "Liberou Saida"
    else:
        cmd_code = 0
        msg = "Liberou Geral"

    # Estratégia de Retentativa Industrial
    for attempt in range(3):
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((ip, porta))
                
                # Wake-up sequence (mcg) - Importante para despertar a placa Toletus
                s.sendall(b"mcg")
                time.sleep(0.1)

                # Payload Toletus: lgu + Byte Nulo (ou cmd_code) + Mensagem
                payload = b"lgu" + bytes([cmd_code]) + msg.encode('cp1252')
                s.sendall(payload)
                print(f"🔓 [HARDWARE] Comando {direcao} enviado com sucesso para {ip}:{porta}")
                safe_pubsub_send({"type": "hw_status", "hw": "catraca", "online": True})
                return True
        except Exception as e:
            safe_pubsub_send({"type": "hw_status", "hw": "catraca", "online": False})
            print(f"⚠️ [HARDWARE] Falha na tentativa {attempt+1}/3: {e}")
            time.sleep(0.5)
    
    safe_pubsub_send({"type": "hw_status", "hw": "catraca", "online": False})
    print(f"❌ [HARDWARE] Falha crítica ao disparar catraca após 3 tentativas.")
    return False

def registrar_acesso_crm(matricula, metodo="DIGITAL"):
    """Tenta registrar o histórico no CRM via múltiplos endpoints"""
    endpoints = [
        f"{SITE_URL}/api/catraca-check/{matricula}/?token={SYNC_TOKEN}&log=1&metodo={metodo}",
        f"{SITE_URL}/api/catraca-log/{matricula}/?token={SYNC_TOKEN}&metodo={metodo}",
        f"{SITE_URL}/api/catraca-history-save/?matricula={matricula}&metodo={metodo}&token={SYNC_TOKEN}"
    ]
    for url in endpoints:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                print(f"✅ [CRM] Histórico remoto atualizado ({metodo})")
                return True
        except: pass
    return False

# --- MONITORAMENTO REMOTO (INTEGRAÇÃO CRM) ---
def loop_monitoramento_remoto():
    """Vigia o CRM para liberar a catraca via comandos do site (Polling)"""
    print("📡 [INTEGRAÇÃO] Monitoramento remoto do CRM ativo.")
    POLLING_URL = f"{SITE_URL}/api/catraca-polling/?token={SYNC_TOKEN}"
    
    while True:
        try:
            # Pergunta ao site se há algum comando de liberação pendente
            response = requests.get(POLLING_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # O CRM envia uma lista em 'liberacoes'
                liberacoes = data.get("liberacoes", [])
                for lib in liberacoes:
                    print(f"🚀 [CRM] Liberação remota para: {lib.get('nome')}!")
                    trigger_catraca(direcao="ENTRADA")
            
        except Exception as e:
            # Erros de rede são comuns no polling, apenas ignoramos para não travar
            pass
        
        time.sleep(2) # Verifica a cada 2 segundos

# Inicia o monitoramento em segundo plano
threading.Thread(target=loop_monitoramento_remoto, daemon=True).start()

# --- API BRIDGE PARA O CRM (FLASK) ---
api_app = Flask(__name__)
manager_global = None
BIOMETRIA_BUSY = False # Flag para evitar conflito entre Verificação e Cadastro
page_global = None
GLOBAL_LOOP_STARTED = False
GLOBAL_SESSION_STATES = []
GLOBAL_PRIORITY_MATRICULA = None

@api_app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def requires_token(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        token = request.args.get('token') or request.headers.get('Authorization')
        if token and token.startswith('Token '):
            token = token.split(' ')[1]
        if token != SYNC_TOKEN:
            return jsonify({"success": False, "error": "Acesso não autorizado. Token inválido."}), 401
        return f(*args, **kwargs)
    return decorated

@api_app.route('/api/enroll/<matricula>', methods=['GET', 'POST', 'OPTIONS'])
@requires_token
def api_enroll(matricula):
    global BIOMETRIA_BUSY
    if not manager_global:
        return jsonify({"success": False, "error": "Hardware não inicializado"}), 500
    
    # Notifica a UI do Flet para abrir o quadro
    if page_global:
        # Busca o aluno no cache global
        aluno = next((a for a in GLOBAL_ALUNOS if str(a.get("matricula")) == str(matricula)), {"matricula": matricula, "nome": "Aluno Externo"})
        safe_pubsub_send({"type": "open_enroll", "aluno": aluno})
        
    return jsonify({"success": True, "message": "Quadro de captura aberto no terminal de recepção."})

@api_app.route('/api/liberar', methods=['GET', 'POST', 'OPTIONS'])
@requires_token
def api_liberar_geral():
    success = trigger_catraca("ENTRADA")
    return jsonify({"success": success, "message": "Comando enviado para a catraca"})

@api_app.route('/api/liberar-entrada', methods=['GET', 'POST', 'OPTIONS'])
@requires_token
def api_liberar_entrada():
    success = trigger_catraca("ENTRADA")
    return jsonify({"success": success, "message": "Entrada liberada"})

@api_app.route('/api/liberar-saida', methods=['GET', 'POST', 'OPTIONS'])
@requires_token
def api_liberar_saida():
    success = trigger_catraca("SAIDA")
    return jsonify({"success": success, "message": "Saida liberada"})

# Definição do servidor de ponte CRM (Inicia apenas no bloco main)
def run_api():
    print("🌐 API Bridge iniciada em http://0.0.0.0:8553")
    api_app.run(host='0.0.0.0', port=8553, debug=False, threaded=True)


def is_liberado(status):
    """Verifica se o status recebido é considerado liberado/ativo de forma resiliente"""
    if not status: return False
    s = str(status).lower().strip()
    return s in ["ativo", "liberado", "pago", "ok", "true", "1", "yes", "sim"]

def detectar_sentido_acesso(matricula, metodo="DIGITAL"):
    """
    Verifica se o aluno está entrando ou saindo baseado no log do dia (Toggle Inteligente)
    Implementa carência inteligente: 3 segundos para Digital/Biometria e configurável (30s) para Facial.
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
            for line in lines[1:]: # Pula cabeçalho
                parts = line.strip().split(";")
                if len(parts) >= 3:
                    if parts[2].strip().upper() == mat_str:
                        count += 1
                        try:
                            # Tenta ler a data e hora do log (Data;Hora;...)
                            dt_str = f"{parts[0]} {parts[1]}"
                            ultimo_acesso = datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
                        except: pass
        
        # Carência inteligente baseada no método de identificação
        cooldown = 3 if metodo == "DIGITAL" else CONFIG.get("cooldown_facial", 30)
        if ultimo_acesso:
            delta = (datetime.now() - ultimo_acesso).total_seconds()
            if delta < cooldown:
                print(f"⏳ [FLUXO] Matrícula {mat_str} reconhecida muito rápido via {metodo} ({delta:.1f}s). Ignorando.")
                return "ENTRADA" if count % 2 == 0 else "SAÍDA", False

        # Se o contador é ímpar, o próximo estado é SAÍDA
        sentido = "SAÍDA" if count % 2 != 0 else "ENTRADA"
        print(f"📊 [FLUXO] Matrícula {mat_str} possui {count} registros hoje. Definido como: {sentido}")
        return sentido, True
    except Exception as e:
        print(f"⚠️ [FLUXO] Erro ao detectar sentido: {e}")
        return "ENTRADA", True

def log_acesso_local(aluno, metodo, status, sentido="ENTRADA"):
    try:
        hoje = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("BIOMETRIA_DATA/LOGS", exist_ok=True)
        log_path = os.path.join("BIOMETRIA_DATA/LOGS", f"ACESSOS_{hoje}.csv")
        file_exists = os.path.isfile(log_path)
        agora = datetime.now(); data_str = agora.strftime("%d/%m/%Y"); hora_str = agora.strftime("%H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            if not file_exists: f.write("Data;Hora;Matricula;Nome;Metodo;Status;Sentido\n")
            f.write(f"{data_str};{hora_str};{aluno.get('matricula')};{aluno.get('nome')};{metodo};{status};{sentido}\n")
    except: pass
def auto_calibrate_threshold(page, lbl_face_thr, lbl_face_streak, lbl_face_skip, lbl_face_scale, slider_thr, slider_streak, slider_skip, slider_scale, update_config_fn):
    """
    Autorregulagem Inteligente – Rocks-Fit
    Captura um frame, mede o brilho e calibra TODO o motor neural:
    - face_threshold  → Sensibilidade
    - face_streak     → Ciclos de confirmação
    - face_frame_skip → Velocidade de análise
    - face_scale      → Resolução de análise
    """

    def _calibrar():
        try:
            frame = None
            shared_path = "BIOMETRIA_DATA/shared_frame.jpg"
            if os.path.exists(shared_path):
                try:
                    frame = cv2.imread(shared_path)
                except: pass
            
            if frame is None:
                cap = None
                for dev_idx in [0, 2, 4, 1, 3]:
                    try:
                        temp = cv2.VideoCapture(dev_idx)
                        if temp and temp.isOpened():
                            cap = temp; break
                        if temp: temp.release()
                    except: pass

                if not cap:
                    print("⚠️ [CALIB] Câmera não disponível.")
                    return

                for _ in range(8):
                    cap.read()
                    time.sleep(0.04)

                ret, frame = cap.read()
                cap.release()

            if frame is None: return

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            brightness = float(np.mean(hsv[:, :, 2]))

            # Matriz de Calibração Industrial
            if brightness < 60:
                new_thr, new_streak, new_skip, new_scale = 0.45, 1, 2, 0.60
                perfil = "🌑 ESCURO"
            elif brightness < 110:
                new_thr, new_streak, new_skip, new_scale = 0.50, 1, 3, 0.50
                perfil = "🌥️ MEIA-LUZ"
            elif brightness < 170:
                new_thr, new_streak, new_skip, new_scale = 0.52, 1, 4, 0.50
                perfil = "☀️ BOM"
            elif brightness < 220:
                new_thr, new_streak, new_skip, new_scale = 0.55, 1, 5, 0.45
                perfil = "🌟 MUITO CLARO"
            else:
                new_thr, new_streak, new_skip, new_scale = 0.58, 1, 6, 0.40
                perfil = "💡 SUPEREXPOSTO"

            print(f"🔆 [CALIB] {perfil} ({brightness:.0f}/255)")
            
            # Aplica no motor
            update_config_fn("face_threshold", new_thr)
            update_config_fn("face_streak", new_streak)
            update_config_fn("face_frame_skip", new_skip)
            update_config_fn("face_scale", new_scale)

            # Atualiza UI
            try:
                with PAGE_LOCK:
                    if lbl_face_thr: lbl_face_thr.value = f"Sensibilidade (Threshold): {new_thr}"
                    if lbl_face_streak: lbl_face_streak.value = f"Ciclos de Confirmação (Streak): {new_streak}"
                    if lbl_face_skip: lbl_face_skip.value = f"Frequência de Análise (Frames): {new_skip}"
                    if lbl_face_scale: lbl_face_scale.value = f"Escala de Análise: {int(new_scale*100)}%"
                    
                    if slider_thr: slider_thr.value = new_thr
                    if slider_streak: slider_streak.value = float(new_streak)
                    if slider_skip: slider_skip.value = float(new_skip)
                    if slider_scale: slider_scale.value = new_scale
                    
                    safe_update(page)
            except: pass

        except Exception as ex:
            print(f"❌ [CALIB] Erro: {ex}")

    threading.Thread(target=_calibrar, daemon=True).start()

def abrir_cadastro_digital(aluno, page: ft.Page, biometria_manager, render_main_content, state):
    """Módulo Industrial de Captura Biográfica (ESTABILIDADE MÁXIMA - FIXED DASHBOARD)"""
    global BIOMETRIA_BUSY, PAUSE_BIOMETRIA, ENROLLMENT_ACTIVE
    if ENROLLMENT_ACTIVE: return # Evita reentrância/cliques duplos
    ENROLLMENT_ACTIVE = True
    finger_units = {} 
    
    COR_ACCENT = COR_PRIMARY
    
    if BIOMETRIA_BUSY or not PAUSE_BIOMETRIA:
        print("🛑 [FPRINT] Solicitando parada do loop para cadastro...")
        PAUSE_BIOMETRIA = True
        try:
            with open("BIOMETRIA_DATA/scanner_status.json", "w") as f:
                json.dump({"status": "ENROLLING", "timestamp": time.time()}, f)
        except: pass
        if biometria_manager: 
            biometria_manager.pause()
        # Tempo curto para o hardware estabilizar
        time.sleep(0.5)
        
    try:
        # Garante estado atômico de cadastro
        BIOMETRIA_BUSY = True
        PAUSE_BIOMETRIA = True
        ENROLLMENT_ACTIVE = True 
        nome = aluno.get("nome", "Membro").upper()
        matricula = str(aluno.get("matricula"))
        
        status_captura = ft.Text("AGUARDANDO SELEÇÃO", color="#ffffff", size=12, weight="bold")
        sw_calib = ft.Switch(label="AJUSTAR POSIÇÕES", value=False, active_color=COR_PRIMARY)
        log_messages = ft.Column(scroll="auto", spacing=5)

        def add_log(msg, color=COR_TEXT_SEC):
            timestamp = time.strftime("%H:%M:%S")
            print(f"📝 [LOG] {msg}")
            log_messages.controls.append(
                ft.Row([
                    ft.Text(f"[{timestamp}]", color="#444444", size=9, weight="bold"),
                    ft.Text(f" {msg}", color=color, size=11, weight="bold", expand=True)
                ], spacing=5)
            )
            if len(log_messages.controls) > 30: log_messages.controls.pop(0)
            
            # ATUALIZAÇÃO AGRESSIVA DE LOG
            try:
                log_messages.update()
                safe_update(page)
            except: pass

        def fechar_dlg(_=None):
            global BIOMETRIA_BUSY, PAUSE_BIOMETRIA, ENROLLMENT_ACTIVE
            
            BIOMETRIA_BUSY = False
            PAUSE_BIOMETRIA = False
            ENROLLMENT_ACTIVE = False
            state["close_enroll"] = None # Limpa referência de fechamento
            
            # Limpa referência de fechamento externo
            state["close_enroll"] = None
            
            if biometria_manager: 
                biometria_manager.resume()
                biometria_manager.stop_all()
            
            with UI_LOCK:
                if "enroll_layer" in state:
                    state["enroll_layer"].visible = False
                    state["enroll_layer"].content = None
                render_main_content()
                page.update()
            
            print("🔄 [FPRINT] Voltando ao dashboard principal...")

        # Disponibiliza o fechamento para o menu lateral
        state["close_enroll"] = fechar_dlg

        # Verifica se imagem existe para evitar placeholder cinza
        HAND_IMAGE_PATH = "media/imagens/biometric_hand_premium.png"
        if os.path.exists(HAND_IMAGE_PATH):
            hand_bg_content = ft.Image(
                src=HAND_IMAGE_PATH,
                fit="cover",
                opacity=0.9,
                border_radius=12
            )
        else:
            # Fallback visual elegante quando não há imagem
            hand_bg_content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.FINGERPRINT, size=80, color=COR_PRIMARY),
                    ft.Text("MAPA BIOMÉTRICO", size=14, weight="bold", color=COR_PRIMARY, text_align="center"),
                    ft.Text("Toque no sensor para cadastrar", size=11, color=COR_TEXT_SEC, text_align="center"),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True,
                bgcolor="#0a0a0a",
                border_radius=12,
            )

        # DASHBOARD PREMIUM (CYBER-INDUSTRIAL)
        main_layout = ft.Container(
            expand=True, bgcolor="#050505", border_radius=20, padding=10,
            content=ft.Row([
                # Mapa de Captura (Esquerda)
                ft.Container(
                    expand=75, bgcolor="#000000", border_radius=15,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Container(
                        expand=True,
                        aspect_ratio=1.0, # Proporção quadrada para preencher o quadro sem bordas pretas
                        alignment=ft.Alignment(0, 0),
                        border=ft.Border.all(2, COR_PRIMARY), # Quadro ajustado à imagem
                        border_radius=15,
                        padding=2,
                        content=ft.Stack(
                            expand=True,
                            controls=[hand_bg_content]
                        )
                    )
                ),
                # Painel de Controle (Direita)
                ft.Container(
                    expand=25, bgcolor="#0a0a0a", border_radius=15, padding=20,
                    border=ft.Border.all(1, "#ffffff05"),
                    content=ft.Column([
                        ft.Text(nome, size=20, weight="bold", color=COR_PRIMARY, overflow="ellipsis"),
                        ft.Text(f"MATRÍCULA: {matricula}", size=11, color=COR_TEXT_SEC),
                        ft.Divider(height=15, color="#ffffff10"),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("STATUS DO SENSOR", size=9, weight="bold", color="#888888"),
                                ft.Row([ft.Icon(ft.Icons.WIFI, color=COR_PRIMARY, size=16), status_captura], spacing=10),
                            ]),
                            bgcolor="#1a1a1a", padding=12, border_radius=12,
                            border=ft.Border.all(1, "#ffffff10")
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text("CONFIGURAÇÃO DE INTERFACE", size=9, weight="bold", color="#888888"),
                                sw_calib,
                            ]),
                            bgcolor="#1a1a1a", padding=12, border_radius=12,
                            border=ft.Border.all(1, "#ffffff10")
                        ),
                        ft.Row([
                            ft.Text("LOG DE OPERAÇÕES", size=10, weight="bold", color=COR_TEXT_SEC),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(
                            expand=True, bgcolor="#000000", border_radius=12, padding=10, 
                            content=log_messages, border=ft.Border.all(1, "#ffffff05"),
                        ),
                        ft.Column([
                            ft.ElevatedButton(
                                "RESETAR POSIÇÕES", 
                                icon="restore", 
                                on_click=lambda _: reset_coords(), 
                                width=300, height=40, 
                                style=ft.ButtonStyle(bgcolor="#442222", color="white", shape=ft.RoundedRectangleBorder(radius=8))
                            ),
                            ft.ElevatedButton(
                                "CONCLUIR CADASTRO", 
                                icon="check_circle", 
                                on_click=lambda _: fechar_dlg(None), 
                                width=300, height=50, 
                                style=ft.ButtonStyle(bgcolor=COR_PRIMARY, color="white", shape=ft.RoundedRectangleBorder(radius=10))
                            )
                        ], spacing=10)
                    ], spacing=10)
                )
            ], spacing=10)
        )

        hand_stack = main_layout.content.controls[0].content.content
        
        # SISTEMA DE COORDENADAS PERSISTENTE
        PATH_COORDS = "BIOMETRIA_DATA/config_coords.json"
        
        def load_custom_coords():
            default = [
                {"id": "left-little-finger", "pos": [80, 241], "lbl": "Mínimo E"},
                {"id": "left-ring-finger", "pos": [145, 190], "lbl": "Anelar E"},
                {"id": "left-middle-finger", "pos": [201, 172], "lbl": "Médio E"},
                {"id": "left-index-finger", "pos": [268, 171], "lbl": "Indicador E"},
                {"id": "left-thumb", "pos": [371, 280], "lbl": "Polegar E"},
                {"id": "right-thumb", "pos": [457, 283], "lbl": "Polegar D"},
                {"id": "right-index-finger", "pos": [540, 182], "lbl": "Indicador D"},
                {"id": "right-middle-finger", "pos": [623, 166], "lbl": "Médio D"},
                {"id": "right-ring-finger", "pos": [676, 188], "lbl": "Anelar D"},
                {"id": "right-little-finger", "pos": [724, 229], "lbl": "Mínimo D"},
            ]
            if os.path.exists(PATH_COORDS):
                try:
                    with open(PATH_COORDS, "r") as f:
                        saved = json.load(f)
                        # Mescla com labels padrões
                        for d in default:
                            if d["id"] in saved: d["pos"] = saved[d["id"]]
                        return default
                except: return default
            return default

        dedos_config = load_custom_coords()

        def save_coords():
            try:
                data = {d["id"]: d["pos"] for d in dedos_config}
                os.makedirs("BIOMETRIA_DATA", exist_ok=True)
                with open(PATH_COORDS, "w") as f:
                    json.dump(data, f)
                add_log("💾 POSIÇÕES SALVAS NO DISCO", COR_SUCCESS)
            except Exception as e:
                add_log(f"Erro ao salvar: {e}", COR_ERROR)

        def reset_coords():
            if os.path.exists(PATH_COORDS):
                try: os.remove(PATH_COORDS)
                except: pass
            nonlocal dedos_config
            dedos_config = load_custom_coords()
            update_fingers_ui()
            add_log("♻️ POSIÇÕES RESETADAS PARA O PADRÃO", COR_SUCCESS)

        def move_finger(e: ft.DragUpdateEvent, f_id):
            if not sw_calib.value: return # Travado - Impede movimento acidental
            
            # Cálculo de escala lógica baseado no AspectRatio 1:1
            p_w = page.width if page.width else 1200
            p_h = page.height if page.height else 800
            avail_w = (p_w - 30) * 0.75
            avail_h = p_h - 20
            
            # Fator de escala para sistema lógico 1000x1000
            scale = min(avail_w / 1000, avail_h / 1000)

            for d in dedos_config:
                if d["id"] == f_id:
                    # Atualiza coordenadas lógicas (0-1000)
                    d["pos"][0] = max(0, min(1000, d["pos"][0] + e.delta_x / scale))
                    d["pos"][1] = max(0, min(1000, d["pos"][1] + e.delta_y / scale))
                    
                    # Atualiza o controle visual diretamente para não quebrar a sessão de Pan (drag)
                    px, py = d["pos"]
                    unit = finger_units[f_id]
                    unit.left = px * scale
                    unit.top = py * scale
                    try: unit.update()
                    except: pass
                    break

        def log_coords():
            save_coords() # Salva no arquivo
            add_log("📍 COORDENADAS ATUALIZADAS", COR_ACCENT)

        def update_fingers_ui():
            # Reutiliza os controles existentes para evitar cintilação e perda de estado
            enrolled = biometria_manager.get_enrolled_fingers(matricula) if biometria_manager else []
            
            p_w = page.width if page.width else 1200
            p_h = page.height if page.height else 800
            # Usamos a mesma lógica de porcentagem do layout 1:1
            avail_w = (p_w - 30) * 0.75
            avail_h = p_h - 20
            scale = min(avail_w / 1000, avail_h / 1000)

            # Se o stack estiver vazio ou apenas com a imagem, inicializa os dedos
            if len(hand_stack.controls) <= 1:
                hand_stack.controls = [hand_stack.controls[0]] # Garante que a imagem está lá
                for d in dedos_config:
                    f_id = d["id"]
                    # Criação inicial do controle (GestureDetector)
                    unit = ft.GestureDetector(
                        content=ft.Stack([
                            ft.Container( # btn_finger_base
                                content=ft.Column([
                                    ft.Container(
                                        width=52, height=52, border_radius=26, 
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Icon(ft.Icons.FINGERPRINT, size=28)
                                    ),
                                    ft.Container(
                                        content=ft.Text(d["lbl"], size=9, weight="bold", color="white"),
                                        bgcolor="#000000dd", padding=ft.Padding(left=8, right=8, top=2, bottom=2), border_radius=4
                                    )
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                                on_click=lambda _, id_d=f_id, lbl_d=d["lbl"]: _execute_enroll(id_d, lbl_d),
                            ),
                            ft.Container( # btn_del_base
                                content=ft.Icon(ft.Icons.CLOSE, size=10, color="white"),
                                width=18, height=18, border_radius=9, bgcolor=COR_ERROR,
                                border=ft.Border.all(1, "white"),
                                left=32, top=-3
                            )
                        ], width=70, height=80),
                        on_pan_update=lambda e, f_id=f_id: move_finger(e, f_id),
                    )
                    finger_units[f_id] = unit
                    hand_stack.controls.append(unit)

            # Atualização cirúrgica de propriedades
            for d in dedos_config:
                f_id = d["id"]
                is_on = f_id in enrolled
                unit = finger_units[f_id]
                
                # Atualiza Posição (Lógica 1000x1000)
                unit.left = d["pos"][0] * scale
                unit.top = d["pos"][1] * scale
                
                # Acessa os componentes internos para atualizar status (cor/visibilidade)
                # unit (GestureDetector) -> Stack -> [Container(Finger), Container(Del)]
                stack = unit.content
                btn_finger_cont = stack.controls[0]
                btn_del_cont = stack.controls[1]
                
                # Atualiza visual do círculo da digital
                circle = btn_finger_cont.content.controls[0]
                icon = circle.content
                circle.bgcolor = COR_SUCCESS if is_on else "#1a1a1a"
                circle.border = ft.Border.all(2, COR_SUCCESS if is_on else "#444444")
                circle.shadow = ft.BoxShadow(spread_radius=1, blur_radius=15, color=COR_SUCCESS + "40") if is_on else None
                icon.color = "white" if is_on else COR_TEXT_SEC
                
                # Atualiza botão de deletar
                btn_del_cont.visible = is_on
                btn_del_cont.on_click = lambda _, id_d=f_id, lbl_d=d["lbl"]: confirm_delete(id_d, lbl_d)

            try:
                hand_stack.update()
                safe_update(page)
            except: 
                rocksfit_core_update(page)

        def confirm_delete(finger_id, label):
            def handle_delete(_):
                overlay.visible = False
                rocksfit_core_update(page)
                add_log(f"Removendo digital: {label}...", COR_WARNING)
                if biometria_manager.apagar_digital_local(matricula, finger_id):
                    add_log(f"✔ Registro de {label} apagado.", COR_SUCCESS)
                    atualizar_cache_digital(matricula, finger_id, acao="DEL")
                    update_fingers_ui()
                else:
                    add_log(f"Falha ao apagar {label}.", COR_ERROR)
                rocksfit_core_update(page)

            overlay = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("CONFIRMAR EXCLUSÃO", size=18, weight="bold", color="white"),
                        ft.Text(f"Deseja apagar o registro de {label}?", color=COR_TEXT_SEC),
                        ft.Row([
                            ft.ElevatedButton("SIM, APAGAR", bgcolor=COR_ERROR, color="white", on_click=handle_delete),
                            ft.TextButton("CANCELAR", on_click=lambda _: (setattr(overlay, "visible", False), rocksfit_core_update(page)))
                        ], alignment=ft.MainAxisAlignment.END)
                    ], spacing=20, tight=True),
                    bgcolor=COR_BG, padding=30, border_radius=15, width=400,
                    border=ft.Border.all(1, "#ffffff20")
                ),
                alignment=ft.Alignment(0, 0),
                bgcolor="#000000dd",
                expand=True,
                visible=True
            )
            page.overlay.append(overlay)
            rocksfit_core_update(page)

        def _execute_enroll(finger_id, label):
            add_log(f"🖐️ Iniciando captura: {label}...", COR_PRIMARY)
            status_captura.value = f"CAPTURA: {label.upper()}"
            status_captura.color = COR_PRIMARY
            rocksfit_core_update(page)
            
            def _thread():
                try:
                    add_log("🔄 Iniciando hardware biométrico...", COR_WARNING)
                    biometria_manager.stop_all()
                    time.sleep(0.8)
                    
                    proc = biometria_manager.enroll(matricula, finger_id)
                    if proc:
                        success = False
                        add_log(f"🖐️ AGUARDANDO TOQUES ({label})", COR_ACCENT)
                        while True:
                            line = proc.stdout.readline()
                            err_line = proc.stderr.readline()
                            
                            if err_line:
                                msg_err = err_line.strip()
                                if "already claimed" in msg_err.lower():
                                    add_log("❌ ERRO: Sensor em uso por outro app!", COR_ERROR)
                                else:
                                    add_log(f"⚠️ {msg_err}", COR_WARNING)
                            
                            if not line: break
                            line = line.strip()
                            if "enroll-stage-passed" in line:
                                add_log("⚡ Toque detectado! Continue...", COR_SUCCESS)
                            elif "enroll-retry-scan" in line:
                                add_log("⚠️ Falha na leitura. Tente novamente.", COR_WARNING)
                            elif "enroll-completed" in line:
                                success = True
                                break
                        
                        proc.wait()
                        if success or proc.returncode == 0:
                            biometria_manager.guardar_arquivo_local(matricula, finger_id)
                            atualizar_cache_digital(matricula, finger_id, acao="ADD")
                            add_log(f"✅ {label.upper()} CADASTRADO!", COR_SUCCESS)
                            time.sleep(0.5)
                        else:
                            add_log(f"✖ Captura cancelada ou falhou.", COR_ERROR)
                    else:
                        add_log("❌ Falha crítica ao abrir driver fprintd.", COR_ERROR)
                except Exception as e:
                    add_log(f"Erro Crítico: {e}", COR_ERROR)
                finally:
                    status_captura.value = "AGUARDANDO SELEÇÃO"
                    status_captura.color = COR_TEXT_SEC
                    update_fingers_ui()
                    rocksfit_core_update(page)

            threading.Thread(target=_thread, daemon=True).start()

        # Botão extra no painel de controle para salvar posições
        main_layout.content.controls[1].content.controls.insert(-1, ft.ElevatedButton(
            "SALVAR COORDENADAS", 
            icon=ft.Icons.SAVE_ALT, 
            on_click=lambda _: log_coords(),
            width=300, height=40,
            style=ft.ButtonStyle(bgcolor="#1a1a1a", color=COR_ACCENT, shape=ft.RoundedRectangleBorder(radius=8))
        ))

        # ARQUITETURA DE CAMADAS (STACK) - PREVINE REMOVE_VIEW CRASH
        with UI_LOCK:
            if "enroll_layer" in state:
                layer = state["enroll_layer"]
                layer.content = main_layout
                layer.visible = True
                page.update()
            
        # Registrar evento de resize para manter os dedos no lugar responsivamente
        def handle_resize(e):
            if ENROLLMENT_ACTIVE:
                try: update_fingers_ui()
                except: pass
        page.on_resize = handle_resize
        
        update_fingers_ui()
        print(f"✅ [UI] Camada de cadastro ativa para: {nome}")
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"💥 ERRO AO ABRIR MODAL: {e}\n{error_msg}")
        BIOMETRIA_BUSY = False
        ENROLLMENT_ACTIVE = False
        PAUSE_BIOMETRIA = False

def main(page: ft.Page):
    # Previne Stack Overflow desativando área de seleção global
    try: page.selection_area = False
    except: pass

    def _safe_page_update(control=None):
        rocksfit_core_update(page, control)

    page.title = "ROCKS FIT - RECEPÇÃO"
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COR_BG
    
    # --- SISTEMA DE UPLOAD DE FOTO ---
    def on_file_result(e):
        if e.files:
            file_path = e.files[0].path
            print(f"📸 Foto selecionada: {file_path}")
            profile_img.src = file_path
            profile_img.update()

    # file_picker = ft.FilePicker()
    # page.overlay.append(file_picker)
    # file_picker.on_result = on_file_result
    file_picker = None # Fallback para evitar NameError

    profile_img_src = "media/imagens/rkslogo.png" if os.path.exists("media/imagens/rkslogo.png") else None

    profile_placeholder = ft.Container(
        content=ft.Icon(ft.Icons.PERSON_OUTLINE, color=COR_PRIMARY, size=70),
        bgcolor="#1a1a1a",
        width=140, height=140,
        border_radius=70,
        alignment=ft.Alignment(0, 0),
        border=ft.Border.all(2, COR_PRIMARY + "40"),
        shadow=ft.BoxShadow(blur_radius=15, color="#00000030")
    )

    profile_img = ft.Image(
        src=profile_img_src if profile_img_src else TRANSPARENT_PIXEL,
        width=140, height=140,
        fit="cover",
        border_radius=70,
    )


    lbl_side_nome = ft.Text("RECEPÇÃO ATIVA", size=16, weight="bold", color=COR_TEXTO, text_align="center")
    lbl_side_vencimento = ft.Text("Aguardando identificação...", size=12, color=COR_TEXT_SEC, text_align="center")

    photo_field = ft.Container(
        content=ft.Stack([
            profile_placeholder,
            profile_img,
            ft.Container(
                content=ft.Icon(ft.Icons.CAMERA, size=20, color="white"),
                bgcolor=COR_PRIMARY,
                width=36, height=36,
                border_radius=18,
                right=5, bottom=5,
                border=ft.Border.all(3, "#000000"),
                alignment=ft.Alignment(0, 0)
            )
        ]),
        width=140, height=140,
        # on_click=lambda _: file_picker.pick_files(),
        on_click=lambda _: print("Upload temporariamente desativado"),
        tooltip="Fazer upload de foto"
    )

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
    
    # Sistema de notificação entre abas e threads (Versão Ultra-Segura)
    def on_broadcast(msg):
        try:
            if not page: return
            if isinstance(msg, dict):
                m_type = msg.get("type")
                if m_type == "identificacao":
                    print(f"✅ [ON_BROADCAST] Recebido identificacao para: {msg.get('data', {}).get('nome')}")
                    _dashboard_feedback(msg.get("data"), msg.get("liberado"), msg.get("metodo"), msg.get("sentido"))

                elif m_type == "open_enroll":
                    aluno = msg.get("aluno")
                    abrir_cadastro_digital(aluno, page, biometria_manager_global, render_main_content, state)
                elif m_type == "hw_status":
                    hw = msg.get("hw")
                    online = msg.get("online")
                    if hw == "fprint":
                        dot_status_fprint.bgcolor = COR_SUCCESS if online else COR_ERROR
                        lbl_status_fprint.value = "Biometria: ONLINE" if online else "Biometria: ERRO"
                    elif hw == "catraca":
                        dot_status_catraca.bgcolor = COR_SUCCESS if online else COR_ERROR
                        lbl_status_catraca.value = "Catraca: ONLINE" if online else "Catraca: OFFLINE"
                    try: right_panel.update()
                    except: pass
                elif m_type == "aguardando":
                    pass
        except Exception as e:
            print(f"⚠️ Erro no processamento de broadcast: {e}")

    page.pubsub.subscribe(on_broadcast)

    # ==========================
    # COMPONENTES DA SIDEBAR ESQUERDA
    # ==========================

    # Logo/Perfil (Apenas a foto agora)
    logo = ft.Column(
        [
            photo_field,
            ft.Container(height=10),
            lbl_side_nome,
            lbl_side_vencimento
        ],
        alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0
    )

    def create_menu_item(text, icon, active=False, on_click=None):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=COR_PRIMARY if active else COR_TEXT_SEC, size=20),
                    ft.Text(text, color=COR_TEXTO if active else COR_TEXT_SEC, size=14, weight="normal"),
                ],
                spacing=12, alignment=ft.MainAxisAlignment.START
            ),
            padding=ft.Padding(16, 12, 16, 12),
            border_radius=12,
            bgcolor="#1a1a1a" if active else "transparent",
            on_click=on_click,
        )

    def create_section_title(text):
        return ft.Text(text, color=COR_TEXT_SEC, size=11, weight="bold", opacity=0.7)

    # Menu Monitoramento
    def switch_view(view_name):
        # Fecha camada de cadastro se estiver aberta (Resolve navegação)
        if state.get("close_enroll"):
            try: state["close_enroll"]()
            except: pass
            
        state["current_view"] = view_name
        render_main_content()
        safe_update(page)

    menu_monitoramento = ft.Column(
        [
            create_section_title("MONITORAMENTO"),
            create_menu_item("Clientes", ft.Icons.PEOPLE, active=state["current_view"] == "clientes", on_click=lambda _: switch_view("clientes")),
            create_menu_item("Monitor Câmera", ft.Icons.VIDEOCAM, on_click=lambda _: subprocess.Popen([sys.executable, os.path.abspath(os.path.join(os.path.dirname(__file__), "monitor_aluno.py"))], start_new_session=True)),
        ],
        spacing=4
    )

    # Menu Acesso
    def liberar_manual(sentido):
        def _task():
            success = trigger_catraca(sentido)
            if success:
                page.snack_bar = ft.SnackBar(ft.Text(f"Catraca liberada ({sentido}) com sucesso!"), bgcolor=COR_SUCCESS)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Erro: Não foi possível conectar à catraca."), bgcolor=COR_ERROR)
            page.snack_bar.open = True
            safe_update(page)
        
        threading.Thread(target=_task, daemon=True).start()

    def liberar_aluno(aluno, sentido="ENTRADA"):
        def _task():
            nome = aluno.get("nome", "Liberacao").split()[0]
            success = trigger_catraca(sentido)
            if success:
                page.snack_bar = ft.SnackBar(ft.Text(f"{nome} liberado com sucesso!"), bgcolor=COR_SUCCESS)
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao liberar {nome}."), bgcolor=COR_ERROR)
            page.snack_bar.open = True
            safe_update(page)
        
        threading.Thread(target=_task, daemon=True).start()

    btn_entrada = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LOCK_OPEN, color=COR_PRIMARY, size=18),
                ft.Text("Liberar entrada", color=COR_TEXTO, size=14, weight="bold"),
            ],
            spacing=10, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_PRIMARY,
        height=48,
        border_radius=12,
        padding=ft.Padding(20, 0, 20, 0),
        ink=True,
        on_click=lambda _: liberar_manual("ENTRADA"),
    )

    btn_saida = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LOCK, color=COR_ERROR, size=18),
                ft.Text("Liberar saída", color=COR_ERROR, size=14, weight="bold"),
            ],
            spacing=10, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_CARD,
        height=48,
        border_radius=12,
        padding=ft.Padding(20, 0, 20, 0),
        border=ft.Border.all(1, COR_ERROR + "40"),
        ink=True,
        on_click=lambda _: liberar_manual("SAIDA"),
    )

    menu_acesso = ft.Column(
        [
            create_section_title("ACESSO"),
            btn_entrada,
            btn_saida,
        ],
        spacing=8
    )

    def sync_crm(e=None):
        if not SYNC_LOCK.acquire(blocking=False):
            return

        def _full_sync_task():
            try:
                # Feedback UI
                btn_sync_top.disabled = True
                btn_sync_top.text = "Sincronizando..."
                btn_sync_top.icon = ft.Icons.HOURGLASS_EMPTY
                page.update()

                print("📡 [SYNC] Iniciando Sincronização Industrial Completa...")
                
                # 1. CRM -> Django
                subprocess.run([sys.executable, "../sync_crm_to_db.py"], check=True)
                
                # 2. Django -> Embeddings
                subprocess.run([sys.executable, "../rebuild_face_index.py"], check=True)
                
                # 3. Django -> Reception Module
                subprocess.run([sys.executable, "../export_to_reception.py"], check=True)
                
                print("✅ [SYNC] Sincronização Industrial concluída com sucesso.")
                
                # Recarrega o cache local na memória da ponte
                carregar_cache_local()
                
                # Notifica a UI
                page.snack_bar = ft.SnackBar(ft.Text("Sincronização concluída com sucesso!"), bgcolor=COR_SUCCESS)
                page.snack_bar.open = True
                render_alunos() # Atualiza a lista na tela
                page.update()
            except Exception as ex:
                print(f"❌ [SYNC] Erro na sincronização: {ex}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro no sincronismo: {ex}"), bgcolor=COR_ERROR)
                page.snack_bar.open = True
                page.update()
            finally:
                btn_sync_top.disabled = False
                btn_sync_top.text = "Sincronizar CRM"
                btn_sync_top.icon = ft.Icons.SYNC
                try: SYNC_LOCK.release()
                except: pass
                page.update()

        threading.Thread(target=_full_sync_task, daemon=True).start()


    sidebar = ft.Container(
        width=260,
        bgcolor="#0a0a0a",
        padding=ft.Padding(20, 20, 20, 20),
        border=ft.Border(right=ft.BorderSide(1, "#222222")),
        content=ft.Column(
            [
                ft.Container(content=logo, alignment=ft.Alignment(0, 0)),
                ft.Divider(height=20, color="transparent"),
                create_section_title("MONITORAMENTO"),
                create_menu_item("Clientes", ft.Icons.PEOPLE, active=state["current_view"] == "clientes", on_click=lambda _: switch_view("clientes")),
            create_menu_item("Monitor Câmera", ft.Icons.VIDEOCAM, on_click=lambda _: subprocess.Popen([sys.executable, os.path.abspath(os.path.join(os.path.dirname(__file__), "monitor_aluno.py"))], start_new_session=True)),
                
                ft.Divider(height=10, color="transparent"),
                create_section_title("ACESSO"),
                btn_entrada,
                btn_saida,
                
                ft.Divider(height=10, color="transparent"),
                create_section_title("SISTEMA"),
                create_menu_item("Histórico", ft.Icons.HISTORY, on_click=lambda _: abrir_historico()),
                create_menu_item("Diagnóstico", ft.Icons.TROUBLESHOOT, on_click=lambda _: abrir_diagnostico()),
                
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=COR_SUCCESS),
                        ft.Text("SISTEMA ONLINE", color=COR_TEXT_SEC, size=11),
                    ], spacing=8),
                    padding=10, bgcolor="#161616", border_radius=8
                ),
            ],
            spacing=4,
            
        ),
    )

    # ==========================
    # COMPONENTES DO CENTRO
    # ==========================

    # Barra superior
    status_online = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CLOUD_DONE, color=COR_SUCCESS, size=16),
                ft.Text("Online: ", color=COR_TEXT_SEC, size=13),
                ft.Text("CRM", color=COR_SUCCESS, size=13, weight="bold"),
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COR_SUCCESS, size=14),
            ],
            spacing=4
        ),
        padding=ft.Padding(16, 8, 16, 8),
        border_radius=20,
        bgcolor=COR_CARD,
    )

    status_camera = ft.Container(
        content=ft.Row(
            [
                ft.Text("Câmera: ", color=COR_TEXT_SEC, size=13),
                ft.Text("OFF" if not CONFIG["camera_enabled"] else "ON", color=COR_ERROR if not CONFIG["camera_enabled"] else COR_SUCCESS, size=13, weight="bold"),
            ],
            spacing=4
        ),
        padding=ft.Padding(16, 8, 16, 8),
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
        content_padding=ft.Padding(15, 10, 15, 10),
        text_size=14,
        expand=True,
        on_change=lambda e: render_alunos(),
    )

    btn_sync_icon = ft.Icon(ft.Icons.SYNC, color="#000000", size=18)
    btn_sync_text = ft.Text("Sincronizar CRM", color="#000000", size=14, weight="bold")
    btn_sync_top = ft.Container(
        content=ft.Row(
            [
                btn_sync_icon,
                btn_sync_text,
            ],
            spacing=8, alignment=ft.MainAxisAlignment.CENTER
        ),
        bgcolor=COR_PRIMARY,
        height=40,
        border_radius=10,
        padding=ft.Padding(left=15, top=0, right=15, bottom=0),
        ink=True,
        on_click=lambda _: sync_crm()
    )

    top_bar = ft.Row(
        [
            search_field,
            btn_sync_top,
            status_online,
            status_camera,
        ],
        spacing=12, alignment=ft.MainAxisAlignment.START
    )

    # Cards de estatísticas (Dinâmicos)
    lbl_ativos_val = ft.Text("0", color=COR_SUCCESS, size=36, weight="bold", font_family="Space Grotesk")
    lbl_vencendo_val = ft.Text("0", color=COR_WARNING, size=36, weight="bold", font_family="Space Grotesk")
    lbl_vencidos_val = ft.Text("0", color=COR_ERROR, size=36, weight="bold", font_family="Space Grotesk")

    def create_stat_card(title, value_control, color):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, color=COR_TEXT_SEC, size=13, weight="normal"),
                    value_control,
                ],
                spacing=4, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=140, height=100,
            bgcolor=COR_CARD,
            border_radius=16,
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(16, 16, 16, 16),
        )

    stats_row = ft.Row(
        [
            create_stat_card("Ativos", lbl_ativos_val, COR_SUCCESS),
            create_stat_card("Vencendo", lbl_vencendo_val, COR_WARNING),
            create_stat_card("Vencidos", lbl_vencidos_val, COR_ERROR),
        ],
        spacing=12, alignment=ft.MainAxisAlignment.START
    )

    # Lista de alunos
    lista_alunos_col = ft.ListView(expand=True, spacing=8, padding=ft.Padding(0, 10, 0, 0))

    def get_status_color(status):
        status = str(status).lower()
        if status in ["ativo", "liberado", "pago", "ok"]: return COR_SUCCESS
        elif status in ["alerta", "vencendo", "atencao"]: return COR_WARNING
        else: return COR_ERROR

    def get_status_badge(status, dias, vencimento=""):
        status = str(status).lower()
        venc_str = f" | {vencimento}" if vencimento else ""
        if status == "vencido" or dias <= 0:
            return ft.Container(content=ft.Text(f"Crédito: {dias}d{venc_str}", color=COR_SUCCESS, size=11, weight="bold"), bgcolor=COR_SUCCESS + "15", padding=ft.Padding(10, 6, 10, 6), border_radius=8)
        elif status == "alerta" or 0 < dias <= 15:
            return ft.Container(content=ft.Text(f"Crédito: {dias}d{venc_str}", color=COR_WARNING, size=11, weight="bold"), bgcolor=COR_WARNING + "15", padding=ft.Padding(left=10, right=10, top=6, bottom=6), border_radius=8)
        else:
            return ft.Container(content=ft.Text(f"Crédito: {dias}d{venc_str}", color=COR_SUCCESS, size=11, weight="bold"), bgcolor=COR_SUCCESS + "15", padding=ft.Padding(left=10, right=10, top=6, bottom=6), border_radius=8)

    def render_alunos():
        lista_alunos_col.controls.clear()
        c_ativos, c_vencendo, c_vencidos = 0, 0, 0
        if state["alunos_data"]:
            for a in state["alunos_data"]:
                s_raw = str(a.get("status", "ativo")).upper()
                d = int(a.get("dias_restantes") or 0)
                if s_raw in ["ATIVO", "LIBERADO", "PAGO", "OK"]:
                    if d > 15: c_ativos += 1
                    elif 0 < d <= 15: c_vencendo += 1
                    else: c_vencidos += 1
                elif s_raw in ["ALERTA", "VENCENDO", "ATENÇÃO", "AVISO"]: c_vencendo += 1
                else: c_vencidos += 1
        
        lbl_ativos_val.value = str(c_ativos)
        lbl_vencendo_val.value = str(c_vencendo)
        lbl_vencidos_val.value = str(c_vencidos)
        
        if not state["alunos_data"]:
            lista_alunos_col.controls.append(ft.Container(content=ft.Text("Nenhum aluno sincronizado.", color=COR_TEXT_SEC), padding=50, alignment=ft.Alignment(0, 0)))
            safe_update(page); return

        filter_text = search_field.value.lower() if search_field.value else ""
        matriculas_com_digital = set()
        if BIOMETRIA_MAPPING_CACHE:
            for mats in BIOMETRIA_MAPPING_CACHE.values():
                for m in mats: matriculas_com_digital.add(str(m))

        rendered_count = 0
        for aluno in state["alunos_data"]:
            nome = str(aluno.get("nome", "ALUNO"))
            mat = str(aluno.get("matricula", "N/D"))
            status = str(aluno.get("status", "ativo"))
            dias = int(aluno.get("dias_restantes") or 0)
            if filter_text and filter_text not in nome.lower() and filter_text not in mat: continue

            rendered_count += 1
            if rendered_count > 30:
                lista_alunos_col.controls.append(
                    ft.Container(
                        content=ft.Text("Use a barra de pesquisa para filtrar outros alunos...", color=COR_TEXT_SEC, size=12, italic=True),
                        padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                        alignment=ft.Alignment(0, 0)
                    )
                )
                break

            cor_status = get_status_color(status)
            furl = aluno.get("foto_url", "")
            img_avatar = ft.Image(src=furl if furl.startswith("http") else f"{SITE_URL}{furl}", width=50, height=50, border_radius=25, fit="cover") if furl else None
            
            avatar = ft.Container(
                content=ft.Text("".join([p[0] for p in nome.split()[:2]]).upper(), color=cor_status, size=16, weight="bold") if not img_avatar else img_avatar,
                width=50, height=50, border_radius=25, bgcolor=COR_CARD_HIGH, border=ft.Border.all(2, cor_status), alignment=ft.Alignment(0, 0), clip_behavior=ft.ClipBehavior.HARD_EDGE
            )

            info = ft.Column([ft.Text(nome[:20], color=COR_TEXTO, size=14, weight="bold"), ft.Text(f"Mat. {mat}", color=COR_TEXT_SEC, size=12)], spacing=2)
            badge = get_status_badge(status, dias, str(aluno.get("vencimento", "")))
            
            has_digital = mat in matriculas_com_digital
            btn_digital = ft.Container(content=ft.Icon(ft.Icons.FINGERPRINT, size=24, color=COR_PRIMARY), on_click=lambda e, a=aluno: abrir_cadastro_digital(a, page, biometria_manager_global, render_main_content, state), padding=10, border_radius=10, ink=True)
            btn_liberar = ft.Container(content=ft.Icon(ft.Icons.LOCK_OPEN, size=24, color=COR_SUCCESS), on_click=lambda e, a=aluno: liberar_aluno(a, "ENTRADA"), padding=10, border_radius=10, ink=True)

            lista_alunos_col.controls.append(ft.Container(
                content=ft.Row([ft.Row([avatar, info], spacing=12), ft.Row([badge, btn_liberar, btn_digital], spacing=4)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=COR_CARD, border_radius=16, padding=16, on_click=lambda e, a=aluno: abrir_cadastro_digital(a, page, biometria_manager_global, render_main_content, state), ink=True
            ))
        safe_update(page)

    # --- HISTÓRICO ---
    # Componentes de Histórico Reforçados (Industrial Premium - FULL WIDTH)
    historico_items = ft.Column(spacing=0, expand=True, scroll="auto")
    
    # Cabeçalho da Tabela (Fixed)
    historico_header = ft.Container(
        content=ft.Row([
            ft.Text("ALUNO", weight="bold", size=13, width=280),
            ft.Text("DATA E HORA", weight="bold", size=13, width=220),
            ft.Text("SENTIDO", weight="bold", size=13, width=120, text_align="center"),
            ft.Text("MÉTODO", weight="bold", size=13, expand=True, text_align="right"),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#f271211a",
        padding=ft.Padding(20, 12, 20, 12),
        border_radius=10
    )

    # Inputs de Filtro (Industrial)
    search_hist = ft.TextField(
        label="Pesquisar por Nome ou Matrícula", 
        text_size=13, 
        border_radius=12,
        border_color="#ffffff20", 
        expand=True, 
        prefix_icon="search",
        on_submit=lambda _: render_historico()
    )
    
    date_hist = ft.TextField(
        label="Data (DD/MM/AAAA)", 
        value=datetime.now().strftime("%d/%m/%Y"), 
        text_size=13, 
        width=180, 
        border_radius=12,
        border_color="#ffffff20",
        prefix_icon="calendar_month"
    )

    def render_historico():
        historico_items.controls.clear()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            query = """
                SELECT l.matricula, a.nome, l.timestamp, l.sentido, l.metodo 
                FROM logs_acesso l
                LEFT JOIN alunos a ON l.matricula = a.matricula
                WHERE 1=1
            """
            params = []
            
            if date_hist.value:
                try:
                    data_iso = datetime.strptime(date_hist.value, "%d/%m/%Y").strftime("%Y-%m-%d")
                    query += " AND l.timestamp LIKE ?"
                    params.append(f"{data_iso}%")
                except: pass
            
            if search_hist.value:
                query += " AND (l.matricula LIKE ? OR a.nome LIKE ?)"
                params.extend([f"%{search_hist.value}%", f"%{search_hist.value}%"])
            
            query += " ORDER BY l.timestamp DESC LIMIT 100"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            for r in rows:
                nome_display = r[1] if r[1] else f"Matrícula {r[0]}"
                try:
                    dt_obj = datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S")
                    dt_display = dt_obj.strftime("%d/%m/%Y %H:%M")
                except: dt_display = r[2]

                historico_items.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(nome_display.upper()[:30], weight="bold", size=13, width=280, color="#f0f0f0"),
                            ft.Text(dt_display, size=12, width=220, color=COR_TEXT_SEC),
                            ft.Container(
                                content=ft.Text(r[3], size=10, weight="bold", color="white"),
                                bgcolor=COR_SUCCESS if "ENTRADA" in r[3] else COR_ERROR,
                                padding=ft.Padding(10, 4, 10, 4),
                                border_radius=6,
                                width=120,
                                alignment=ft.Alignment(0, 0),
                            ),
                            ft.Text(r[4], size=11, expand=True, text_align="right", color=COR_TEXT_SEC, italic=True)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.Padding(20, 12, 20, 12),
                        border=ft.Border(bottom=ft.BorderSide(1, "#ffffff08"))
                    )
                )
            conn.close()
        except Exception as e:
            print(f"❌ [DB] Erro ao renderizar histórico: {e}")
        
        safe_update(page)

    def render_main_content():
        # No modo Stack, apenas garantimos que o dashboard está visível se não estivermos cadastrando
        if not ENROLLMENT_ACTIVE:
            render_alunos()
            rocksfit_core_update(page)

    def abrir_historico(e=None):
        try:
            if state.get("close_enroll"):
                try: state["close_enroll"]()
                except: pass
            
            print("📜 [UI] Preparando Histórico...")
            render_historico()
            
            overlay_hist = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.HISTORY, color=COR_PRIMARY, size=30),
                                ft.Column([
                                    ft.Text("AUDITORIA DE ACESSOS", size=22, weight="bold"),
                                    ft.Text("LOGS EM TEMPO REAL • FORMATO INDUSTRIAL", size=11, color=COR_TEXT_SEC),
                                ], spacing=0)
                            ], spacing=15),
                            ft.Container(content=ft.Icon(ft.Icons.CLOSE, color="#555555", size=20), on_click=lambda _: close_hist(), padding=5, border_radius=5, ink=True)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=30, color="#ffffff10"),
                        ft.Row([
                            search_hist,
                            date_hist,
                            ft.Container(
                                content=ft.Container(content=ft.Icon(ft.Icons.REFRESH, color="white", size=20), on_click=lambda _: render_historico(), padding=8, border_radius=12, ink=True),
                                bgcolor=COR_PRIMARY,
                                border_radius=12
                            )
                        ], spacing=15),
                        ft.Divider(height=20, color="transparent"),
                        ft.Container(
                            content=ft.Column([historico_header, historico_items], scroll="auto", expand=True),
                            expand=True,
                            border_radius=15,
                            bgcolor="#00000030",
                            padding=10
                        )
                    ]), 
                    bgcolor="#0d0d0d", 
                    padding=35, 
                    border_radius=30, 
                    width=950, 
                    height=700, 
                    border=ft.Border.all(1, "#ffffff10")
                ), 
                alignment=ft.Alignment(0, 0), 
                bgcolor="#000000ee", 
                expand=True
            )
            def close_hist():
                if overlay_hist in page.overlay:
                    page.overlay.remove(overlay_hist)
                page.update()

            page.overlay.append(overlay_hist)
            page.update()
            print("✅ [UI] Histórico aberto.")
        except Exception as ex:
            print(f"❌ [UI] Erro ao abrir histórico: {ex}")

    # Lista de alunos
    lista_alunos_col = ft.ListView(expand=True, spacing=8, padding=ft.Padding(0, 10, 0, 0))

    # Painel Direito: Monitor de Acesso em Tempo Real (Industrial)
    last_access_img = ft.Image(src=TRANSPARENT_PIXEL, width=120, height=120, border_radius=60, fit="cover", visible=False)
    last_access_placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.PERSON_OUTLINE, color=COR_PRIMARY, size=50),
            ft.Text("AGUARDANDO...", size=10, color=COR_TEXT_SEC, weight="bold"),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#1a1a1a", width=120, height=120, border_radius=60, 
        alignment=ft.Alignment(0, 0), 
        border=ft.Border.all(2, COR_PRIMARY + "40"),
        shadow=ft.BoxShadow(blur_radius=20, color="#00000050")
    )
    last_access_nome = ft.Text("AGUARDANDO...", weight="bold", size=18, text_align="center")
    last_access_matricula = ft.Text("", size=13, color=COR_TEXT_SEC)
    last_access_vencimento = ft.Text("", size=14, weight="bold", color=COR_PRIMARY)
    last_access_status_txt = ft.Text("STANDBY", size=12, weight="bold", color="white")
    
    last_access_status_box = ft.Container(
        content=last_access_status_txt, 
        padding=ft.Padding(20, 8, 20, 8), 
        border_radius=10, 
        bgcolor="#222222",
        animate=ft.Animation(300, "decelerate")
    )

    dot_status_fprint = ft.Container(width=8, height=8, border_radius=4, bgcolor=COR_SUCCESS)
    lbl_status_fprint = ft.Text("Biometria: ONLINE", size=11, color="#666666")
    dot_status_catraca = ft.Container(width=8, height=8, border_radius=4, bgcolor=COR_SUCCESS)
    lbl_status_catraca = ft.Text("Catraca: ONLINE", size=11, color="#666666")

    right_panel = ft.Container(
        width=300,
        bgcolor="#0f0f0f",
        padding=ft.Padding(20, 20, 20, 20),
        border=ft.Border(top=ft.BorderSide(1, "#ffffff08")), 
        content=ft.Column(
            [
                ft.Text("ÚLTIMO ACESSO", size=11, weight="bold", color=COR_TEXT_SEC, opacity=0.7),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Stack([last_access_placeholder, last_access_img]),
                        ft.Container(height=10),
                        last_access_nome,
                        last_access_matricula,
                        ft.Container(height=5),
                        ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY, size=16, color=COR_TEXT_SEC), last_access_vencimento], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    padding=ft.Padding(20, 20, 20, 20),
                    bgcolor="#161616",
                    border_radius=20,
                    # blur=ft.Blur(10, 10),
                    border=ft.Border.all(1, "#ffffff05"),
                ),
                ft.Container(height=15),
                last_access_status_box,
                ft.Divider(height=40, color="#ffffff10"),
                ft.Text("CONECTIVIDADE", size=11, color="#444444", weight="bold"),
                ft.Container(
                    content=ft.Column([
                        ft.Row([dot_status_fprint, lbl_status_fprint], spacing=8),
                        ft.Row([dot_status_catraca, lbl_status_catraca], spacing=8),
                    ], spacing=8),
                    padding=15,
                    bgcolor="#111111",
                    border_radius=12,
                    border=ft.Border.all(1, "#ffffff05"),
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=260, # Largura útil (300 - padding)
            scroll="auto",
        ),
        animate_offset=ft.Animation(500, "decelerate"),
        offset=ft.Offset(0, 0)
    )

    center_content = ft.Row(
        [
            # Coluna da Esquerda: Gestão e Lista
            ft.Column([
                top_bar,
                ft.Divider(height=20, color="transparent"),
                stats_row,
                ft.Divider(height=20, color="transparent"),
                lista_alunos_col,
            ], expand=True, spacing=0),
            
            # Coluna da Direita: Monitoramento
            right_panel
        ],
        expand=True, spacing=0
    )

    # CAMADA DE CADASTRO (PERSISTENTE PARA EVITAR CRASHES DE REMOÇÃO)
    enroll_layer = ft.Container(visible=False, expand=True)
    state["enroll_layer"] = enroll_layer

    global CENTER_PANEL_GLOBAL
    CENTER_PANEL_GLOBAL = ft.Container(
        expand=True,
        bgcolor=COR_BG,
        padding=ft.Padding(left=30, right=30, top=30, bottom=30),
        content=ft.Stack([
            center_content,
            enroll_layer
        ], expand=True)
    )
    center_panel = CENTER_PANEL_GLOBAL
    
    # Adiciona componentes invisíveis ao overlay por último
    # page.overlay.append(file_picker) # Removido para evitar erro no Windows
    
    render_main_content()

    def abrir_diagnostico(e=None):
        try:
            if state.get("close_enroll"):
                try: state["close_enroll"]()
                except: pass
            
            print("🔍 [UI] Preparando Diagnóstico...")
            
            def check_crm():
                try: return requests.get(f"{SITE_URL}/api/catraca-sync/?token={SYNC_TOKEN}", timeout=2).status_code == 200
                except: return False
            
            def check_catraca():
                import socket
                try:
                    ip = CONFIG.get("catraca_ip", "169.254.37.150")
                    porta = int(CONFIG.get("catraca_porta", 1001))
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.5)
                        s.connect((ip, porta))
                        return True
                except: return False

            def check_biometria():
                try:
                    user = os.getenv("USER") or os.getenv("LOGNAME") or "root"
                    res = subprocess.run(["fprintd-list", user], capture_output=True, text=True, timeout=2)
                    return "found" in res.stdout.lower() or "device" in res.stdout.lower()
                except: return False

            def diag_card(title, value, detail, icon):
                is_ok = value if isinstance(value, bool) else (True if "detectado" in str(value).lower() or "ativo" in str(value).lower() else False)
                color = COR_SUCCESS if is_ok else COR_ERROR
                return ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, color=COR_PRIMARY, size=24),
                        ft.Column([
                            ft.Text(title, size=13, weight="bold", color=COR_TEXT_SEC),
                            ft.Text(detail, size=11, color=COR_TEXT_SEC),
                        ], spacing=2, expand=True),
                        ft.Icon(ft.Icons.CHECK_CIRCLE if is_ok else ft.Icons.ERROR, color=color, size=32),
                    ], spacing=15),
                    padding=15, bgcolor="#000000", border_radius=12,
                    border=ft.Border.all(1, color + "40")
                )

            # Cards de carregamento inicial
            card_crm = ft.Container(content=ft.Row([ft.ProgressRing(width=20, height=20, color=COR_PRIMARY), ft.Text("Verificando CRM...", size=13, color=COR_TEXT_SEC)], spacing=15), padding=15, bgcolor="#000000", border_radius=12)
            card_cat = ft.Container(content=ft.Row([ft.ProgressRing(width=20, height=20, color=COR_PRIMARY), ft.Text("Verificando Catraca...", size=13, color=COR_TEXT_SEC)], spacing=15), padding=15, bgcolor="#000000", border_radius=12)
            card_bio = ft.Container(content=ft.Row([ft.ProgressRing(width=20, height=20, color=COR_PRIMARY), ft.Text("Verificando Biometria...", size=13, color=COR_TEXT_SEC)], spacing=15), padding=15, bgcolor="#000000", border_radius=12)
            
            overlay_diag = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Row([ft.Icon(ft.Icons.ANALYTICS, color=COR_PRIMARY), ft.Text("DIAGNÓSTICO ROCKS-FIT", size=20, weight="bold")], spacing=10),
                            ft.Container(content=ft.Icon(ft.Icons.CLOSE, size=20), on_click=lambda _: close_diag(), padding=5, border_radius=5, ink=True)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=1, color="#ffffff10"),
                        ft.Column([
                            card_crm,
                            card_cat,
                            card_bio,
                            diag_card("CÂMERA BIOMÉTRICA", True, "Dispositivo USB Ativo", ft.Icons.VIDEOCAM),
                            diag_card("MOTOR NEURAL", True, "DeepFace: " + ("API REMOTA" if DEEPFACE_ONLINE else "LOCAL (ATIVO)"), ft.Icons.MEMORY),
                        ], spacing=10, scroll="auto", height=400),
                        ft.Row([
                            ft.ElevatedButton("LIMPAR HARDWARE", on_click=lambda _: nuclear_cleanup(), expand=True, style=ft.ButtonStyle(bgcolor=COR_PRIMARY, color="white")),
                            ft.ElevatedButton("TESTAR ENTRADA", on_click=lambda _: trigger_catraca("ENTRADA"), expand=True, bgcolor=COR_SUCCESS, color="white"),
                            ft.ElevatedButton("TESTAR SAÍDA", on_click=lambda _: trigger_catraca("SAIDA"), expand=True, bgcolor=COR_ERROR, color="white"),
                        ], spacing=10)
                    ], spacing=20, tight=True),
                    bgcolor="black", padding=ft.Padding(25, 25, 25, 25), border_radius=20, width=500,
                    border=ft.Border.all(1, "#ffffff20")
                ),
                alignment=ft.Alignment(0, 0), bgcolor="#000000dd", expand=True, visible=True
            )
            def run_async_checks():
                try:
                    s_crm = check_crm()
                    s_cat = check_catraca()
                    s_bio = check_biometria()
                    
                    res_crm = diag_card("SERVIDOR CRM", s_crm, "IP: academiarocksfit.com.br", ft.Icons.CLOUD_DONE)
                    card_crm.content = res_crm.content
                    card_crm.border = res_crm.border
                    
                    res_cat = diag_card("CATRACA (RELÉ)", s_cat, f"IP: {CONFIG.get('catraca_ip')}", ft.Icons.DASHBOARD)
                    card_cat.content = res_cat.content
                    card_cat.border = res_cat.border
                    
                    res_bio = diag_card("LEITOR DIGITAL", s_bio, "Scanner fprintd Ativo", ft.Icons.FINGERPRINT)
                    card_bio.content = res_bio.content
                    card_bio.border = res_bio.border
                    
                    page.update()
                except: pass

            def close_diag():
                if overlay_diag in page.overlay:
                    page.overlay.remove(overlay_diag)
                page.update()

            page.overlay.append(overlay_diag)
            page.update()
            
            # Dispara os testes em segundo plano
            threading.Thread(target=run_async_checks, daemon=True).start()
            print("✅ [UI] Diagnóstico aberto.")
        except Exception as ex:
            print(f"❌ [UI] Erro crítico ao abrir diagnóstico: {ex}")

    def abrir_configuracoes(e=None):
        try:
            global PAUSE_BIOMETRIA
            print("⚙️ [UI] Preparando Configurações...")
            if state.get("close_enroll"):
                try: state["close_enroll"]()
                except: pass

            def update_config(key, value):
                CONFIG[key] = value
                save_settings(CONFIG)
                update_global_from_config()
                # Sincronização automática com a ponte
                if key in ["catraca_ip", "catraca_porta"]:
                    sync_ponte_catraca(key, value)
                print(f"⚙️ [CONFIG] {key} alterado para {value}")
                page.update()

            # Labels Dinâmicos
            lbl_face_thr = ft.Text(f"Sensibilidade (Threshold): {CONFIG['face_threshold']}", size=12, weight="bold")
            lbl_face_streak = ft.Text(f"Ciclos de Confirmação (Streak): {CONFIG['face_streak']}", size=12, weight="bold")
            lbl_face_skip = ft.Text(f"Frequência de Análise (Frames): {CONFIG['face_frame_skip']}", size=12, weight="bold")
            lbl_fprint_timeout = ft.Text(f"Tempo Limite (Timeout): {max(1, CONFIG.get('fprint_timeout', 30))}s", size=12, weight="bold")
            lbl_cooldown_facial = ft.Text(f"Carência de Reconhecimento: {max(1, CONFIG.get('cooldown_facial', 30))}s", size=12, weight="bold")

            lbl_face_model = ft.Text(f"Modelo de Deteção: {CONFIG.get('face_model', 'hog').upper()}", size=12, weight="bold")
            lbl_face_scale = ft.Text(f"Escala de Análise: {int(CONFIG.get('face_scale', 0.5)*100)}%", size=12, weight="bold")

            tab_facial = ft.Column([
                ft.Text("REGULAGEM DE FIDELIDADE FACIAL", size=14, weight="bold", color=COR_PRIMARY),
                ft.Text("Ajuste a sensibilidade do algoritmo neural para seu ambiente.", size=11, color=COR_TEXT_SEC),
                ft.Divider(height=10, color="transparent"),

                lbl_face_thr,
                (slider_face_thr := ft.Slider(
                    min=0.30, max=0.70, divisions=40,
                    value=CONFIG['face_threshold'],
                    on_change=lambda e: (
                        setattr(lbl_face_thr, "value", f"Sensibilidade (Threshold): {round(e.control.value, 2)}"),
                        update_config("face_threshold", round(e.control.value, 2))
                    )
                )),
                ft.Text("◄ Menor = Mais Rígido (menos falsos) | Maior = Mais Permissivo ►", size=10, italic=True, color=COR_TEXT_SEC),

                ft.Divider(height=20),
                lbl_face_streak,
                (slider_face_streak := ft.Slider(
                    min=1, max=10, divisions=9,
                    value=CONFIG['face_streak'],
                    on_change=lambda e: (
                        setattr(lbl_face_streak, "value", f"Ciclos de Confirmação (Streak): {int(e.control.value)}"),
                        update_config("face_streak", int(e.control.value))
                    )
                )),
                ft.Text("Quantas vezes seguidas a IA deve reconhecer para liberar.", size=10, italic=True, color=COR_TEXT_SEC),

                ft.Divider(height=20),
                lbl_face_skip,
                (slider_face_skip := ft.Slider(min=1, max=30, divisions=29, value=CONFIG.get('face_frame_skip', 3),
                          on_change=lambda e: (
                              setattr(lbl_face_skip, "value", f"Frequência de Análise (Frames): {int(e.control.value)}"),
                              update_config("face_frame_skip", int(e.control.value))
                          ))),
                ft.Text("Menor = Análise mais freqüente (mais CPU) | Maior = Mais econômico", size=10, italic=True, color=COR_TEXT_SEC),

                ft.Divider(height=20),
                lbl_face_model,
                ft.Dropdown(
                    label="Modelo de Detecção",
                    value=CONFIG.get("face_model", "hog"),
                    options=[
                        ft.dropdown.Option("hog", "HOG – Rápido (CPU, recomendado)"),
                        ft.dropdown.Option("cnn", "CNN – Preciso (GPU/CUDA, lento sem GPU)"),
                    ],
                    on_select=lambda e: (
                        setattr(lbl_face_model, "value", f"Modelo de Deteção: {e.control.value.upper()}"),
                        update_config("face_model", e.control.value)
                    ),
                    bgcolor="#111111",
                ),
                ft.Text("HOG recomendado para a maioria dos sistemas. CNN requer GPU CUDA.", size=10, italic=True, color=COR_TEXT_SEC),

                ft.Divider(height=20),
                lbl_face_scale,
                (slider_face_scale := ft.Slider(min=0.25, max=1.0, divisions=15, value=CONFIG.get('face_scale', 0.5),
                          on_change=lambda e: (
                              setattr(lbl_face_scale, "value", f"Escala de Análise: {int(e.control.value*100)}%"),
                              update_config("face_scale", round(e.control.value, 2))
                          ))),
                ft.Text("50% = Melhor equilíbrio velocidade/precisão | 100% = Máxima precisão", size=10, italic=True, color=COR_TEXT_SEC),

                ft.Divider(height=20),
                ft.Text("🔬 STATUS DO MOTOR NEURAL", size=12, weight="bold", color=COR_PRIMARY),
                ft.Row([
                    ft.Container(width=8, height=8, border_radius=4, bgcolor=COR_SUCCESS),
                    ft.Text(
                        f"DeepFace Engine: {'API Remota (Alta Perf.)' if DEEPFACE_ONLINE else 'Motor Local (Ativo)'}",
                        size=11, color=COR_TEXT_SEC
                    )
                ], spacing=8),

                ft.Divider(height=20),
                ft.Text("☀️ AUTORREGULAGEM DE LUMINOSIDADE", size=12, weight="bold", color=COR_PRIMARY),
                ft.Text(
                    "Analisa a luminosidade atual da câmera e ajusta o threshold automaticamente "
                    "para o ambiente de iluminação.",
                    size=10, italic=True, color=COR_TEXT_SEC
                ),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.AUTO_FIX_HIGH, color="white", size=18),
                        ft.Text("  CALIBRAR AGORA", color="white", weight="bold", size=13)
                    ], tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=COR_PRIMARY,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(left=20, right=20, top=12, bottom=12),
                    ),
                    on_click=lambda _: auto_calibrate_threshold(
                        page, lbl_face_thr, lbl_face_streak, lbl_face_skip, lbl_face_scale,
                        slider_face_thr, slider_face_streak, slider_face_skip, slider_face_scale,
                        update_config
                    ),
                ),

                ft.Divider(height=10),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SAVE, color="white", size=18),
                        ft.Text("  SALVAR PARÂMETROS FACIAIS", color="white", weight="bold", size=13)
                    ], tight=True),
                    style=ft.ButtonStyle(
                        bgcolor=COR_SUCCESS,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(20, 12, 20, 12),
                    ),
                    on_click=lambda _: (
                        save_settings(CONFIG),
                        setattr(page, "snack_bar", ft.SnackBar(ft.Text("✅ Parâmetros Faciais salvos e aplicados!"), bgcolor=COR_SUCCESS)),
                        setattr(page.snack_bar, "open", True),
                        page.update()
                    ),
                ),
            ], scroll="auto", spacing=10)

            # TAB 2: Catraca & Rede
            tab_catraca = ft.Column([
                ft.Text("COMUNICAÇÃO COM HARDWARE", size=14, weight="bold", color=COR_PRIMARY),
                ft.TextField(label="IP da Catraca", value=CONFIG['catraca_ip'], 
                             on_blur=lambda e: update_config("catraca_ip", e.control.value), bgcolor="#111111"),
                ft.TextField(label="Porta Socket", value=str(CONFIG['catraca_porta']), 
                             on_blur=lambda e: (
                                 update_config("catraca_porta", int(e.control.value)) if e.control.value.isdigit() else None
                             ), bgcolor="#111111"),
                ft.Divider(height=20),
                ft.Text("SENTIDOS DE ROTAÇÃO", size=14, weight="bold", color=COR_PRIMARY),
                ft.Dropdown(
                    label="Sentido Entrada",
                    value=str(CONFIG['catraca_sentido_entrada']),
                    options=[ft.dropdown.Option("0", "Horário (Comando 0)"), ft.dropdown.Option("1", "Anti-Horário (Comando 1)")],
                    on_select=lambda e: update_config("catraca_sentido_entrada", int(e.control.value))
                ),
                ft.Dropdown(
                    label="Sentido Saída",
                    value=str(CONFIG['catraca_sentido_saida']),
                    options=[ft.dropdown.Option("0", "Horário (Comando 0)"), ft.dropdown.Option("1", "Anti-Horário (Comando 1)")],
                    on_select=lambda e: update_config("catraca_sentido_saida", int(e.control.value))
                ),
                ft.Divider(height=20),
                ft.Text("REGRAS DE ACESSO", size=14, weight="bold", color=COR_PRIMARY),
                lbl_cooldown_facial,
                ft.Slider(min=1, max=120, divisions=119, value=max(1, CONFIG.get('cooldown_facial', 30)),
                          on_change=lambda e: (
                              setattr(lbl_cooldown_facial, "value", f"Carência de Reconhecimento: {int(e.control.value)}s"),
                              update_config("cooldown_facial", int(e.control.value))
                          )),
                ft.Text("Tempo mínimo entre uma identificação e outra para o mesmo aluno.", size=10, italic=True, color=COR_TEXT_SEC),
            ], scroll="auto", spacing=15)

            # TAB 3: Digital & Câmera
            tab_hardware = ft.Column([
                ft.Text("BIOMETRIA DIGITAL", size=14, weight="bold", color=COR_PRIMARY),
                lbl_fprint_timeout,
                ft.Slider(min=1, max=60, value=max(1, CONFIG.get('fprint_timeout', 30)), 
                          on_change=lambda e: (
                              setattr(lbl_fprint_timeout, "value", f"Tempo Limite (Timeout): {int(e.control.value)}s"),
                              update_config("fprint_timeout", int(e.control.value))
                          )),
                
                ft.Divider(height=20),
                ft.Text("CÂMERA DO SISTEMA", size=14, weight="bold", color=COR_PRIMARY),
                ft.Switch(label="Câmera Ativada", value=CONFIG['camera_enabled'], 
                          on_change=lambda e: update_config("camera_enabled", e.control.value)),
                ft.Text("Desative para usar apenas a digital e economizar recursos.", size=10, italic=True),
            ], scroll="auto", spacing=15)

            def close_config(e=None):
                dlg_config.visible = False
                page.update()

            dlg_config = ft.Container(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("CONFIGURAÇÕES TÉCNICAS", size=20, weight="bold", color="white"),
                            ft.Container(content=ft.Icon(ft.Icons.CLOSE, size=20), on_click=close_config, padding=5, border_radius=5, ink=True)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(height=10),
                        ft.Container(
                            width=600, height=550,
                            content=ft.Tabs(
                                selected_index=0,
                                animation_duration=300,
                                length=3,
                                expand=True,
                                content=ft.Column(
                                    expand=True,
                                    controls=[
                                        ft.TabBar(
                                            tabs=[
                                                ft.Tab(label="FACIAL"),
                                                ft.Tab(label="CATRACA"),
                                                ft.Tab(label="HARDWARE"),
                                            ]
                                        ),
                                        ft.TabBarView(
                                            expand=True,
                                            controls=[
                                                tab_facial,
                                                tab_catraca,
                                                tab_hardware,
                                            ]
                                        )
                                    ]
                                )
                            )
                        )
                    ]),
                    bgcolor=COR_BG,
                    padding=ft.Padding(25, 25, 25, 25),
                    border_radius=20,
                    width=650,
                    border=ft.Border.all(1, "#ffffff20")
                ),
                alignment=ft.Alignment(0, 0),
                bgcolor="#000000dd",
                expand=True,
                visible=True,
                on_click=lambda _: None  # Bloqueia cliques para os elementos abaixo do overlay
            )

            # Para evitar sobreposições infinitas, removemos os antigos
            for o in list(page.overlay):
                if getattr(o, "data", "") == "config_modal":
                    try: page.overlay.remove(o)
                    except: pass
            dlg_config.data = "config_modal"
            
            page.overlay.append(dlg_config)
            page.update()
            print("✅ [UI] Configurações abertas.")
        except Exception as ex:
            print(f"❌ [UI] Erro ao abrir configurações: {ex}")

    # ==========================
    # BARRA DE TÍTULO CUSTOMIZADA (PREMIUM) - FUNÇÃO GERADORA
    # ==========================
    def create_title_bar(title_text="ROCKS FIT - SISTEMA DE RECEPÇÃO"):
        def maximize_app(e): 
            pass

        return ft.Container(
            content=ft.Row(
                [
                    ft.WindowDragArea(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Image(src="media/imagens/rkslogo.png", height=20) if os.path.exists("media/imagens/rkslogo.png") else ft.Icon(ft.Icons.FITNESS_CENTER, color=COR_PRIMARY, size=20),
                                ft.Text(title_text, size=11, weight="bold", color=COR_TEXT_SEC, font_family="Space Grotesk"),
                            ], spacing=10),
                            padding=ft.Padding(left=20, right=0, top=0, bottom=0),
                        ),
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(content=ft.Icon(ft.Icons.SETTINGS, size=20, color="#adaaaa"), on_click=lambda _: abrir_configuracoes(), padding=6, border_radius=6, ink=True),
                            ],
                            spacing=0,
                        ),
                        padding=ft.Padding(right=10, left=0, top=0, bottom=0)
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
    dashboard_layout = ft.Column([create_title_bar(), main_container], expand=True, spacing=0)

    # --- ARQUITETURA SINGLE-VIEW (ESTABILIDADE TOTAL LINUX) ---
    app_content_wrapper = ft.Container(content=dashboard_layout, expand=True)
    page.add(app_content_wrapper)

    def route_change(e):
        route = e.route if hasattr(e, "route") else page.route
        print(f"🛣️ Roteamento Single-View: {route}")
        
        # Limpa callbacks globais
        state["_ui_identificado_cb"] = None
        state["_ui_aguardando_cb"] = None
        
        # Para câmera se estiver ativa
        if hasattr(page, "_cam_estado") and page._cam_estado:
            page._cam_estado["rodando"] = False
            time.sleep(0.3)

        if route == "/monitor":
            render_monitor_view()
        else:
            app_content_wrapper.content = dashboard_layout
            state["_ui_identificado_cb"] = lambda d, l, m, s: _dashboard_feedback(d, l, m, s)
            state["_ui_aguardando_cb"] = lambda: page.pubsub.send_all({"type": "aguardando"}) # Mantém compatibilidade
            rocksfit_core_update(page)


    def _dashboard_feedback(data, liberado, metodo, sentido="ENTRADA"):
        try:
            nome_completo = data.get("nome", "Cliente")
            nome = nome_completo.split()[0].upper()
            cor = COR_SUCCESS if liberado else COR_ERROR
            
            venc = data.get("vencimento", data.get("validade", "N/A"))
            dias = data.get("dias_restantes", data.get("dias", 0))
            matricula = data.get("matricula", "")
            
            # --- OTIMIZAÇÃO INDUSTRIAL DE VISUALIZAÇÃO: BASE64 EM MEMÓRIA ---
            import base64
            caminho_existente = None
            foto_base64 = None
            
            if matricula:
                for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
                    test_path = os.path.join("/home/ccs/Modelos/Rocks-Fit/media/alunos/fotos", f"aluno_{matricula}{ext}")
                    if os.path.exists(test_path):
                        caminho_existente = test_path
                        break
            
            if caminho_existente:
                try:
                    with open(caminho_existente, "rb") as image_file:
                        foto_base64 = "data:image/jpeg;base64," + base64.b64encode(image_file.read()).decode('utf-8')
                except Exception as ex:
                    print(f"⚠️ [UI] Erro base64 no painel: {ex}")
            
            # 1. ATUALIZA A SIDEBAR ESQUERDA (NO LUGAR DA LOGOMARCA)
            if lbl_side_nome:
                lbl_side_nome.value = f"{nome} - {sentido}"
                lbl_side_nome.color = cor
            
            if lbl_side_vencimento:
                lbl_side_vencimento.value = f"CRÉDITO: {dias} DIAS"

            if profile_img:
                if foto_base64:
                    profile_img.src = foto_base64
                else:
                    logo_path = "media/imagens/rkslogo.png"
                    if os.path.exists(logo_path):
                        profile_img.src = logo_path
                    else:
                        profile_img.src = TRANSPARENT_PIXEL
            
            # 2. ATUALIZA O MONITOR DE ACESSO DIREITO (MIRROR DO MONITOR DO ALUNO)
            try:
                if last_access_nome:
                    last_access_nome.value = nome_completo.upper()
                
                if last_access_matricula:
                    last_access_matricula.value = f"MATRÍCULA: {matricula}\nCRÉDITO: {dias} DIAS"
                
                if last_access_vencimento:
                    last_access_vencimento.value = f"VENC: {venc}"
                
                if last_access_status_txt:
                    last_access_status_txt.value = sentido
                
                if last_access_status_box:
                    last_access_status_box.bgcolor = cor
                
                if last_access_img:
                    if foto_base64:
                        last_access_img.src = foto_base64
                        last_access_img.visible = True
                        if last_access_placeholder: last_access_placeholder.visible = False
                    else:
                        last_access_img.src = TRANSPARENT_PIXEL
                        last_access_img.visible = False
                        if last_access_placeholder: last_access_placeholder.visible = True
            except Exception as ex:
                print(f"⚠️ [UI] Falha no monitor direito: {ex}")
                
            safe_update(page) # Atualização atômica imediata
            
            # REMOVIDO RESET DE TIMEOUT: Mantém a informação refletida persistentemente 
            # na tela até que o próximo aluno realize a identificação (conforme solicitado).
        except Exception as e:
            print(f"❌ [FEEDBACK ERROR] {e}")
            print(f"⚠️ [UI] Falha dashboard feedback: {e}")

    def render_monitor_view():
        # Elementos da UI do Monitor (Instâncias Únicas para esta "Vista")
        lbl_nome = ft.Text("AGUARDANDO", size=22, font_family="Space Grotesk", weight="bold", color="#ffffff", text_align=ft.TextAlign.CENTER)
        lbl_matricula = ft.Text("Posicione-se em frente à câmera", size=13, color="#adaaaa", text_align=ft.TextAlign.CENTER)
        lbl_msg = ft.Text("", size=22, weight="bold", color="#adaaaa", text_align=ft.TextAlign.CENTER)
        lbl_vencimento = ft.Text("", size=13, weight="bold", color="#ffffff")
        lbl_status_tag = ft.Text("INATIVO", size=14, weight="bold", color="#ff7351")
        lbl_cam_status = ft.Text("APROXIME-SE", size=14, weight="bold", color="#000000")
        
        # Placeholder transparente para evitar TransformLayer error no primeiro frame (JPEG)
        transparent_pixel = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYFBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD+f+iiigD/2Q=="
        img_cam = ft.Image(src=TRANSPARENT_PIXEL, width=640, height=480, fit="cover", border_radius=16)
        img_perfil = ft.Image(src="", width=180, height=180, border_radius=90, fit="cover", visible=False)
        
        # QR Code para suporte (WhatsApp)
        def get_qr():
            try:
                import urllib.parse
                qr = qrcode.QRCode(version=1, box_size=10, border=2)
                msg = "Estou com problemas no meu acesso, pode verificar por favor?"
                url = f"https://wa.me/5584999470586?text={urllib.parse.quote(msg)}"
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
            except: return ""
            
        img_qr = ft.Image(src=get_qr(), width=180, height=180, border_radius=12, visible=False)
        
        status_container = ft.Container(
            content=ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor="#ff7351"), lbl_status_tag], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#ff735133", padding=ft.Padding(left=20, right=20, top=10, bottom=10), border_radius=20,
        )

        badge_cam_status = ft.Container(
            content=ft.Row([ft.Container(width=12, height=12, border_radius=6, bgcolor="#000000"), lbl_cam_status], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            bgcolor=COR_PRIMARY, border_radius=20, padding=ft.Padding(left=24, right=24, top=10, bottom=10), margin=ft.Padding(left=0, right=0, top=0, bottom=20)
        )

        # Callbacks de UI (Capturam as instâncias locais acima)
        def _set_aguardando():
            lbl_nome.value = "AGUARDANDO"; lbl_nome.color = "#ffffff"
            lbl_matricula.value = "Posicione-se em frente à câmera"
            lbl_msg.value = "AGUARDANDO BIOMETRIA..."; lbl_msg.color = "#adaaaa"
            lbl_status_tag.value = "INATIVO"; status_container.bgcolor = "#ff735133"
            img_perfil.visible = False; img_qr.visible = False
            lbl_cam_status.value = "APROXIME-SE"; badge_cam_status.bgcolor = COR_PRIMARY
            rocksfit_core_update(page)

        def _set_identificado(data, liberado, metodo="FACIAL", sentido="ENTRADA"):
            nome = data.get("nome", "ALUNO").upper()
            mat = str(data.get("matricula", ""))
            lbl_nome.value = nome
            lbl_matricula.value = f"Matrícula: {mat} | {sentido}"
            
            dias = data.get("dias_restantes", 0)
            venc = data.get("vencimento", "N/A")
            lbl_vencimento.value = f"Crédito: {dias} dias | Venc: {venc}"
            
            furl = data.get("foto_url", "")
            if furl:
                if furl.startswith("/"): furl = f"{SITE_URL}{furl}"
                img_perfil.src = furl; img_perfil.visible = True
            
            if liberado:
                lbl_status_tag.value = f"✔ {sentido}"; lbl_status_tag.color = "#000000"
                cor = "#2ecc71"
                status_container.bgcolor = cor; badge_cam_status.bgcolor = cor
                lbl_cam_status.value = "Olá, bom treino" if sentido == "ENTRADA" else "Até logo"
                lbl_msg.value = "BOM TREINO!" if sentido == "ENTRADA" else "ATÉ AMANHÃ!"
                lbl_msg.color = cor
                threading.Thread(target=registrar_acesso_crm, args=(mat, metodo), daemon=True).start()
                trigger_catraca(sentido)
            else:
                lbl_status_tag.value = "✖ BLOQUEADO"; status_container.bgcolor = "#e74c3c"
                lbl_cam_status.value = "ACESSO NEGADO"; badge_cam_status.bgcolor = "#e74c3c"
                lbl_msg.value = "FALE CONOSCO"; lbl_msg.color = "#e74c3c"
                img_perfil.visible = False; img_qr.visible = True
                lbl_matricula.value = "Aponte o celular para o QR Code"
            
            safe_update(page)

        state["_ui_identificado_cb"] = _set_identificado
        state["_ui_aguardando_cb"] = _set_aguardando

        # Layout do Monitor (Full Premium)
        monitor_layout = ft.Container(
            content=ft.Column([
                create_title_bar("MONITOR DE ACESSO - ROCKS FIT"),
                ft.ResponsiveRow([
                    ft.Column([
                        ft.Container(
                            content=ft.Stack([
                                ft.Container(content=img_cam, expand=True, alignment=ft.Alignment(0, 0)),
                                ft.Container(content=badge_cam_status, alignment=ft.Alignment(0, 1))
                            ]), 
                            expand=True, bgcolor="#000000", border_radius=16, border=ft.Border.all(1, "#ffffff10"), clip_behavior=ft.ClipBehavior.HARD_EDGE
                        )
                    ], col={"sm": 12, "md": 7, "lg": 8}),
                    ft.Column([
                        ft.Container(content=ft.Column([
                            ft.Stack([img_perfil, img_qr], width=180, height=180),
                            lbl_nome, lbl_matricula, status_container, ft.Divider(height=20, color="#ffffff10"), 
                            ft.Row([ft.Text("UNIDADE", size=12, color="#adaaaa"), ft.Text("ROCKS FIT #01", size=13, weight="bold", color="#ffffff")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("VENCIMENTO", size=12, color="#adaaaa"), lbl_vencimento], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Container(content=lbl_msg, margin=ft.Padding(left=0, right=0, top=20, bottom=0))
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15), bgcolor=COR_CARD, padding=30, border_radius=20)
                    ], col={"sm": 12, "md": 5, "lg": 4})
                ], spacing=20, run_spacing=20, expand=True)
            ], expand=True),
            expand=True, bgcolor=COR_BG, padding=30
        )

        app_content_wrapper.content = monitor_layout
        rocksfit_core_update(page)
        time.sleep(0.5) # Estabilização térmica da UI (Harden Linux)

        # O monitor agora apenas consome o feed global que já está rodando em background
        def ui_feed_loop():
            # Inicializa estado se não existir
            if not hasattr(page, "_cam_estado"):
                page._cam_estado = {"rodando": True, "engine_alive": True}
            
            print("📺 [UI] Monitorando feed de câmera industrial...")
            last_frame = ""
            while page._cam_estado["rodando"] and page._engine_alive:
                try:
                    if not page._engine_alive: break
                    
                    with VISION_LOCK:
                        current_frame = GLOBAL_FRAME_BASE64
                    
                    if current_frame and current_frame != last_frame:
                        # Só atualiza se a string base64 for válida (mínimo de cabeçalho)
                        if len(current_frame) > 128:
                            with PAGE_LOCK:
                                if not page._engine_alive: break
                                img_cam.src = current_frame
                                last_frame = current_frame
                                try:
                                    img_cam.update()
                                except: pass
                                # Update assíncrono para evitar gargalo na thread principal
                                page.update()
                except BaseException as e:
                    pass
                time.sleep(0.1) # ~10 FPS estável para evitar sobrecarga no barramento USB/Gráfico
        
        threading.Thread(target=ui_feed_loop, daemon=True).start()

    # Configuração de Callbacks iniciais
    state["_ui_identificado_cb"] = _dashboard_feedback
    
    # Rastreamento de Sessão
    if state not in GLOBAL_SESSION_STATES:
        GLOBAL_SESSION_STATES.append(state)

    def on_close(e):
        # Sinaliza parada da câmera e invalida engine desta sessão
        page._engine_alive = False
        if hasattr(page, "_cam_estado") and page._cam_estado:
            page._cam_estado["rodando"] = False
            page._cam_estado["engine_alive"] = False
        if state in GLOBAL_SESSION_STATES:
            GLOBAL_SESSION_STATES.remove(state)
        # Pausa maior para threads pararem antes da engine sumir (Harden Linux)
        print("🛑 [SISTEMA] Encerrando sessão UI...")
        time.sleep(0.5)
    page.on_close = on_close

    page.on_route_change = route_change
    rocksfit_core_update(page)

    # --- HARDENING: INÍCIO DOS LOOPS DE HARDWARE (APÓS UI ESTABILIZAR - ASSÍNCRONO) ---
    def start_hardware_loops():
        global GLOBAL_LOOP_STARTED
        if GLOBAL_LOOP_STARTED:
            print("📡 [SISTEMA] Loops de hardware globais já estão ativos. Evitando duplicidade de barramento.")
            return
        GLOBAL_LOOP_STARTED = True

        time.sleep(2.0)
        if FPRINT_DISPONIVEL:
            print("☝️ [FPRINT] Ativando Biometria Always-On (Gestor)...")
            threading.Thread(target=global_loop_digital, daemon=True).start()
        
        print("🎥 [SISTEMA] Iniciando captura de vídeo industrial...")
        threading.Thread(target=loop_camera, daemon=True).start()
        
        print("📡 [SYNC] Ativando Sincronização em Tempo Real com Monitor...")
        threading.Thread(target=bridge_event_relay, daemon=True).start()
        threading.Thread(target=auto_calibration_loop, daemon=True).start()

    threading.Thread(target=start_hardware_loops, daemon=True).start()

# Fim da lógica de processamento de acesso

def auto_calibration_loop():
    """Loop 100% autônomo que roda a cada 15 minutos calibrando a biometria"""
    print("🔆 [CALIB] Robô autônomo iniciado (A cada 15 min).")
    while True:
        try:
            frame = None
            shared_path = "BIOMETRIA_DATA/shared_frame.jpg"
            if os.path.exists(shared_path):
                try:
                    frame = cv2.imread(shared_path)
                except: pass
            
            if frame is not None:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                brightness = float(np.mean(hsv[:, :, 2]))  # 0–255

                if brightness < 60:
                    new_thr, new_streak = 0.45, 1
                    perfil = f"🌑 ESCURO ({brightness:.0f}/255) → Threshold rígido"
                elif brightness < 110:
                    new_thr, new_streak = 0.50, 1
                    perfil = f"🌥️ MEIA-LUZ ({brightness:.0f}/255) → Threshold moderado"
                elif brightness < 170:
                    new_thr, new_streak = 0.52, 1
                    perfil = f"☀️ BOM ({brightness:.0f}/255) → Threshold ideal (Perfeito)"
                elif brightness < 220:
                    new_thr, new_streak = 0.55, 1
                    perfil = f"🌟 MUITO CLARO ({brightness:.0f}/255) → Threshold permissivo"
                else:
                    new_thr, new_streak = 0.58, 1
                    perfil = f"💡 SUPEREXPOSTO ({brightness:.0f}/255) → Threshold máximo"

                print(f"🔆 [CALIB-AUTO] Luminosidade: {brightness:.1f}/255 | Perfil: {perfil}")
                
                # Salvar no config.json de forma segura
                cfg = {}
                config_path = "BIOMETRIA_DATA/config.json"
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        try:
                            cfg = json.load(f)
                        except: pass
                
                cfg["face_threshold"] = new_thr
                cfg["face_streak"] = new_streak
                
                with open(config_path, "w") as f:
                    json.dump(cfg, f)
                
        except Exception as e:
            pass # Silencioso para não poluir o terminal
            
        # Espera 15 minutos (900 segundos) antes de calibrar novamente
        time.sleep(900)


def bridge_event_relay():
    """Monitora eventos vindos do Monitor do Aluno e sincroniza a UI do Gestor com segurança"""
    last_event_time = time.time()
    event_path = "BIOMETRIA_DATA/bridge_event.json"
    while True:
        try:
            if os.path.exists(event_path):
                with open(event_path, "r") as f:
                    ev = json.load(f)
                ev_time = ev.get("timestamp", 0)
                if ev_time > last_event_time:
                    last_event_time = ev_time
                    mat = ev.get("matricula")
                    met = ev.get("metodo", "FACIAL")
                    sent = ev.get("sentido", "ENTRADA")
                    
                    if mat and page_global:
                        # Busca aluno de forma segura (thread-safe copy)
                        alunos_snapshot = list(GLOBAL_ALUNOS)
                        aluno = next((a for a in alunos_snapshot if str(a.get("matricula")) == str(mat)), None)
                        
                        if aluno:
                            print(f"📡 [BRIDGE RELAY] Sincronizando: {aluno.get('nome')} ({met})")
                            liberado = is_liberado(aluno.get("status", ""))
                            
                            # Envia via PubSub com verificação rigorosa de engine (Harden Linux)
                            try:
                                # Bypassa o PubSub do Flet (que pode falhar em threads no Linux)
                                # e chama diretamente o callback da UI armazenado no state
                                if GLOBAL_SESSION_STATES:
                                    state_ativo = GLOBAL_SESSION_STATES[-1] # Pega a sessão mais recente
                                    if "_ui_identificado_cb" in state_ativo:
                                        print(f"✅ [BRIDGE RELAY] Invocando callback direto da UI...")
                                        state_ativo["_ui_identificado_cb"](aluno, liberado, f"{met} (MONITOR)", sent)
                                        
                                        # REDUNDÂNCIA INDUSTRIAL: Dispara catraca também pela ponte se o monitor falhar
                                        if liberado:
                                            threading.Thread(target=trigger_catraca, args=(sent,), daemon=True).start()
                                        
                                        # Reset automático após 5s
                                        def delayed_reset():
                                            time.sleep(5)
                                            try:
                                                if "_ui_aguardando_cb" in state_ativo:
                                                    state_ativo["_ui_aguardando_cb"]()
                                            except: pass
                                        threading.Thread(target=delayed_reset, daemon=True).start()
                                    else:
                                        print("⚠️ [BRIDGE RELAY] Callback _ui_identificado_cb não encontrado no state!")
                            except Exception as ex:
                                print(f"⚠️ [BRIDGE RELAY] Falha crítica ao atualizar UI: {ex}")

                        else:
                            print(f"⚠️ [BRIDGE RELAY] Matrícula {mat} não encontrada no GLOBAL_ALUNOS!")
        except Exception as e:
            # Silencioso para evitar crash no console
            pass
        time.sleep(1)

def process_match(matricula_alvo, matriculas_validas, metodo="DIGITAL"):
    global BIOMETRIA_BUSY, PAUSE_BIOMETRIA, page_global, IS_PROCESSING_MATCH
    if not MATCH_PROCESSING_LOCK.acquire(blocking=False): return
    try:
        if IS_PROCESSING_MATCH: return
        IS_PROCESSING_MATCH = True
        PAUSE_BIOMETRIA = True
        aluno = next((a for a in GLOBAL_ALUNOS if str(a.get("matricula")) == str(matricula_alvo)), None)
        if aluno:
            liberado = is_liberado(aluno.get("status", ""))
            sentido, allowed = detectar_sentido_acesso(str(matricula_alvo), metodo=metodo)
            
            if not allowed:
                # Se não permitido (carência), apenas loga e não abre catraca
                cooldown_time = 3 if metodo == "DIGITAL" else CONFIG.get("cooldown_facial", 30)
                print(f"🚫 [{metodo}] Acesso negado por carência de {cooldown_time}s: {matricula_alvo}")
                return

            registrar_acesso_local(matricula_alvo, metodo, sentido)
            log_acesso_local(aluno, metodo, "LIBERADO" if liberado else "BLOQUEADO", sentido)
            
            # Envia para a UI e Monitor
            safe_pubsub_send({
                "type": "identificacao", 
                "data": aluno, 
                "liberado": liberado, 
                "metodo": metodo, 
                "sentido": sentido
            })

            # Notifica o Monitor do Aluno (Processo Externo)
            try:
                os.makedirs("BIOMETRIA_DATA", exist_ok=True)
                with open("BIOMETRIA_DATA/monitor_event.json", "w") as f:
                    json.dump({
                        "matricula": matricula_alvo, 
                        "metodo": metodo, 
                        "sentido": sentido, # Passa o sentido calculado
                        "timestamp": time.time(),
                        "aluno_data": aluno
                    }, f)
            except: pass

            # Dispara a catraca de forma assíncrona (não-bloqueante) em segundo plano
            # para não atrasar a atualização da foto e o fluxo da UI
            if liberado:
                threading.Thread(target=trigger_catraca, args=(sentido,), daemon=True).start()
            
            # Pequeno delay de segurança antes de liberar o processamento
            time.sleep(0.5)
            safe_pubsub_send({"type": "aguardando"})
    finally:
        if not ENROLLMENT_ACTIVE: PAUSE_BIOMETRIA = False
        BIOMETRIA_BUSY = False
        IS_PROCESSING_MATCH = False
        MATCH_PROCESSING_LOCK.release()

def global_loop_digital():
    global BIOMETRIA_BUSY, PAUSE_BIOMETRIA, GLOBAL_PRIORITY_MATRICULA
    if not FPRINT_DISPONIVEL: return
    
    err_count = 0
    no_device_logged = False  # Evita spam de log quando o sensor está ausente
    while True:
        try:
            GLOBAL_PRIORITY_MATRICULA = None
            if PAUSE_BIOMETRIA:
                try:
                    with open("BIOMETRIA_DATA/scanner_status.json", "w") as f:
                        json.dump({"status": "ENROLLING", "timestamp": time.time()}, f)
                except: pass
                time.sleep(0.1); continue
            
            # Notifica que o scanner está ativo para identificação
            try:
                with open("BIOMETRIA_DATA/scanner_status.json", "w") as f:
                    json.dump({"status": "ACTIVE", "timestamp": time.time()}, f)
            except: pass

            BIOMETRIA_BUSY = True
            res = biometria_manager_global.verify(timeout=15)
            BIOMETRIA_BUSY = False
            
            if PAUSE_BIOMETRIA: continue

            # --- None = hardware ausente (sensor desconectado/sem dispositivo) ---
            # Não é um erro; aguarda e tenta novamente após 10s sem spam de log.
            if res is None:
                if not no_device_logged:
                    print("⚠️ [FPRINT] Sensor biométrico não detectado. Aguardando conexão...")
                    safe_pubsub_send({"type": "hw_status", "hw": "fprint", "online": False})
                    no_device_logged = True
                time.sleep(2)  # Verifica novamente após 2s (mais responsivo ao reconectar USB)
                continue

            # Se chegou aqui, o hardware voltou
            if no_device_logged:
                print("✅ [FPRINT] Sensor biométrico reconectado!")
                no_device_logged = False
            
            if res is False:
                safe_pubsub_send({"type": "hw_status", "hw": "fprint", "online": False})
                err_count += 1
                if err_count > 10: # Aumentado de 3 para 10 para evitar death spiral
                    print("☢️ [FPRINT] Erros persistentes (10+). Tentativa de recuperação...")
                    nuclear_cleanup()
                    err_count = 0
                    time.sleep(5) # Espera maior após limpeza
            
            # Modo Industrial: Ciclo contínuo de verificação
            if res and isinstance(res, str) and res != "NO_MATCH":
                safe_pubsub_send({"type": "hw_status", "hw": "fprint", "online": True})
                mats = BIOMETRIA_MAPPING_CACHE.get(res, [])
                if mats:
                    mat_identificad = mats[0]
                    print(f"🎯 [FPRINT] Mapeado dedo {res} para matricula {mat_identificad}")
                    process_match(mat_identificad, GLOBAL_ALUNOS, metodo="DIGITAL")
                else:
                    print(f"⚠️ [FPRINT] Dedo {res} reconhecido, mas nenhuma matrícula mapeada no banco local.")
        except: pass

def global_loop_camera():
    """Deprecated vision loop – processing moved to remote Django API.
    The local client now only captures frames, sends them to the server,
    and displays the preview. Keeping this stub avoids import errors
    and satisfies references elsewhere in the code.
    """
    print("⚠️ [NOTICE] global_loop_camera() is deprecated – use the Flet client to capture and send frames to the API.")
    # No operation – actual camera handling is performed in the Flet UI thread (see loop_camera()).

def loop_camera():
    """Captura de câmera local e comunicação com o backend DeepFace.
    Substitui a antiga `global_loop_camera`, delegando a inferência ao
    servidor Django, garantindo alta velocidade e resiliência.
    """
    # Garante diretório offline
    os.makedirs("BIOMETRIA_DATA/offline_queue", exist_ok=True)
    
    print("🎥 [SISTEMA] Iniciando captura de vídeo industrial...")
    
    # --- ABERTURA ANTI-TRAVAMENTO DA CÂMERA ---
    # No Linux, cv2.VideoCapture(0) sem backend pode tentar múltiplos drivers e
    # bloquear por muitos segundos. Usamos V4L2 diretamente e definimos um buffer
    # mínimo (1 frame) para evitar acúmulo de frames antigos na memória.
    cap = None
    backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
    for idx in [0, 1, 2]:  # Reduzido: tenta apenas 0, 1, 2 (os mais comuns)
        try:
            print(f"🎥 [CAM] Tentando abrir dispositivo {idx} (backend V4L2)...")
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                # Buffer de 1 frame: evita fila de frames velhos e reduz latência
                c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # Resolução 640x480: Qualidade maior para o motor neural
                c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                c.set(cv2.CAP_PROP_FPS, 15)  # 15 FPS é suficiente para reconhecimento
                cap = c
                print(f"✅ [CAM] Câmera ativa no dispositivo {idx} | Res: 320x240 | FPS: 15")
                break
            c.release()
        except Exception as e:
            print(f"⚠️ [CAM] Falha no dispositivo {idx}: {e}")
            pass
            
    if not cap or not cap.isOpened():
        print("❌ [CAM] Falha crítica: Nenhuma câmera detectada no sistema.")
        return
    
    print("✅ [CAM] Visão industrial ativa e transmitindo.")

    def inference_worker(img_b64, frame_buffer):
        """Worker assíncrono para inferência DeepFace com Fallback Local de alta performance."""
        if INFERENCE_LOCK.locked(): return
        with INFERENCE_LOCK:
            success = False
            try:
                resp = requests.post(
                    "http://localhost:8000/api/biometria/verificar/",
                    json={"image": img_b64},
                    timeout=2.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    mat = data.get("matricula")
                    if mat and mat != "NO_MATCH":
                        print(f"👤 [FACIAL ONLINE] Identificado: {mat} (Dist: {data.get('distancia', 0):.4f})")
                        process_match(mat, GLOBAL_ALUNOS, metodo="FACIAL")
                        success = True
                else:
                    raise Exception("Status API inválido")
            except Exception as e:
                # --- OTIMIZAÇÃO INDUSTRIAL: FALLBACK DE RECONHECIMENTO FACIAL OFFLINE ---
                # Se o Django estiver fora do ar ou sem rede, realizamos a inferência DeepFace
                # diretamente aqui na recepção de forma ultrarrápida usando o cache local de .npy!
                try:
                    import base64
                    import cv2
                    import numpy as np
                    from deepface import DeepFace
                    
                    # 1. Decodifica a imagem Base64 vinda da câmera
                    img_bytes = base64.b64decode(img_b64)
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None and GLOBAL_EMBEDDINGS_CACHE:
                        # 2. Extrai embedding usando ArcFace localmente (Sem detecção lenta de bounding boxes)
                        results = DeepFace.represent(
                            img_path=frame,
                            model_name="ArcFace",
                            enforce_detection=False,
                            detector_backend="skip"
                        )
                        
                        if results and len(results) > 0:
                            embedding_np = np.array(results[0]["embedding"])
                            norm_a = np.linalg.norm(embedding_np)
                            
                            best_match = None
                            min_dist = 999.0
                            threshold = 0.55  # Alinhado com o threshold rigoroso do backend
                            
                            # 3. Varredura vetorial Cosine em memória (sub-microssegundo)
                            for matricula, stored_embedding in GLOBAL_EMBEDDINGS_CACHE.items():
                                try:
                                    norm_b = np.linalg.norm(stored_embedding)
                                    cosine_sim = np.dot(embedding_np, stored_embedding) / (norm_a * norm_b)
                                    dist = 1.0 - cosine_sim
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_match = matricula
                                except: continue
                            
                            if best_match and min_dist < threshold:
                                print(f"👤 [FACIAL OFFLINE] Identificado localmente via cache .npy: {best_match} (Dist: {min_dist:.4f})")
                                process_match(best_match, GLOBAL_ALUNOS, metodo="FACIAL")
                except Exception as ex:
                    # Silencioso para não travar a thread de visão nem poluir a tela
                    pass

    global GLOBAL_FRAME_COUNT
    last_inference_time = 0
    while True:
        try:
            # Throttle para evitar 100% de CPU e travamento do sistema
            time.sleep(0.04) 

            ret, frame_raw = cap.read()
            if not ret or frame_raw is None:
                time.sleep(0.1)
                continue

            GLOBAL_FRAME_COUNT += 1
            # Espelha para visualização natural
            frame = cv2.flip(frame_raw, 1)

            # Detecção leve apenas para o HUD (Quadrado de busca) - Não é reconhecimento neural!
            faces_hud = []
            if GLOBAL_FRAME_COUNT % 2 == 0:
                try:
                    if frame is not None and frame.size > 0:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        h, w = gray.shape[:2]
                        if h > 50 and w > 50:
                            # Detecção de alta sensibilidade no frame completo
                            detected = FACE_CASCADE.detectMultiScale(gray, 1.1, 2)
                            for (x, y, w_f, h_f) in detected:
                                # top, right, bottom, left (escala 0.5 compatível com monitor_aluno)
                                faces_hud.append([int(y * 0.5), int((x+w_f) * 0.5), int((y+h_f) * 0.5), int(x * 0.5)])
                            
                            # Exporta para o monitor consumir
                            with open("BIOMETRIA_DATA/faces_detected.json", "w") as f:
                                json.dump({"faces": faces_hud, "ts": time.time()}, f)
                except Exception as e:
                    print(f"⚠️ [HUD] Erro na detecção: {e}")
                    pass

            # Converte para JPEG + base64 (Qualidade aumentada para reconhecimento facial)
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not success: continue
            
            img_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

            # Shared Frame Service (Feed para o monitor do aluno) - Otimizado para não travar I/O
            if GLOBAL_FRAME_COUNT % 3 == 0:
                try:
                    temp_path = "BIOMETRIA_DATA/shared_frame.tmp"
                    with open(temp_path, "wb") as f:
                        f.write(buffer.tobytes())
                    os.replace(temp_path, "BIOMETRIA_DATA/shared_frame.jpg")
                    if GLOBAL_FRAME_COUNT == 3: # Loga apenas o primeiro para não sujar o terminal
                        print("📡 [SHARED-FEED] Transmitindo frames para o Monitor do Aluno...")
                except Exception as e:
                    print(f"⚠️ [SHARED-FEED] Erro ao gravar frame: {e}")
                    pass

            # Atualiza UI global de forma thread-safe
            with VISION_LOCK:
                global GLOBAL_FRAME_BASE64
                GLOBAL_FRAME_BASE64 = img_b64

            # Inferência Assíncrona Otimizada (A cada 2 frames ou 0.1s se houver rosto - Primeira tentativa rápida)
            current_time = time.time()
            if GLOBAL_FRAME_COUNT % 2 == 0 and (current_time - last_inference_time) > 0.1:
                if not INFERENCE_LOCK.locked():
                    last_inference_time = current_time
                    target_img_b64 = img_b64
                    target_buffer = buffer.tobytes()
                    
                    # Se detectamos um rosto pelo Haar Cascade, enviamos o RECORTE para a API
                    if faces_hud:
                        try:
                            # Ordena por tamanho para pegar o rosto mais próximo
                            face = sorted(faces_hud, key=lambda f: (f[2]-f[0])*(f[1]-f[3]), reverse=True)[0]
                            # Escala de volta (faces_hud foi reduzido 50%)
                            y1, x2, y2, x1 = face[0]*2, face[1]*2, face[2]*2, face[3]*2
                            # Margem de 10%
                            margin_y = int((y2-y1)*0.1)
                            margin_x = int((x2-x1)*0.1)
                            crop = frame[max(0, y1-margin_y):min(480, y2+margin_y), 
                                         max(0, x1-margin_x):min(640, x2+margin_x)]
                            
                            if crop.size > 0:
                                success, c_buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
                                if success:
                                    target_img_b64 = base64.b64encode(c_buf).decode('utf-8')
                                    target_buffer = c_buf.tobytes()
                        except: pass
                    
                    threading.Thread(target=inference_worker, args=(target_img_b64, target_buffer), daemon=True).start()

        except Exception as e:
            time.sleep(0.1)

if __name__ == "__main__":
    # Hardening Industrial: Limpeza nuclear no startup
    nuclear_cleanup()
    
    threading.Thread(target=run_api, daemon=True).start()
    
    # Limpa processos de biometria residuais
    try: 
        print("🧹 [SISTEMA] Limpando processos residuais...")
        biometria_manager_global.stop_all()
        time.sleep(1)
    except: pass

    carregar_cache_local()

    print("🚀 Iniciando Módulo de Recepção Rocks-Fit...")
    print("🌐 Dashboard Flet disponível em: http://localhost:8552")
    time.sleep(1) # Delay de segurança para estabilização de hardware/renderização
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
            
        # Usa ft.run para versões modernas ou ft.app como fallback seguro
        if hasattr(ft, "run"):
            ft.run(main, view=view_mode, port=8552, assets_dir=".")
        else:
            # Garante que passamos os argumentos corretos para ft.app legado
            ft.app(target=main, view=view_mode, port=8552, assets_dir=".")
    except Exception as e:
        print(f"⚠️ [FLET] Falha ao iniciar a interface gráfica Flet: {e}")