import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
import customtkinter as ctk
import sys, requests, socket, threading, time, base64, json, cv2
import numpy as np
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
        os.path.join(BASE_DIR, "media", "imagens", os.path.basename(nome_relativo)),
        os.path.join(BASE_DIR, "media", "images", os.path.basename(nome_relativo)),
        os.path.join(BASE_DIR, "media", os.path.basename(nome_relativo)),
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
        self.camera_index = 1 # Começa tentando a externa
        self.face_cooldown = 0
        self.face_lock_time = 0
        self.last_crop_rect = None # [x1, y1, x2, y2]
        self.zoom_persistence = 0
        self.facial_lock = threading.Lock()
        
        # Inicia em modo Tela Cheia
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", not self.attributes("-fullscreen")))

        self.tentar_proxima_camera()
        threading.Thread(target=self.loop_camera, daemon=True).start()

    def tentar_proxima_camera(self):
        # Tenta os índices 1, 0, 2
        indices = [1, 0, 2]
        for idx in indices:
            print(f"Buscando hardware no index {idx}...")
            # Tenta com e sem CAP_DSHOW para compatibilidade máxima
            for backend in [cv2.CAP_ANY, cv2.CAP_DSHOW]:
                temp_cap = cv2.VideoCapture(idx, backend)
                if temp_cap.isOpened():
                    if hasattr(self, 'cap') and self.cap:
                        try: self.cap.release()
                        except: pass
                    
                    self.cap = temp_cap
                    # Tenta configurar, mas ignora se falhar (alguns drivers não aceitam)
                    try:
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    except: pass
                    
                    self.camera_index = idx
                    self.after(0, lambda: self.lbl_cam_info.configure(text=f"CÂMERA ATIVA: ID {idx} {'(USB)' if idx > 0 else '(PC)'}"))
                    return True
                else:
                    temp_cap.release()
        return False

    def alternar_camera(self):
        proximo = (self.camera_index + 1) % 3
        print(f"Alternando para hardware {proximo}...")
        
        # Tenta os backends no novo índice
        sucesso = False
        for backend in [cv2.CAP_ANY, cv2.CAP_DSHOW]:
            temp_cap = cv2.VideoCapture(proximo, backend)
            if temp_cap.isOpened():
                if hasattr(self, 'cap') and self.cap:
                    try: self.cap.release()
                    except: pass
                
                self.cap = temp_cap
                try:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                except: pass
                
                self.camera_index = proximo
                self.after(0, lambda: self.lbl_cam_info.configure(text=f"CÂMERA ATIVA: ID {proximo} {'(USB)' if proximo > 0 else '(PC)'}"))
                sucesso = True
                break
            else:
                temp_cap.release()
        
        if not sucesso:
            self.tentar_proxima_camera()

    def setup_ui(self):
        # Header Laranja com Logomarca
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        self.header.pack(fill="x", padx=40, pady=(20, 0))
        
        try:
            logo_img = Image.open(CAMINHO_LOGO)
            logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(100, 100))
            ctk.CTkLabel(self.header, image=logo_ctk, text="").pack(side="left", padx=(0, 20))
        except: pass

        ctk.CTkLabel(self.header, text="ROCKS", font=("Space Grotesk", 48, "bold"), text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(self.header, text="FIT", font=("Space Grotesk", 48, "bold"), text_color=COR_PRIMARY).pack(side="left", padx=5)
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40, pady=(20, 40))
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=0, minsize=450)
        self.container.grid_rowconfigure(0, weight=1)
        
        # Área da Câmera
        self.cam_f = ctk.CTkFrame(self.container, fg_color=COR_CARD, corner_radius=20, border_width=2, border_color=COR_PRIMARY)
        self.cam_f.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        
        self.lbl_cam = ctk.CTkLabel(self.cam_f, text="", text_color=COR_PRIMARY); self.lbl_cam.pack(expand=True, fill="both")
        
        # Overlay ID
        self.lbl_cam_info = ctk.CTkLabel(self.cam_f, text="CÂMERA: ID --", font=("Inter", 14), text_color=COR_TEXT_SEC)
        self.lbl_cam_info.place(relx=0.03, rely=0.03)

        # Botão Alternar
        self.btn_switch = ctk.CTkButton(self.cam_f, text="🔄 ALTERNAR CÂMERA", width=220, height=55, fg_color=COR_CARD_HIGH, text_color=COR_TEXTO, font=("Inter", 14, "bold"), corner_radius=15, command=self.alternar_camera)
        self.btn_switch.place(relx=0.5, rely=0.92, anchor="center")

        # Painel Lateral
        self.info_f = ctk.CTkFrame(self.container, width=450, fg_color="transparent")
        self.info_f.grid(row=0, column=1, sticky="nsew")
        self.info_f.grid_propagate(False)
        
        ctk.CTkLabel(self.info_f, text="FOTO DO ALUNO", font=("Inter", 18, "bold"), text_color=COR_TEXT_SEC).pack(anchor="w", pady=(0, 10))
        self.avatar_f = ctk.CTkFrame(self.info_f, width=410, height=410, corner_radius=25, fg_color=COR_CARD, border_width=1, border_color=COR_CARD_HIGH)
        self.avatar_f.pack(pady=(0, 30)); self.avatar_f.pack_propagate(False)
        self.lbl_aluno_foto = ctk.CTkLabel(self.avatar_f, text="AGUARDANDO", font=("Inter", 24, "bold"), text_color=COR_TEXT_SEC); self.lbl_aluno_foto.pack(expand=True)
        
        self.lbl_nome = ctk.CTkLabel(self.info_f, text="SISTEMA PRONTO", font=("Space Grotesk", 56, "bold"), text_color=COR_TEXTO, wraplength=430, justify="left"); self.lbl_nome.pack(anchor="w")
        self.lbl_status = ctk.CTkLabel(self.info_f, text="POSICIONE-SE PARA SCAN", font=("Inter", 32, "bold"), text_color=COR_PRIMARY, wraplength=430, justify="left"); self.lbl_status.pack(anchor="w", pady=20)
        
        fb = ctk.CTkFrame(self.info_f, height=10, fg_color=COR_CARD_HIGH, corner_radius=5); fb.pack(fill="x", pady=20)
        self.bar_fill = ctk.CTkFrame(fb, width=0, height=10, fg_color=COR_PRIMARY, corner_radius=5); self.bar_fill.place(x=0, y=0)

    def loop_camera(self):
        # O hardware ja foi capturado em tentar_proxima_camera() na inicializacao.
        # Caso a capturade pare, este loop tentara recuperar.
        
        while self.rodando:
            if hasattr(self, 'cap') and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    try:
                        frame_ui = frame.copy()
                        frame_ui = cv2.flip(frame_ui, 1) # Espelhar para ficar natural
                        gray = cv2.cvtColor(frame_ui, cv2.COLOR_BGR2GRAY)
                        faces = []
                        if OPENCV_OK:
                            # Ajuste de escala e vizinhos para ambiente de academia (luz variada)
                            faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 4)
                            
                        # --- LÓGICA DE FOCO SUAVE (SMOOTH ZOOM) ---
                        if len(faces) > 0:
                            (x, y, w, h) = faces[0]
                            pad_w, pad_h = int(w*0.6), int(h*0.6)
                            x1, y1 = max(0, x-pad_w), max(0, y-pad_h)
                            x2, y2 = min(frame_ui.shape[1], x+w+pad_w), min(frame_ui.shape[0], y+h+pad_h)
                            self.last_crop_rect = (x1, y1, x2, y2)
                            self.zoom_persistence = 20
                            cv2.rectangle(frame_ui, (x, y), (x+w, y+h), (242, 113, 33), 2)
                        
                        if self.zoom_persistence > 0 and self.last_crop_rect:
                            x1, y1, x2, y2 = self.last_crop_rect
                            frame_display = frame_ui[y1:y2, x1:x2]
                            self.zoom_persistence -= 1
                        else:
                            frame_display = frame_ui
                            self.last_crop_rect = None

                        if not self.winfo_exists(): break
                        
                        # Obtém tamanho real do container para preencher a tela
                        cw = self.cam_f.winfo_width()
                        ch = self.cam_f.winfo_height()
                        if cw < 300: cw, ch = 800, 600

                        img = Image.fromarray(cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB))
                        
                        # --- PROPORÇÃO PRESERVADA ---
                        # Calcula o redimensionamento mantendo o aspect ratio
                        img.thumbnail((cw, ch), Image.Resampling.LANCZOS)
                        
                        # Cria fundo preto para centralizar se houver sobra (Letterboxing)
                        canvas = Image.new("RGB", (cw, ch), (0, 0, 0))
                        offset = ((cw - img.width) // 2, (ch - img.height) // 2)
                        canvas.paste(img, offset)
                        
                        self.photo = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(cw, ch))
                        
                        if self.lbl_cam.winfo_exists():
                            self.after(0, lambda: self.lbl_cam.configure(image=self.photo, text="") if self.lbl_cam.winfo_exists() else None)

                        # Gatilho de Reconhecimento
                        if len(faces) > 0 and self.face_cooldown <= 0:
                            self.face_lock_time += 1
                            if self.face_lock_time == 5:
                                self.after(0, lambda: self.lbl_status.configure(text="🔍 ANALISANDO ROSTO...", text_color="#FFF") if self.lbl_status.winfo_exists() else None)
                            if self.face_lock_time > 12:
                                self.reconhecer_facial(frame)
                                self.face_cooldown = 100
                                self.face_lock_time = 0
                        else:
                            if self.face_cooldown > 0: self.face_cooldown -= 1
                            self.face_lock_time = 0
                            
                    except Exception as e:
                        print(f"⚠️ Erro no processamento de frame: {e}")
                else:
                    # Falha na leitura: tenta recuperar hardware se persistir
                    time.sleep(0.1)
            else:
                time.sleep(1) # Câmera desconectada ou erro crítico
            time.sleep(0.033) # Estabiliza em ~30 FPS

    def reconhecer_facial(self, frame):
        """ Executa o reconhecimento LOCAL para velocidade máxima (< 1s) """
        # Busca o cache na JanelaPrincipal (parent)
        perfis = getattr(self.parent, 'alunos_perfis', {})
        if not perfis:
            return

        if hasattr(self, 'facial_lock') and self.facial_lock.locked():
            return

        def f():
            with self.facial_lock:
                try:
                    print("🔍 [FACIAL LOCAL] Analisando...")
                    start_time = time.time()
                    
                    # 1. Preparar Frame da Webcam
                    gray_webcam = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray_webcam = cv2.equalizeHist(gray_webcam)
                    
                    orb = cv2.ORB_create(1000)
                    kp_webcam, des_webcam = orb.detectAndCompute(gray_webcam, None)
                    
                    if des_webcam is None: return

                    melhor_aluno = None
                    melhor_score = 0
                    
                    # 2. Comparar com perfis em cache
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    
                    for matricula, perfil in perfis.items():
                        if perfil['des'] is None: continue
                        try:
                            matches = bf.match(des_webcam, perfil['des'])
                            score = len([m for m in matches if m.distance < 75])
                            
                            if score > melhor_score:
                                melhor_score = score
                                melhor_aluno = perfil['data']
                        except: continue

                    duration = time.time() - start_time
                    
                    # 3. Limiar de Decisão Local
                    if melhor_aluno and melhor_score > 18:
                        print(f"✅ [SUCESSO] Local Match: {melhor_aluno['nome']} (Score: {melhor_score}) em {duration:.2f}s")
                        try:
                            r = requests.get(f"{SITE_URL}/api/catraca-check/{melhor_aluno['matricula']}/?token={SYNC_TOKEN}", timeout=5)
                            data = r.json() if r.status_code in [200, 403] else {}
                            
                            if r.status_code == 200:
                                sentido = data.get('s', '0')
                                self.after(0, lambda: self.identificar_aluno(data))
                                self.after(0, lambda: self.parent.abrir_catraca(sentido))
                            elif r.status_code == 403:
                                # Aluno bloqueado ou erro administrativo - ainda assim mostramos no painel
                                self.after(0, lambda: self.identificar_aluno(data))
                            else:
                                print(f"⚠️ Servidor retornou {r.status_code}")
                                self.after(0, lambda: self.lbl_status.configure(text="❌ ERRO NO SERVIDOR", text_color=COR_ERROR))
                        except Exception as e:
                            print(f"❌ Erro de rede ao validar: {e}")
                    else:
                        msg = "ROSTO NÃO RECONHECIDO"
                        if melhor_score < 10: msg = "APROXIME-SE DA CÂMERA"
                        print(f"❌ [FALHA] Match local insuficiente (Score: {melhor_score:.1f})")
                        self.after(0, lambda: self.lbl_status.configure(text=f"❌ {msg}", text_color=COR_ERROR))
                        self.after(2000, self.reset)
                except Exception as e:
                    print(f"⚠️ Erro no reconhecimento local: {e}")
                
                # Garantir pausa após cada tentativa para não floodar
                time.sleep(1)
        threading.Thread(target=f, daemon=True).start()

    def flash_effect(self):
        self.cam_f.configure(border_color="#ffffff")
        self.after(100, lambda: self.cam_f.configure(border_color=COR_PRIMARY))

    def identificar_aluno(self, d):
        self.lbl_nome.configure(text=d.get('nome', 'IDENTIFICADO').upper())
        # Exibe a mensagem personalizada vinda do servidor (Aniversário, Boas Vindas, etc)
        msg = d.get('mensagem', 'ACESSO LIBERADO').upper()
        self.lbl_status.configure(text=msg, text_color=COR_SUCCESS)
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
        self.after(300000, self.auto_sync)

    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=260, fg_color="#050505", corner_radius=0); self.sidebar.pack(side="left", fill="y")
        
        # Logo Rocks Fit (Image + Text)
        self.logo_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_f.pack(pady=40)
        
        # Tenta carregar a imagem da logomarca
        try:
            logo_img = Image.open(CAMINHO_LOGO)
            # Redimensiona mantendo proporção ou força um tamanho fixo
            logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(60, 60))
            self.lbl_logo_img = ctk.CTkLabel(self.logo_f, image=logo_ctk, text="")
            self.lbl_logo_img.pack(pady=(0, 10))
        except Exception as e:
            print(f"Erro ao carregar logomarca: {e}")

        ctk.CTkLabel(self.logo_f, text="ROCKS", font=("Space Grotesk", 28, "bold"), text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(self.logo_f, text="FIT", font=("Space Grotesk", 28, "bold"), text_color=COR_PRIMARY).pack(side="left", padx=2)
        
        btn_st = {"height": 55, "corner_radius": 10, "font": ("Inter", 13, "bold")}
        ctk.CTkButton(self.sidebar, text="🖥️ MONITORAR", fg_color=COR_PRIMARY, text_color="#000", hover_color="#ff8533", command=self.saltar_monitor, **btn_st).pack(pady=10, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="🔄 ATUALIZAR", fg_color=COR_CARD, text_color=COR_TEXTO, border_width=1, border_color=COR_CARD_HIGH, command=self.carregar_alunos, **btn_st).pack(pady=10, padx=25, fill="x")
        
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COR_CARD_HIGH).pack(fill="x", pady=25, padx=40)
        ctk.CTkButton(self.sidebar, text="🔓 LIBERAR ENTRADA", fg_color="#1a1a1a", text_color=COR_PRIMARY, border_width=1, border_color=COR_PRIMARY, command=lambda: self.abrir_catraca("0"), **btn_st).pack(pady=10, padx=25, fill="x")
        ctk.CTkButton(self.sidebar, text="🔒 LIBERAR SAÍDA", fg_color="#1a1a1a", text_color=COR_TEXT_SEC, border_width=1, border_color=COR_CARD_HIGH, command=lambda: self.abrir_catraca("1"), **btn_st).pack(pady=10, padx=25, fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COR_CARD_HIGH).pack(fill="x", pady=15, padx=40)
        
        # Indicador de Fluxo
        self.flow_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.flow_f.pack(pady=10, padx=25, fill="x")
        ctk.CTkLabel(self.flow_f, text="FLUXO ATUAL:", font=("Inter", 11, "bold"), text_color=COR_TEXT_SEC).pack(side="left")
        self.lbl_flow_status = ctk.CTkLabel(self.flow_f, text="CARREGANDO...", font=("Inter", 11, "bold"), text_color=COR_PRIMARY)
        self.lbl_flow_status.pack(side="right")

        ctk.CTkButton(self.sidebar, text="⚙️ DIAGNÓSTICO", fg_color="transparent", text_color=COR_TEXT_SEC, hover_color=COR_CARD, command=self.rodar_diagnostico, **btn_st).pack(pady=0, padx=25, fill="x")

        self.main = ctk.CTkFrame(self, fg_color="transparent"); self.main.pack(side="right", fill="both", expand=True, padx=40, pady=40)
        
        # Busca Rocks Style
        self.search_f = ctk.CTkFrame(self.main, fg_color=COR_CARD, height=65, corner_radius=15, border_width=1, border_color=COR_CARD_HIGH)
        self.search_f.pack(fill="x", pady=(0, 30)); self.search_f.pack_propagate(False)
        self.e_search = ctk.CTkEntry(self.search_f, placeholder_text="PESQUISAR CLIENTE ROCKS FIT...", fg_color="transparent", border_width=0, font=("Inter", 15), text_color=COR_TEXTO)
        self.e_search.pack(fill="both", expand=True, padx=25); self.e_search.bind("<KeyRelease>", lambda e: self.render_list(self.e_search.get()))

        self.sr = ctk.CTkScrollableFrame(self.main, fg_color="transparent"); self.sr.pack(fill="both", expand=True)

    def rodar_diagnostico(self):
        script = os.path.join(BASE_DIR, "centro_diagnostico.py")
        if os.path.exists(script):
            import subprocess
            threading.Thread(target=lambda: subprocess.run([sys.executable, script], creationflags=0x00000010 if os.name == 'nt' else 0), daemon=True).start()

    def saltar_monitor(self):
        if not self.monitor or not self.monitor.winfo_exists(): self.monitor = JanelaMonitor(self)
        else: self.monitor.lift()

    def carregar_alunos(self):
        u = f"{SITE_URL}/api/catraca-sync/?token={SYNC_TOKEN}"
        def f():
            try:
                print("📡 Sincronizando Perfis e Fotos...")
                r = requests.get(u, timeout=15)
                if r.status_code == 200:
                    self.alunos_data = r.json().get('alunos', [])
                    self.settings = r.json().get('settings', {})
                    
                    # Atualiza o indicador de fluxo na UI
                    fluxo_traducao = {
                        'ENTRADA': 'APENAS ENTRADA',
                        'SAIDA': 'APENAS SAÍDA',
                        'BIDIRECIONAL': 'AUTO (ENTRADA/SAÍDA)'
                    }
                    fluxo_txt = fluxo_traducao.get(self.settings.get('fluxo'), 'DESCONHECIDO')
                    self.after(0, lambda: self.lbl_flow_status.configure(text=fluxo_txt))

                    self.alunos_perfis = {} # Cache centralizado aqui na JanelaPrincipal
                    orb = cv2.ORB_create(1000)
                    
                    for a in self.alunos_data:
                        furl = a.get('foto_url')
                        if furl:
                            try:
                                # Se a URL for relativa, completa com o domínio
                                if furl.startswith('/'): furl = f"{SITE_URL}{furl}"
                                
                                resp = requests.get(furl, timeout=7)
                                if resp.status_code == 200:
                                    nparr = np.frombuffer(resp.content, np.uint8)
                                    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                                    if img is not None:
                                        img = cv2.resize(img, (300, 300))
                                        kp, des = orb.detectAndCompute(img, None)
                                        self.alunos_perfis[a['matricula']] = {'des': des, 'data': a}
                                        print(f"💾 Foto Cache: {a['nome']}")
                            except Exception as e: 
                                print(f"⚠️ Erro foto {a['nome']}: {e}")
                            
                    print(f"✅ Sync Finalizado. {len(self.alunos_perfis)} rostos em memória.")
                    self.after(0, self.mostrar_todos)
            except Exception as e:
                print(f"❌ Erro na sync: {e}")
        threading.Thread(target=f, daemon=True).start()

    def mostrar_todos(self): self.render_list("")

    def render_list(self, filter_text=""):
        for w in self.sr.winfo_children(): w.destroy()
        # Filtra apenas alunos ATIVOS para visualização no monitor principal
        data = [a for a in self.alunos_data if "ATIVO" in str(a.get('status','')).upper()]
        if filter_text:
            data = [a for a in data if filter_text.lower() in str(a.get('nome','')).lower()]
        
        for a in data[:20]:
            st_c = COR_PRIMARY if "ATIVO" in str(a.get('status','')).upper() else COR_CARD_HIGH
            c = ctk.CTkFrame(self.sr, fg_color=COR_CARD, height=90, corner_radius=15); c.pack(fill="x", pady=6, padx=10); c.pack_propagate(False)
            
            # Círculo Laranja Rocks
            f_status = ctk.CTkFrame(c, width=12, height=12, corner_radius=6, fg_color=st_c)
            f_status.pack(side="left", padx=25)
            
            dias = a.get('dias_restantes', 0)
            cor_dias = COR_SUCCESS if dias > 0 else COR_ERROR
            txt_dias = f"{dias} DIAS RESTANTES" if dias > 0 else "PLANO VENCIDO"
            
            lbl = ctk.CTkLabel(c, text=f"{a.get('nome','').upper()[:35]}\n{txt_dias}", font=("Inter", 13, "bold"), justify="left", text_color=cor_dias)
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
            # SEGURANÇA: Só libera se o status for explicitamente 'ativo' ou 'alerta'
            if r.get('status') in ['ativo', 'alerta', 'liberado']: 
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

    def auto_sync(self): self.carregar_alunos(); self.after(300000, self.auto_sync)

if __name__ == "__main__":
    try:
        app = AppRecepcao()
        app.mainloop()
    except Exception as e:
        with open("ERRO_SISTEMA.txt", "w", encoding="utf-8") as f: f.write(str(e))
