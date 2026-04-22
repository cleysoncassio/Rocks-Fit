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
CATRACA_PORTA = 3000  # Port 3000 is standard for most Toletus/Henry devices
SERVIDOR_PORTA = 5000
POLLING_INTERVAL = 3  # Seconds between remote release checks

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
    possibilidades = [
        os.path.join(BASE_DIR, nome_relativo),
        os.path.join(BASE_DIR, os.path.basename(nome_relativo)),
        os.path.join(BASE_DIR, "media", "images", os.path.basename(nome_relativo)),
        os.path.join(BASE_DIR, "media", "rks01.png"), 
        os.path.join(BASE_DIR, "rks01.png")
    ]
    for p in possibilidades:
        if os.path.exists(p): return p
    return os.path.join(BASE_DIR, nome_relativo)

CAMINHO_CACHE = _encontrar_arquivo("alunos_local.json")
CAMINHO_LOGO  = _encontrar_arquivo("rkslogo.png")

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

    def flash_effect(self):
        # Efeito visual de disparador de câmera
        self.cam_f.configure(border_color="#ffffff")
        self.after(100, lambda: self.cam_f.configure(border_color=COR_CARD_HIGH))

    def identificar_aluno(self, d):
        self.lbl_nome.configure(text=d.get('nome', 'IDENTIFICADO').upper())
        self.lbl_status.configure(text="ACESSO AUTORIZADO | STATUS: ATIVO", text_color=COR_SUCCESS)
        self.bar_fill.configure(width=300, fg_color=COR_SUCCESS)
        if d.get('foto_url'): threading.Thread(target=self.carregar_foto, args=(d.get('foto_url'),), daemon=True).start()
        threading.Timer(5, self.reset).start()

    def reset(self):
        self.lbl_nome.configure(text="ÁREA DE ESCANEAMENTO")
        self.lbl_status.configure(text="AGUARDANDO BIOMETRIA", text_color=COR_TEXT_SEC)
        self.lbl_aluno_foto.configure(image=None, text="PRONTO")
        self.bar_fill.configure(width=0, fg_color=COR_PRIMARY)

    def fechar(self):
        self.rodando = False
        if OPENCV_OK: self.cap.release()
        self.destroy()

    def carregar_foto(self, url):
        try:
            r = requests.get(url, timeout=5)
            i = Image.open(BytesIO(r.content)).resize((280, 280), Image.Resampling.LANCZOS)
            p = ImageTk.PhotoImage(i); self.lbl_aluno_foto.configure(image=p, text=""); self.lbl_aluno_foto.image = p
        except: pass

# --- 🧬 JANELAS E OVERLAYS ---
# Removida JanelaCadastroBio externa para usar Overlay interno (mais estável no Windows)

