import customtkinter as ctk
from PIL import Image, ImageTk
import requests
import socket
import threading
import time
from datetime import datetime
from io import BytesIO
import os
import base64
import json

# --- 🚀 GESTÃO ROCKS FIT v3.0.0 (INDUSTRIAL RKS EDITION) ---
SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rocksfit@2024"
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 1001
SERVIDOR_PORTA = 5000

# Palette Industrial RKS
COR_BG = "#0e0e0e"
COR_CARD = "#131313"
COR_CARD_HIGH = "#1a1a1a"
COR_TEXTO = "#ffffff"
COR_PRIMARY = "#ff9159" # Laranja Industrial
COR_TEXT_SEC = "#adaaaa"
COR_SUCCESS = "#4ade80"
COR_ERROR = "#ff7351"

# --- 📂 DETECÇÃO DE CAMINHOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _encontrar_arquivo(nome_relativo):
    caminho = os.path.join(BASE_DIR, nome_relativo)
    return caminho if os.path.exists(caminho) else nome_relativo

CAMINHO_CACHE = _encontrar_arquivo(os.path.join("rks-catraca", "alunos_local.json"))
CAMINHO_LOGO  = _encontrar_arquivo(os.path.join("media", "images", "rkslogo.png"))

try:
    import cv2
    OPENCV_OK = True
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except:
    OPENCV_OK = False

ctk.set_appearance_mode("dark")

class JanelaMonitor(ctk.CTkToplevel):
    """ TELA DO ALUNO: COM INTERFACE TÁTICA DE ESCANEAMENTO """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PERÍMETRO DE IDENTIFICAÇÃO - ROCKS FIT")
        self.geometry("1024x768")
        self.attributes("-fullscreen", False) # Pode ser True em produção
        self.configure(fg_color=COR_BG)
        self.parent = parent
        self.rodando = True
        self.setup_ui()
        if OPENCV_OK:
            self.cap = cv2.VideoCapture(0)
            threading.Thread(target=self.loop_camera, daemon=True).start()

    def setup_ui(self):
        # Header Técnico
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=100)
        self.header.pack(fill="x", padx=40, pady=(40, 0))
        
        lbl_brand = ctk.CTkLabel(self.header, text="ROCKS FIT", font=("Space Grotesk", 48, "bold"), text_color=COR_PRIMARY)
        lbl_brand.pack(side="left")
        
        lbl_mode = ctk.CTkLabel(self.header, text="|  TERMINAL DE DIAGNÓSTICO  |  v3.0.0", font=("Inter", 12, "bold"), text_color=COR_TEXT_SEC)
        lbl_mode.pack(side="left", padx=20, pady=(20, 0))

        # Grid Principal
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40, pady=40)

        # Câmera (Hexagonal Style/Square Industrial)
        self.cam_f = ctk.CTkFrame(self.container, width=640, height=480, fg_color="#000", corner_radius=30, border_width=2, border_color=COR_CARD_HIGH)
        self.cam_f.pack(side="left", fill="both", expand=True)
        self.cam_f.pack_propagate(False)
        
        self.lbl_cam = ctk.CTkLabel(self.cam_f, text="INICIALIZANDO SENSORES ÓPTICOS...", text_color=COR_TEXT_SEC, font=("Inter", 14, "bold"))
        self.lbl_cam.pack(expand=True)

        # Dossier de Identificação (Direita)
        self.info_f = ctk.CTkFrame(self.container, width=320, fg_color="transparent")
        self.info_f.pack(side="right", fill="both", padx=(40, 0))

        # Avatar Container
        self.avatar_f = ctk.CTkFrame(self.info_f, width=280, height=280, corner_radius=40, fg_color=COR_CARD, border_width=1, border_color=COR_CARD_HIGH)
        self.avatar_f.pack(pady=(0, 30)); self.avatar_f.pack_propagate(False)
        self.lbl_aluno_foto = ctk.CTkLabel(self.avatar_f, text="PRONTO", font=("Inter", 18, "bold"), text_color=COR_TEXT_SEC)
        self.lbl_aluno_foto.pack(expand=True)

        self.lbl_nome = ctk.CTkLabel(self.info_f, text="ÁREA DE ESCANEAMENTO", font=("Space Grotesk", 32, "bold"), text_color=COR_TEXTO, wraplength=300, justify="left")
        self.lbl_nome.pack(anchor="w")
        
        self.lbl_status = ctk.CTkLabel(self.info_f, text="AGUARDANDO BIOMETRIA", font=("Inter", 11, "bold"), text_color=COR_TEXT_SEC, anchor="w")
        self.lbl_status.pack(anchor="w", pady=10)
        
        self.status_bar = ctk.CTkFrame(self.info_f, height=4, fg_color=COR_CARD_HIGH, corner_radius=2)
        self.status_bar.pack(fill="x", pady=20)
        self.bar_fill = ctk.CTkFrame(self.status_bar, width=0, height=4, fg_color=COR_PRIMARY, corner_radius=2)
        self.bar_fill.place(x=0, y=0)

    def loop_camera(self):
        while self.rodando:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1) # Espelhado para o aluno
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5)
                
                # Efeito Tecnológico no Frame
                for (x, y, w, h) in faces:
                    # Mira nos Cantos (Industrial Style)
                    l = 40; t = 3
                    cv2.line(frame, (x, y), (x+l, y), (89, 145, 255), t)
                    cv2.line(frame, (x, y), (x, y+l), (89, 145, 255), t)
                    cv2.line(frame, (x+w, y), (x+w-l, y), (89, 145, 255), t)
                    cv2.line(frame, (x+w, y), (x+w, y+l), (89, 145, 255), t)
                    cv2.line(frame, (x, y+h), (x+l, y+h), (89, 145, 255), t)
                    cv2.line(frame, (x, y+h), (x, y+h-l), (89, 145, 255), t)
                    cv2.line(frame, (x+w, y+h), (x+w-l, y+h), (89, 145, 255), t)
                    cv2.line(frame, (x+w, y+h), (x+w, y+h-l), (89, 145, 255), t)
                    cv2.putText(frame, "TRAVADO", (x, y-15), cv2.FONT_HERSHEY_DUPLEX, 0.6, (89, 145, 255), 1)

                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((640, 480))
                self.photo = ImageTk.PhotoImage(img)
                self.after(0, lambda: self.lbl_cam.configure(image=self.photo, text=""))
            time.sleep(0.01)

    def indentificar_aluno(self, d):
        self.lbl_nome.configure(text=d.get('nome', 'IDENTIFIED').upper())
        self.lbl_status.configure(text="ACESSO AUTORIZADO | STATUS: ATIVO", text_color=COR_SUCCESS)
        self.bar_fill.configure(width=300, fg_color=COR_SUCCESS)
        if d.get('foto_url'): threading.Thread(target=self.carregar_foto, args=(d.get('foto_url'),), daemon=True).start()
        threading.Timer(5, self.reset).start()

    def carregar_foto(self, url):
        try:
            r = requests.get(url, timeout=5)
            i = Image.open(BytesIO(r.content)).resize((280, 280), Image.Resampling.LANCZOS)
            p = ImageTk.PhotoImage(i); self.lbl_aluno_foto.configure(image=p, text=""); self.lbl_aluno_foto.image = p
        except: pass

    def reset(self):
        self.lbl_nome.configure(text="SCANNING AREA")
        self.lbl_status.configure(text="AGUARDANDO BIOMETRIA", text_color=COR_TEXT_SEC)
        self.lbl_aluno_foto.configure(image=None, text="READY")
        self.bar_fill.configure(width=0, fg_color=COR_PRIMARY)

    def fechar(self):
        self.rodando = False
        if OPENCV_OK: self.cap.release()
        self.destroy()

