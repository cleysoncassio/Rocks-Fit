import customtkinter as ctk
import os, sys, requests, socket, threading, time, base64, json, cv2
from PIL import Image, ImageTk
from io import BytesIO

# --- CONFIGURAÇÕES IDENTITY ROCKS FIT ---
SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rocksfit@2024"
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 3000
SERVIDOR_PORTA = 5000
POLLING_INTERVAL = 3

# Design System Oficial Rocks Fit (High Contrast)
COR_BG = "#000000"
COR_PRIMARY = "#f27121" # Laranja Oficial
COR_CARD = "#111111" 
COR_CARD_HIGH = "#222222"
COR_TEXTO = "#ffffff"
COR_TEXT_SEC = "#a0a0a0"
COR_SUCCESS = "#4caf50"
COR_ERROR = "#f44336"

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
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    OPENCV_OK = True
except: OPENCV_OK = False

# --- UI COMPONENTS ---

class JanelaMonitor(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SCANNER ROCKS FIT")
        self.geometry("1024x768"); self.configure(fg_color=COR_BG)
        self.parent = parent; self.rodando = True
        self.setup_ui()
        if OPENCV_OK:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            threading.Thread(target=self.loop_camera, daemon=True).start()

    def setup_ui(self):
        # Header Laranja
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=100)
        self.header.pack(fill="x", padx=40, pady=(40, 0))
        ctk.CTkLabel(self.header, text="ROCKS", font=("Space Grotesk", 52, "bold"), text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(self.header, text="FIT", font=("Space Grotesk", 52, "bold"), text_color=COR_PRIMARY).pack(side="left", padx=5)
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40, pady=40)
        
        # Câmera com Borda Laranja
        self.cam_f = ctk.CTkFrame(self.container, width=640, height=480, fg_color=COR_CARD, corner_radius=15, border_width=2, border_color=COR_PRIMARY)
        self.cam_f.pack(side="left", fill="both", expand=True); self.cam_f.pack_propagate(False)
        self.lbl_cam = ctk.CTkLabel(self.cam_f, text="SENSORES ATIVOS", text_color=COR_PRIMARY, font=("Inter", 14, "bold")); self.lbl_cam.pack(expand=True)

        # Painel Lateral
        self.info_f = ctk.CTkFrame(self.container, width=320, fg_color="transparent")
        self.info_f.pack(side="right", fill="both", padx=(40, 0))
        
        self.avatar_f = ctk.CTkFrame(self.info_f, width=280, height=280, corner_radius=20, fg_color=COR_CARD, border_width=1, border_color=COR_CARD_HIGH)
        self.avatar_f.pack(pady=(0, 30)); self.avatar_f.pack_propagate(False)
        self.lbl_aluno_foto = ctk.CTkLabel(self.avatar_f, text="AGUARDANDO", font=("Inter", 14, "bold"), text_color=COR_TEXT_SEC); self.lbl_aluno_foto.pack(expand=True)
        
        self.lbl_nome = ctk.CTkLabel(self.info_f, text="SISTEMA PRONTO", font=("Space Grotesk", 36, "bold"), text_color=COR_TEXTO, wraplength=300, justify="left"); self.lbl_nome.pack(anchor="w")
        self.lbl_status = ctk.CTkLabel(self.info_f, text="POSICIONE-SE PARA SCAN", font=("Inter", 12, "bold"), text_color=COR_PRIMARY); self.lbl_status.pack(anchor="w", pady=10)
        
        fb = ctk.CTkFrame(self.info_f, height=2, fg_color=COR_CARD_HIGH); fb.pack(fill="x", pady=20)
        self.bar_fill = ctk.CTkFrame(fb, width=0, height=2, fg_color=COR_PRIMARY); self.bar_fill.place(x=0, y=0)

    def loop_camera(self):
        while self.rodando:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((640, 480))
                self.photo = ImageTk.PhotoImage(img)
                self.after(0, lambda: self.lbl_cam.configure(image=self.photo, text=""))
            time.sleep(0.01)

    def flash_effect(self):
        self.cam_f.configure(border_color="#ffffff")
        self.after(100, lambda: self.cam_f.configure(border_color=COR_PRIMARY))

    def identificar_aluno(self, d):
        self.lbl_nome.configure(text=d.get('nome', 'IDENTIFICADO').upper())
        self.lbl_status.configure(text="ACESSO LIBERADO", text_color=COR_SUCCESS)
        self.bar_fill.configure(width=300, fg_color=COR_SUCCESS)
        if d.get('foto_url'): threading.Thread(target=self.carregar_foto, args=(d.get('foto_url'),), daemon=True).start()
        threading.Timer(5, self.reset).start()

    def reset(self):
        self.lbl_nome.configure(text="SISTEMA PRONTO")
        self.lbl_status.configure(text="POSICIONE-SE PARA SCAN", text_color=COR_PRIMARY)
        self.lbl_aluno_foto.configure(image=None, text="AGUARDANDO"); self.bar_fill.configure(width=0, fg_color=COR_PRIMARY)

    def carregar_foto(self, url):
        try:
            r = requests.get(url, timeout=5)
            i = Image.open(BytesIO(r.content)).resize((280, 280), Image.Resampling.LANCZOS)
            p = ImageTk.PhotoImage(i); self.lbl_aluno_foto.configure(image=p, text=""); self.lbl_aluno_foto.image = p
        except: pass

    def fechar(self):
        self.rodando = False
        if OPENCV_OK: self.cap.release()
        self.destroy()