class AppRecepcao(ctk.CTk):
    def __init__(self):
        super().__init__()
        # DPI Awareness para Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except: pass

        self.title("ROCKS FIT | TERMINAL INDUSTRIAL RKS")
        self.geometry("1100x850"); self.configure(fg_color=COR_BG)
        self.monitor = None; self.alunos_data = []; self.aluno_em_registro = None
        self.overlay_bio = None
        
        self.setup_ui()
        threading.Thread(target=self.servidor_bio, daemon=True).start()
        threading.Thread(target=self.remote_polling, daemon=True).start()
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

    def mostrar_todos(self): 
        self.render_list("")

    def render_list(self, filter_text=""):
        for w in self.sr.winfo_children(): w.destroy()
        
        if filter_text:
            resultados = [a for a in self.alunos_data if filter_text.lower() in str(a.get('nome','')).lower() or filter_text in str(a.get('cpf',''))]
            # Mostra apenas os 10 primeiros resultados da busca também para ser ultra rápido
            render_data = resultados[:10]
        else:
            # Mostra apenas os 10 primeiros (conforme solicitado)
            render_data = self.alunos_data[:10]
        
        # REMOVIDO: self.e_search.configure(placeholder_text=msg) para evitar lag ao digitar

        for a in render_data:
            nome = a.get('nome', 'Sem Nome')
            status = a.get('status', 'INATIVO')
            st_c = COR_SUCCESS if "ATIVO" in status.upper() or "LIBERADO" in status.upper() else COR_ERROR
            
            c = ctk.CTkFrame(self.sr, fg_color=COR_CARD, height=85, corner_radius=15, border_width=1, border_color=COR_CARD_HIGH)
            c.pack(fill="x", pady=5, padx=10); c.pack_propagate(False)
            
            ctk.CTkFrame(c, width=4, fg_color=st_c, corner_radius=2).pack(side="left", fill="y", padx=2, pady=10)
            
            info = f"{nome.upper()[:40]}\nMAT: {a.get('matricula', '---')} | {status}"
            lbl = ctk.CTkLabel(c, text=info, font=("Inter", 12, "bold"), text_color=COR_TEXTO, justify="left")
            lbl.pack(side="left", padx=15)

            a_f = ctk.CTkFrame(c, fg_color="transparent")
            a_f.pack(side="right", padx=15)
            ctk.CTkButton(a_f, text="📸", width=40, font=("Inter", 14), fg_color=COR_CARD_HIGH, command=lambda aid=a['id']: self.reg_foto_imediata(aid)).pack(side="left", padx=5)
            ctk.CTkButton(a_f, text="☝️", width=40, font=("Inter", 14), fg_color=COR_CARD_HIGH, command=lambda aid=a['id']: self.iniciar_registro_digital(aid)).pack(side="left", padx=5)

    def reg_foto_imediata(self, aid):
        # Se o monitor não estiver aberto, abre ele primeiro
        if not self.monitor or not self.monitor.winfo_exists():
            self.saltar_monitor()
            # Dá um pequeno tempo para a câmera inicializar
            self.after(1500, lambda: self.reg_foto_imediata(aid))
            return

        ret, frame = self.monitor.cap.read()
        if ret:
            # Feedback visual de flash
            self.monitor.flash_effect() 
            _, b = cv2.imencode('.jpg', frame)
            b64 = f"data:image/jpeg;base64,{base64.b64encode(b).decode('utf-8')}"
            threading.Thread(target=lambda: requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'foto': b64, 'token': SYNC_TOKEN})).start()
            print(f"[FOTO] Foto capturada e enviada para o aluno ID: {aid}")

    def iniciar_registro_digital(self, aid):
        aluno = next((a for a in self.alunos_data if a['id'] == aid), {'nome': 'Aluno'})
        self.aluno_em_registro = aid
        
        print(f"[CLIQUE] Abrindo painel de cadastro para: {aluno['nome']}")
        
        # Cria Overlay Interno
        if self.overlay_bio: self.overlay_bio.destroy()
        
        self.overlay_bio = ctk.CTkFrame(self, fg_color=COR_BG)
        self.overlay_bio.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        ctk.CTkLabel(self.overlay_bio, text="☝️", font=("Inter", 120)).pack(pady=(150, 20))
        ctk.CTkLabel(self.overlay_bio, text="MODO DE CADASTRO ATIVO", font=("Space Grotesk", 32, "bold"), text_color=COR_PRIMARY).pack()
        ctk.CTkLabel(self.overlay_bio, text=f"ALUNO: {aluno['nome'].upper()}", font=("Inter", 18), text_color=COR_TEXTO).pack(pady=10)
        
        self.lbl_bio_status = ctk.CTkLabel(self.overlay_bio, text="AGUARDANDO DIGITAL NO LEITOR...", font=("Inter", 14, "bold"), text_color=COR_SUCCESS)
        self.lbl_bio_status.pack(pady=40)
        
        ctk.CTkButton(self.overlay_bio, text="CANCELAR REGISTRO (VOLTAR)", fg_color=COR_CARD_HIGH, command=self.fechar_overlay_bio).pack(pady=20)

    def fechar_overlay_bio(self):
        if self.overlay_bio:
            self.overlay_bio.destroy()
            self.overlay_bio = None
        self.aluno_em_registro = None
        self.render_list(self.e_search.get())

    def auto_sync(self): self.carregar_alunos(); self.after(30000, self.auto_sync)
    
    def abrir_catraca(self, s="0"):
        def c():
            try:
                # Protocolo LGU: b"lgu" + b"\x00" (Entrada) ou b"\x01" (Saída) + Mensagem
                msg = "Acesso Liberado" if s == "0" else "Saida Liberada"
                p = b"lgu" + (b"\x00" if s == "0" else b"\x01") + msg.encode('utf-8')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as k:
                    k.settimeout(3)
                    k.connect((CATRACA_IP, CATRACA_PORTA))
                    k.sendall(p)
                    print(f"[CATRACA] Comando de {'ENTRADA' if s=='0' else 'SAIDA'} enviado com sucesso.")
            except Exception as e:
                print(f"[ERRO] Falha ao comunicar com catraca ({CATRACA_IP}:{CATRACA_PORTA}): {e}")
        threading.Thread(target=c, daemon=True).start()

    def remote_polling(self):
        """Verifica se o CRM enviou um comando remoto de abertura (Abri Catraca Agora)"""
        u = f"{SITE_URL}/api/catraca-polling/?token={SYNC_TOKEN}"
        while True:
            try:
                r = requests.get(u, timeout=10)
                if r.status_code == 200:
                    liberacoes = r.json().get('liberacoes', [])
                    for lib in liberacoes:
                        print(f"[REMOTE] Comando de abertura recebido para: {lib.get('nome')}")
                        self.abrir_catraca("0")
            except:
                pass
            time.sleep(POLLING_INTERVAL)

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
        try: 
            requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'digital': tag, 'token': SYNC_TOKEN})
            print(f"[BIO] Sucesso: Digital vinculada ao aluno ID: {aid}")
            if self.overlay_bio:
                self.lbl_bio_status.configure(text="✅ DIGITAL VINCULADA COM SUCESSO!", text_color=COR_SUCCESS)
                self.after(2000, self.fechar_overlay_bio)
        except Exception as e:
            print(f"[BIO] Erro ao vincular: {e}")
            if self.overlay_bio:
                self.lbl_bio_status.configure(text=f"❌ ERRO: {e}", text_color=COR_ERROR)

    def validar(self, tag):
        try:
            r = requests.get(f"{SITE_URL}/api/catraca-check/{tag}/?token={SYNC_TOKEN}").json()
            if r.get('status') != 'vencido': 
                self.abrir_catraca("0")
                if self.monitor and self.monitor.winfo_exists(): self.after(0, lambda: self.monitor.identificar_aluno(r))
        except: pass

if __name__ == "__main__":
    try:
        app = AppRecepcao()
        app.mainloop()
    except Exception as e:
        import traceback
        erro_msg = f"ERRO CRITICO NA INICIALIZACAO:\n{str(e)}\n\n{traceback.format_exc()}"
        print(erro_msg)
        with open("ERRO_SISTEMA.txt", "w", encoding="utf-8") as f:
            f.write(erro_msg)
        input("\nO sistema travou. Pressione ENTER para sair...")