class AppRecepcao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ROCKS FIT | TERMINAL INDUSTRIAL RKS")
        self.geometry("1100x850"); self.configure(fg_color=COR_BG)
        self.monitor = None; self.alunos_data = []; self.aluno_em_registro = None
        
        self.setup_ui()
        threading.Thread(target=self.servidor_bio, daemon=True).start()
        self.carregar_alunos()
        self.after(30000, self.auto_sync)

    def setup_ui(self):
        # Sidebar Técnico (Estilo Industrial site)
        self.sidebar = ctk.CTkFrame(self, width=240, fg_color=COR_CARD, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text="ROCKS FIT", font=("Space Grotesk", 24, "bold"), text_color=COR_PRIMARY).pack(pady=40)
        
        # Botões de Ação Visualmente Fortes
        btn_st = {"height": 50, "corner_radius": 15, "font": ("Inter", 12, "bold")}
        ctk.CTkButton(self.sidebar, text="🖥️ MONITORAR ALUNO", fg_color=COR_PRIMARY, text_color=COR_BG, command=self.saltar_monitor, **btn_st).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="🔄 SINCRONIZAR", fg_color=COR_BG, border_width=1, border_color=COR_CARD_HIGH, command=self.carregar_alunos, **btn_st).pack(pady=10, padx=20, fill="x")
        
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COR_CARD_HIGH).pack(fill="x", pady=20, padx=30)
        
        ctk.CTkButton(self.sidebar, text="🔓 ABRIR ENTRADA", fg_color="#1e2d24", text_color=COR_SUCCESS, hover_color="#233b2b", command=lambda: self.abrir_catraca("0"), **btn_st).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="🔒 ABRIR SAÍDA", fg_color="#2d1e1e", text_color=COR_ERROR, hover_color="#3b2323", command=lambda: self.abrir_catraca("1"), **btn_st).pack(pady=5, padx=20, fill="x")

        # Área Principal
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        
        # Busca Estilizada
        self.search_f = ctk.CTkFrame(self.main, fg_color=COR_CARD, height=60, corner_radius=20, border_width=1, border_color=COR_CARD_HIGH)
        self.search_f.pack(fill="x", pady=(0, 20)); self.search_f.pack_propagate(False)
        self.e_search = ctk.CTkEntry(self.search_f, placeholder_text="PESQUISAR PERFIL (NOME OU CPF)...", fg_color="transparent", border_width=0, font=("Inter", 13))
        self.e_search.pack(fill="both", expand=True, padx=20)
        self.e_search.bind("<KeyRelease>", lambda e: self.render_list(self.e_search.get()))

        # Lista de Alunos (Bento Grid Style em Scroll)
        self.sr = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        self.sr.pack(fill="both", expand=True)

    def saltar_monitor(self):
        if self.monitor and self.monitor.winfo_exists(): self.monitor.fechar()
        self.monitor = JanelaMonitor(self)

    def carregar_alunos(self):
        u = f"{SITE_URL}/api/aluno-list-full/?token={SYNC_TOKEN}"
        print(f"[SYNC] Iniciando sincronização com {SITE_URL}...")
        def f():
            try:
                r = requests.get(u, timeout=12)
                if r.status_code == 200:
                    self.alunos_data = r.json().get('alunos', [])
                    print(f"[SYNC] Sucesso! {len(self.alunos_data)} alunos carregados.")
                    self.after(0, self.mostrar_todos)
                else:
                    print(f"[SYNC] Erro na API: Status {r.status_code}")
            except Exception as e:
                print(f"[SYNC] Falha crítica de conexão: {e}")
        threading.Thread(target=f, daemon=True).start()

    def mostrar_todos(self): self.render_list("")

    def render_list(self, filter=""):
        for w in self.sr.winfo_children(): w.destroy()
        for a in self.alunos_data:
            if filter.lower() in a['nome'].lower() or filter in a['cpf']:
                st_c = COR_SUCCESS if "ATIVO" in a['status'] else COR_ERROR
                
                c = ctk.CTkFrame(self.sr, fg_color=COR_CARD, height=100, corner_radius=25, border_width=1, border_color=COR_CARD_HIGH)
                c.pack(fill="x", pady=8, padx=5); c.pack_propagate(False)
                
                # Barra de Status Lateral
                ctk.CTkFrame(c, width=6, fg_color=st_c, corner_radius=3).pack(side="left", fill="y", padx=2, pady=15)
                
                # Conteúdo
                info = f"{a['nome'].upper()}\nMAT: {a['matricula']} | {a['status']}"
                lbl = ctk.CTkLabel(c, text=info, font=("Inter", 13, "bold"), text_color=COR_TEXTO, justify="left")
                lbl.pack(side="left", padx=25)
                
                # Ações Rápidas
                a_f = ctk.CTkFrame(c, fg_color="transparent")
                a_f.pack(side="right", padx=15)
                ctk.CTkButton(a_f, text="📸", width=40, font=("Inter", 14), fg_color=COR_CARD_HIGH, command=lambda aid=a['id']: self.reg_foto_imediata(aid)).pack(side="left", padx=5)
                ctk.CTkButton(a_f, text="☝️", width=40, font=("Inter", 14), fg_color=COR_CARD_HIGH, command=lambda aid=a['id']: self.iniciar_registro_digital(aid)).pack(side="left", padx=5)

    def reg_foto_imediata(self, aid):
        if self.monitor and self.monitor.winfo_exists():
            ret, frame = self.monitor.cap.read()
            if ret:
                _, b = cv2.imencode('.jpg', frame)
                b64 = f"data:image/jpeg;base64,{base64.b64encode(b).decode('utf-8')}"
                threading.Thread(target=lambda: requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'foto': b64, 'token': SYNC_TOKEN})).start()

    def auto_sync(self): self.carregar_alunos(); self.after(30000, self.auto_sync)
    
    def abrir_catraca(self, s="0"):
        def c():
            try:
                p = b"lgu" + (b"\x00" if s == "0" else b"\x01") + b"Protocol Access"
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as k:
                    k.settimeout(2); k.connect((CATRACA_IP, CATRACA_PORTA)); k.sendall(p)
            except: pass
        threading.Thread(target=c, daemon=True).start()

    def iniciar_registro_digital(self, aid): self.aluno_em_registro = aid

    def servidor_bio(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sv:
            sv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sv.bind(('0.0.0.0', SERVIDOR_PORTA)); sv.listen(5)
            while True:
                conn, _ = sv.accept()
                with conn:
                    raw = conn.recv(1024).decode('utf-8', errors='ignore')
                    if raw:
                        tag = raw.split('|')[1] if '|' in raw else raw.strip()
                        if self.aluno_em_registro: self.vincular_bio(self.aluno_em_registro, tag); self.aluno_em_registro = None
                        else: self.validar(tag)

    def vincular_bio(self, aid, tag):
        try: requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'digital': tag, 'token': SYNC_TOKEN})
        except: pass

    def validar(self, tag):
        try:
            r = requests.get(f"{SITE_URL}/api/catraca-check/{tag}/?token={SYNC_TOKEN}").json()
            if r.get('status') != 'vencido': 
                self.abrir_catraca("0")
                if self.monitor and self.monitor.winfo_exists(): self.after(0, lambda: self.monitor.indentificar_aluno(r))
        except: pass

if __name__ == "__main__":
    AppRecepcao().mainloop()