class AppRecepcao(ctk.CTk):
    def __init__(self):
        super().__init__()
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except: pass

        self.title("ROCKS FIT - GESTOR")
        self.geometry("1100x850"); self.configure(fg_color=COR_BG)
        self.monitor = None; self.alunos_data = []; self.aluno_em_registro = None
        self.tag_temporaria = None
        self.overlay_bio = None
        
        self.setup_ui()
        threading.Thread(target=self.servidor_bio, daemon=True).start()
        threading.Thread(target=self.remote_polling, daemon=True).start()
        self.carregar_alunos()
        self.after(30000, self.auto_sync)

    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=260, fg_color="#050505", corner_radius=0); self.sidebar.pack(side="left", fill="y")
        
        # Logo Rocks Fit
        self.logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_f.pack(pady=50)
        ctk.CTkLabel(self.logo_f, text="ROCKS", font=("Space Grotesk", 32, "bold"), text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(self.logo_f, text="FIT", font=("Space Grotesk", 32, "bold"), text_color=COR_PRIMARY).pack(side="left", padx=2)
        
        btn_st = {"height": 55, "corner_radius": 10, "font": ("Inter", 13, "bold")}
        ctk.CTkButton(self.sidebar, text="🖥️ MONITORAR", fg_color=COR_PRIMARY, text_color="#000", hover_color="#ff8533", command=self.saltar_monitor, **btn_st).pack(pady=10, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="🔄 ATUALIZAR", fg_color=COR_CARD, text_color=COR_TEXTO, border_width=1, border_color=COR_CARD_HIGH, command=self.carregar_alunos, **btn_st).pack(pady=10, padx=25, fill="x")
        
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COR_CARD_HIGH).pack(fill="x", pady=25, padx=40)
        ctk.CTkButton(self.sidebar, text="🔓 LIBERAR ENTRADA", fg_color="#1a1a1a", text_color=COR_PRIMARY, border_width=1, border_color=COR_PRIMARY, command=lambda: self.abrir_catraca("0"), **btn_st).pack(pady=10, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="🔒 LIBERAR SAÍDA", fg_color="#1a1a1a", text_color=COR_TEXT_SEC, border_width=1, border_color=COR_CARD_HIGH, command=lambda: self.abrir_catraca("1"), **btn_st).pack(pady=10, padx=25, fill="x")

        self.main = ctk.CTkFrame(self, fg_color="transparent"); self.main.pack(side="right", fill="both", expand=True, padx=40, pady=40)
        
        # Busca Rocks Style
        self.search_f = ctk.CTkFrame(self.main, fg_color=COR_CARD, height=65, corner_radius=15, border_width=1, border_color=COR_CARD_HIGH)
        self.search_f.pack(fill="x", pady=(0, 30)); self.search_f.pack_propagate(False)
        self.e_search = ctk.CTkEntry(self.search_f, placeholder_text="PESQUISAR CLIENTE ROCKS FIT...", fg_color="transparent", border_width=0, font=("Inter", 15), text_color=COR_TEXTO)
        self.e_search.pack(fill="both", expand=True, padx=25); self.e_search.bind("<KeyRelease>", lambda e: self.render_list(self.e_search.get()))

        self.sr = ctk.CTkScrollableFrame(self.main, fg_color="transparent"); self.sr.pack(fill="both", expand=True)

    def saltar_monitor(self):
        if not self.monitor or not self.monitor.winfo_exists(): self.monitor = JanelaMonitor(self)
        else: self.monitor.lift()

    def carregar_alunos(self):
        u = f"{SITE_URL}/api/aluno-list-full/?token={SYNC_TOKEN}"
        def f():
            try:
                r = requests.get(u, timeout=12)
                if r.status_code == 200:
                    self.alunos_data = r.json().get('alunos', [])
                    self.after(0, self.mostrar_todos)
            except: pass
        threading.Thread(target=f, daemon=True).start()

    def mostrar_todos(self): self.render_list("")

    def render_list(self, filter_text=""):
        for w in self.sr.winfo_children(): w.destroy()
        data = [a for a in self.alunos_data if filter_text.lower() in str(a.get('nome','')).lower()] if filter_text else self.alunos_data
        for a in data[:10]:
            st_c = COR_PRIMARY if "ATIVO" in str(a.get('status','')).upper() else COR_CARD_HIGH
            c = ctk.CTkFrame(self.sr, fg_color=COR_CARD, height=90, corner_radius=15); c.pack(fill="x", pady=6, padx=10); c.pack_propagate(False)
            
            # Círculo Laranja Rocks
            f_status = ctk.CTkFrame(c, width=12, height=12, corner_radius=6, fg_color=st_c)
            f_status.pack(side="left", padx=25)
            
            lbl = ctk.CTkLabel(c, text=f"{a.get('nome','').upper()[:35]}\nMAT: {a.get('matricula','---')} - {a.get('status','').upper()}", font=("Inter", 13, "bold"), justify="left", text_color=COR_TEXTO)
            lbl.pack(side="left", padx=5)
            
            af = ctk.CTkFrame(c, fg_color="transparent"); af.pack(side="right", padx=20)
            ctk.CTkButton(af, text="📸", width=45, height=45, fg_color=COR_CARD_HIGH, hover_color=COR_PRIMARY, command=lambda aid=a['id']: self.reg_foto_imediata(aid)).pack(side="left", padx=5)
            ctk.CTkButton(af, text="☝️", width=45, height=45, fg_color=COR_CARD_HIGH, hover_color=COR_PRIMARY, command=lambda aid=a['id']: self.iniciar_registro_digital(aid)).pack(side="left", padx=5)

    def iniciar_registro_digital(self, aid):
        aluno = next((a for a in self.alunos_data if a['id'] == aid), {'nome': 'Aluno'})
        self.aluno_em_registro = aid
        self.tag_temporaria = None # Limpa leitura anterior
        
        if self.overlay_bio: self.overlay_bio.destroy()
        self.overlay_bio = ctk.CTkFrame(self, fg_color=COR_BG); self.overlay_bio.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        ctk.CTkLabel(self.overlay_bio, text="REGISTRO BIOMÉTRICO", font=("Space Grotesk", 32, "bold"), text_color=COR_PRIMARY).pack(pady=(80, 10))
        ctk.CTkLabel(self.overlay_bio, text=aluno['nome'].upper(), font=("Inter", 18, "bold"), text_color=COR_TEXTO).pack()
        
        # Grade de 4 Quadrados
        self.grid_f = ctk.CTkFrame(self.overlay_bio, fg_color="transparent")
        self.grid_f.pack(pady=40)
        self.quadros = []
        for i in range(4):
            q = ctk.CTkFrame(self.grid_f, width=100, height=130, fg_color=COR_CARD, border_width=2, border_color=COR_CARD_HIGH, corner_radius=10)
            q.pack(side="left", padx=10); q.pack_propagate(False)
            ctk.CTkLabel(q, text=f"{i+1}", font=("Inter", 24, "bold"), text_color=COR_CARD_HIGH).pack(expand=True)
            self.quadros.append(q)
            
        self.lbl_bio_status = ctk.CTkLabel(self.overlay_bio, text="POSICIONE O DEDO NO LEITOR...", font=("Inter", 14, "bold"), text_color=COR_TEXT_SEC)
        self.lbl_bio_status.pack(pady=10)
        
        self.btn_salvar_bio = ctk.CTkButton(self.overlay_bio, text="💾 SALVAR BIOMETRIA", state="disabled", fg_color=COR_CARD_HIGH, text_color=COR_TEXT_SEC, width=300, height=60, font=("Inter", 16, "bold"), command=self.confirmar_salvamento_bio)
        self.btn_salvar_bio.pack(pady=20)
        
        ctk.CTkButton(self.overlay_bio, text="CANCELAR", fg_color="transparent", text_color=COR_ERROR, command=self.fechar_overlay_bio).pack()

    def fechar_overlay_bio(self):
        if self.overlay_bio: self.overlay_bio.destroy(); self.overlay_bio = None
        self.aluno_em_registro = None; self.tag_temporaria = None; self.mostrar_todos()

    def vincular_bio_interface(self, tag):
        """ Chamado quando o leitor envia dados durante o modo de registro """
        self.tag_temporaria = tag
        # Animação dos 4 quadros
        for i, q in enumerate(self.quadros):
            self.after(i*150, lambda q=q: q.configure(fg_color=COR_PRIMARY, border_color=COR_PRIMARY))
        
        self.lbl_bio_status.configure(text="LEITURA CONCLUÍDA! CLIQUE EM SALVAR.", text_color=COR_SUCCESS)
        self.btn_salvar_bio.configure(state="normal", fg_color=COR_PRIMARY, text_color="#000")

    def confirmar_salvamento_bio(self):
        if self.aluno_em_registro and self.tag_temporaria:
            aid = self.aluno_em_registro
            tag = self.tag_temporaria
            try:
                r = requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'digital': tag, 'token': SYNC_TOKEN})
                if r.status_code == 200:
                    self.lbl_bio_status.configure(text="✅ BIOMETRIA SALVA COM SUCESSO!", text_color=COR_SUCCESS)
                    self.after(2000, self.fechar_overlay_bio)
            except:
                self.lbl_bio_status.configure(text="❌ ERRO AO SALVAR NO SERVIDOR", text_color=COR_ERROR)

    def reg_foto_imediata(self, aid):
        if not self.monitor or not self.monitor.winfo_exists(): self.saltar_monitor(); self.after(1500, lambda: self.reg_foto_imediata(aid)); return
        ret, frame = self.monitor.cap.read()
        if ret:
            self.monitor.flash_effect()
            _, b = cv2.imencode('.jpg', frame); b64 = f"data:image/jpeg;base64,{base64.b64encode(b).decode('utf-8')}"
            threading.Thread(target=lambda: requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'foto': b64, 'token': SYNC_TOKEN})).start()

    def servidor_bio(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sv:
            sv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sv.bind(('0.0.0.0', SERVIDOR_PORTA)); sv.listen(5)
            while True:
                conn, _ = sv.accept()
                with conn:
                    raw = conn.recv(1024).decode('utf-8', errors='ignore')
                    if raw:
                        tag = raw.split('|')[1] if '|' in raw else raw.strip()
                        if self.aluno_em_registro: self.vincular_bio_interface(tag)
                        else: self.validar(tag)

    def validar(self, tag):
        try:
            r = requests.get(f"{SITE_URL}/api/catraca-check/{tag}/?token={SYNC_TOKEN}").json()
            if r.get('status') != 'vencido': 
                self.abrir_catraca("0")
                if self.monitor and self.monitor.winfo_exists(): self.after(0, lambda: self.monitor.identificar_aluno(r))
        except: pass

    def abrir_catraca(self, s="0"):
        def c():
            try:
                p = b"lgu" + (b"\x00" if s == "0" else b"\x01") + ("ACESSO ROCKS FIT" if s == "0" else "SAIDA ROCKS FIT").encode('utf-8')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as k:
                    k.settimeout(3); k.connect((CATRACA_IP, CATRACA_PORTA)); k.sendall(p)
            except: pass
        threading.Thread(target=c, daemon=True).start()

    def remote_polling(self):
        u = f"{SITE_URL}/api/catraca-polling/?token={SYNC_TOKEN}"
        while True:
            try:
                r = requests.get(u, timeout=10)
                if r.status_code == 200:
                    for lib in r.json().get('liberacoes', []): self.abrir_catraca("0")
            except: pass
            time.sleep(POLLING_INTERVAL)

    def auto_sync(self): self.carregar_alunos(); self.after(30000, self.auto_sync)

if __name__ == "__main__":
    try:
        app = AppRecepcao()
        app.mainloop()
    except Exception as e:
        with open("ERRO_SISTEMA.txt", "w", encoding="utf-8") as f: f.write(str(e))
