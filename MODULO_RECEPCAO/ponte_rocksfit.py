import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
import customtkinter as ctk
import sys, requests, socket, threading, time, base64, json, cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
from datetime import datetime

# --- CONFIGURAÇÕES IDENTITY ROCKS FIT ---
SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rocksfit@2024"
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 1001
SERVIDOR_PORTA = 5001 
POLLING_INTERVAL = 3

# Design System Oficial Rocks Fit (High Contrast)
COR_BG = "#050505"
COR_PRIMARY = "#f27121" # Laranja Oficial
COR_CARD = "#121212" 
COR_CARD_HIGH = "#1e1e1e"
COR_TEXTO = "#ffffff"
COR_TEXT_SEC = "#888888"
COR_SUCCESS = "#2ecc71"
COR_ERROR = "#e74c3c"
COR_ACCENT = "#222222"

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

def preparar_imagem_circular(img_pil, size=(280, 280)):
    """ Recorta uma imagem PIL em formato de círculo perfeito """
    img_pil = img_pil.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    draw = Image.new("L", size, 0)
    from PIL import ImageDraw
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + size, fill=255)
    
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(img_pil, (0, 0), mask=mask)
    return result

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
        self.facial_lock = threading.Lock()
        self.cap = None
        self.reset_timer = None # Referência para o timer de limpeza
        
        # Inicia em modo Tela Cheia
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", not self.attributes("-fullscreen")))

        self.tentar_proxima_camera()
        threading.Thread(target=self.loop_camera, daemon=True).start()

    def tentar_proxima_camera(self):
        # No Linux, tentamos uma faixa maior de índices e priorizamos V4L2
        indices = [0, 1, 2, 3, 4]
        print(f"--- INICIANDO BUSCA DE HARDWARE (LINUX) ---")
        
        for idx in indices:
            # Backends para tentar: CAP_V4L2 (Linux), CAP_DSHOW (Windows), CAP_ANY (Padrão)
            for backend in [cv2.CAP_V4L2, cv2.CAP_DSHOW, cv2.CAP_ANY]:
                try:
                    print(f"Tentando Câmera {idx} com backend {backend}...")
                    temp_cap = cv2.VideoCapture(idx, backend)
                    
                    if temp_cap.isOpened():
                        # Testa se realmente consegue ler um frame
                        ret, frame = temp_cap.read()
                        if ret:
                            print(f"✅ Câmera {idx} encontrada e respondendo!")
                            if self.cap:
                                try: self.cap.release()
                                except: pass
                            
                            self.cap = temp_cap
                            # CONFIGURAÇÕES BÁSICAS (DEIXA O HARDWARE CONTROLAR LUZ/FOCO AUTOMATICAMENTE)
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            
                            self.camera_index = idx
                            info_txt = f"CÂMERA ATIVA: ID {idx} (Webcam) | AJUSTE AUTOMÁTICO"
                            self.after(0, lambda: self.lbl_cam_info.configure(text=info_txt))
                            return True
                        else:
                            print(f"⚠️ Câmera {idx} abriu mas não enviou imagem.")
                            temp_cap.release()
                    else:
                        temp_cap.release()
                except Exception as e:
                    print(f"❌ Erro ao tentar câmera {idx}: {e}")
        
        print("🔴 NENHUMA CÂMERA ENCONTRADA")
        return False

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
        self.container.grid_rowconfigure(0, weight=3) # Area da Camera (Maior)
        self.container.grid_rowconfigure(1, weight=1) # Area de Mensagem (Abaixo)
        
        # 1. ÁREA DA CÂMERA (Topo)
        self.cam_f = ctk.CTkFrame(self.container, fg_color=COR_CARD, corner_radius=25, border_width=2, border_color=COR_CARD_HIGH)
        self.cam_f.grid(row=0, column=0, sticky="nsew", pady=(0, 20))
        
        self.lbl_cam = ctk.CTkLabel(self.cam_f, text="", text_color=COR_PRIMARY); self.lbl_cam.pack(expand=True, fill="both")
        self.lbl_cam_info = ctk.CTkLabel(self.cam_f, text="CÂMERA ATIVA", font=("Inter", 12), text_color=COR_TEXT_SEC); self.lbl_cam_info.place(relx=0.03, rely=0.03)

        # 2. PAINEL DE MENSAGEM (Abaixo da Câmera)
        self.info_f = ctk.CTkFrame(self.container, fg_color=COR_CARD, corner_radius=25, border_width=1, border_color=COR_CARD_HIGH)
        self.info_f.grid(row=1, column=0, sticky="nsew")
        
        # Grid Interno do Painel de Mensagem: [Mensagem e Nome (Esq)] [Foto (Dir)]
        self.info_f.grid_columnconfigure(0, weight=1)
        self.info_f.grid_columnconfigure(1, weight=0)
        self.info_f.grid_rowconfigure(0, weight=1)

        # Container de Texto (Mensagem e Nome)
        self.text_f = ctk.CTkFrame(self.info_f, fg_color="transparent")
        self.text_f.grid(row=0, column=0, sticky="nsw", padx=50, pady=30)

        self.lbl_nome = ctk.CTkLabel(self.text_f, text="SISTEMA PRONTO", font=("Space Grotesk", 64, "bold"), text_color=COR_TEXTO, justify="left")
        self.lbl_nome.pack(anchor="w")
        
        self.lbl_status = ctk.CTkLabel(self.text_f, text="APROXIME-SE PARA IDENTIFICAÇÃO", font=("Inter", 38, "bold"), text_color=COR_PRIMARY, justify="left")
        self.lbl_status.pack(anchor="w", pady=(10, 20))

        # Barra de Progresso
        fb = ctk.CTkFrame(self.text_f, height=12, width=600, fg_color=COR_CARD_HIGH, corner_radius=6)
        fb.pack(anchor="w")
        self.bar_fill = ctk.CTkFrame(fb, width=0, height=12, fg_color=COR_PRIMARY, corner_radius=6); self.bar_fill.place(x=0, y=0)

        # Container da Foto (Reduzida na Direita)
        self.avatar_f = ctk.CTkFrame(self.info_f, width=280, height=280, corner_radius=25, fg_color="#050505", border_width=2, border_color=COR_CARD_HIGH)
        self.avatar_f.grid(row=0, column=1, padx=40, pady=30); self.avatar_f.pack_propagate(False)
        self.lbl_aluno_foto = ctk.CTkLabel(self.avatar_f, text="RKS", font=("Inter", 24, "bold"), text_color=COR_CARD_HIGH)
        self.lbl_aluno_foto.pack(expand=True)

        self.lbl_aluno_foto = ctk.CTkLabel(self.avatar_f, text="RKS", font=("Inter", 24, "bold"), text_color=COR_CARD_HIGH)
        self.lbl_aluno_foto.pack(expand=True)

    def loop_camera(self):
        # O hardware ja foi capturado em tentar_proxima_camera() na inicializacao.
        # Caso a captura pare, este loop tentara recuperar.
        falhas_consecutivas = 0
        
        while self.rodando:
            if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    falhas_consecutivas = 0
                    try:
                        frame_ui = frame.copy()
                        frame_ui = cv2.flip(frame_ui, 1) # Espelhar para ficar natural
                        gray = cv2.cvtColor(frame_ui, cv2.COLOR_BGR2GRAY)
                        
                        # Ajuste Automático de Brilho/Contraste (Global e Rápido)
                        gray_balanced = cv2.equalizeHist(gray)
                        
                        faces = []
                        if OPENCV_OK:
                            # Parâmetros Balanceados: Rápido e Fiel
                            faces = FACE_CASCADE.detectMultiScale(
                                gray_balanced,
                                scaleFactor=1.1,       # Velocidade padrão
                                minNeighbors=5,       # Equilíbrio entre precisão e falsos positivos
                                minSize=(100, 100)    # Ignora ruídos distantes
                            )
                            
                        if len(faces) > 0:
                            (x, y, w, h) = faces[0]
                            # Apenas a moldura de foco, sem desfoque de fundo para manter a fluidez
                            cv2.rectangle(frame_ui, (x, y), (x+w, y+h), (242, 113, 33), 2)
                        
                        frame_display = frame_ui

                        if not self.winfo_exists(): break
                        
                        # Obtém tamanho real do container para preencher a tela
                        cw = self.cam_f.winfo_width()
                        ch = self.cam_f.winfo_height()
                        if cw < 300: cw, ch = 800, 600

                        img = Image.fromarray(cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB))
                        
                        # --- PROPORÇÃO PRESERVADA ---
                        img.thumbnail((cw, ch), Image.Resampling.LANCZOS)
                        
                        canvas = Image.new("RGB", (cw, ch), (0, 0, 0))
                        offset = ((cw - img.width) // 2, (ch - img.height) // 2)
                        canvas.paste(img, offset)
                        
                        self.photo = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(cw, ch))
                        
                        if self.lbl_cam.winfo_exists():
                            self.after(0, lambda: self.lbl_cam.configure(image=self.photo, text="") if self.lbl_cam.winfo_exists() else None)

                        # Gatilho de Reconhecimento (Bloqueado se já houver alguém na tela)
                        if len(faces) > 0 and self.face_cooldown <= 0 and self.lbl_nome.cget("text") == "SISTEMA PRONTO":
                            self.face_lock_time += 1
                            if self.face_lock_time == 2:
                                self.after(0, lambda: self.lbl_status.configure(text="🔍 SCANNEANDO...", text_color="#FFF") if self.lbl_status.winfo_exists() else None)
                                # Limpa a foto anterior para sinalizar novo scan
                                self.after(0, lambda: self.lbl_aluno_foto.configure(image=None, text="PROCESSANDO...") if self.lbl_aluno_foto.winfo_exists() else None)
                            
                            if self.face_lock_time >= 3: # Trigger ultra-rápido (aprox 100ms)
                                (x, y, w, h) = faces[0]
                                # Recorta a face com uma pequena margem de segurança (20%)
                                margin = int(w * 0.2)
                                x1, y1 = max(0, x - margin), max(0, y - margin)
                                x2, y2 = min(frame.shape[1], x + w + margin), min(frame.shape[0], y + h + margin)
                                face_roi = frame[y1:y2, x1:x2]
                                
                                self.reconhecer_facial(face_roi) 
                                self.face_cooldown = 80 # Cooldown de 2.5s para evitar loop
                                self.face_lock_time = 0
                        else:
                            if self.face_cooldown > 0: self.face_cooldown -= 1
                            self.face_lock_time = 0
                            
                    except Exception as e:
                        print(f"⚠️ Erro no processamento de frame: {e}")
                else:
                    falhas_consecutivas += 1
                    if falhas_consecutivas > 30:
                        print("⚠️ Perda de sinal persistente. Tentando reconectar...")
                        self.tentar_proxima_camera()
                        falhas_consecutivas = 0
                    time.sleep(0.1)
            else:
                # Câmera desconectada ou erro crítico: tenta recuperar a cada 2 segundos
                print("🔄 Tentando inicializar hardware de vídeo...")
                self.tentar_proxima_camera()
                time.sleep(2)
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
                    # 1. Preparar Frame da Webcam (ROI focado no rosto com Realce de Detalhes)
                    frame_small = cv2.resize(frame, (300, 300))
                    gray_webcam = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
                    
                    # CLAHE: Realce adaptativo de contraste para revelar poros e traços finos
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    gray_webcam = clahe.apply(gray_webcam)
                    
                    # 1000 pontos é o ideal para velocidade/precisão em ROI de rosto
                    orb = cv2.ORB_create(1000)
                    kp_webcam, des_webcam = orb.detectAndCompute(gray_webcam, None)
                    
                    if des_webcam is None: return

                    melhor_aluno = None
                    melhor_score = 0
                    
                    # 2. Comparar com perfis em cache (Busca Linear Otimizada)
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    
                    for matricula, perfil in perfis.items():
                        if perfil['des'] is None: continue
                        try:
                            matches = bf.match(des_webcam, perfil['des'])
                            # Reduzido a distância para 64 (Mais rigoroso que 75)
                            score = len([m for m in matches if m.distance < 64])
                            
                            if score > melhor_score:
                                melhor_score = score
                                melhor_aluno = perfil['data']
                            if melhor_score > 45: break
                        except: continue
                    
                    # 3. Limiar de Decisão Local (Equilíbrio de Precisão 30)
                    if melhor_aluno and melhor_score > 30:
                        print(f"✅ [SUCESSO] Local Match: {melhor_aluno['nome']} (Score: {melhor_score})")
                        try:
                            # Validação no servidor com timeout curto para não travar a interface
                            r = requests.get(f"{SITE_URL}/api/catraca-check/{melhor_aluno['matricula']}/?token={SYNC_TOKEN}", timeout=3)
                            if r.status_code == 200:
                                data = r.json()
                                self.after(0, lambda: self.identificar_aluno(data))
                                # Abre a catraca no sentido retornado pelo servidor
                                sentido = data.get('s', '0')
                                self.after(0, lambda: self.parent.abrir_catraca(sentido))
                            else:
                                # Fallback para dados locais se o servidor der erro mas o rosto conferir
                                print(f"⚠️ Servidor Offline/Erro {r.status_code}, usando Match Local")
                                self.after(0, lambda: self.identificar_aluno(melhor_aluno))
                        except Exception as e:
                            print(f"❌ Erro de conexão: {e}. Liberando por Match Local.")
                            self.after(0, lambda: self.identificar_aluno(melhor_aluno))
                    else:
                        # Feedback de Falha
                        msg_falha = "ROSTO NÃO RECONHECIDO"
                        if melhor_aluno and melhor_score > 15: msg_falha = "MANTENHA O ROSTO PARADO"
                        elif melhor_score < 10: msg_falha = "APROXIME-SE DA CÂMERA"
                        
                        print(f"❌ [FALHA] Score baixo: {melhor_score:.1f}")
                        self.after(0, lambda: self.lbl_status.configure(text=f"❌ {msg_falha}", text_color=COR_ERROR))
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
        # 0. Limpeza Imediata de qualquer resquício anterior
        self.lbl_aluno_foto.configure(image=None, text="CARREGANDO...")
        self.lbl_aluno_foto.image = None
        
        # 1. Atualiza Interface Principal
        self.lbl_nome.configure(text=d.get('nome', 'IDENTIFICADO').upper())
        msg = d.get('mensagem', 'ACESSO LIBERADO').upper()
        self.lbl_status.configure(text=msg, text_color=COR_SUCCESS)
        self.bar_fill.configure(width=300, fg_color=COR_SUCCESS)

        # 2. Gestão de Memória e Reset
        if self.reset_timer:
            self.after_cancel(self.reset_timer)
            self.reset_timer = None
        
        if d.get('foto_url'): 
            threading.Thread(target=self.carregar_foto, args=(d.get('foto_url'),), daemon=True).start()
        
        # 3. Registro de Histórico
        self.parent.adicionar_ao_historico(d)
        
        # 4. Agenda Limpeza Ultra-Rápida para o próximo aluno
        self.reset_timer = self.after(2000, self.reset)

    def reset(self):
        self.reset_timer = None
        self.face_cooldown = 0
        self.face_lock_time = 0
        if self.lbl_nome.winfo_exists():
            self.lbl_nome.configure(text="SISTEMA PRONTO")
            self.lbl_status.configure(text="POSICIONE-SE PARA SCAN", text_color=COR_PRIMARY)
            self.lbl_aluno_foto.configure(image=None, text="AGUARDANDO")
            self.lbl_aluno_foto.image = None # Destrói referência
            self.bar_fill.configure(width=0, fg_color=COR_PRIMARY)

    def carregar_foto(self, url):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                img_pil = Image.open(BytesIO(r.content))
                img_circ = preparar_imagem_circular(img_pil, (280, 280))
                p = ImageTk.PhotoImage(img_circ)
                # Atualização segura na thread principal
                self.after(0, lambda: self._set_foto(p))
        except: pass

    def _set_foto(self, photo):
        # Só aplica a foto se o sistema ainda estiver no modo "IDENTIFICADO"
        # Se já tiver dado reset (SISTEMA PRONTO), não coloca a foto do aluno anterior
        if self.lbl_aluno_foto.winfo_exists() and self.lbl_nome.cget("text") != "SISTEMA PRONTO":
            self.lbl_aluno_foto.configure(image=photo, text="")
            self.lbl_aluno_foto.image = photo

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
        self.alunos_perfis = {} # Inicializa vazio para evitar erro de atributo
        self.historico_acessos = [] # Lista global de acessos
        self.tag_temporaria = None
        self.overlay_bio = None
        
        # Garante pastas de logs local para o CRM
        self.log_path = os.path.join(BASE_DIR, "CONTROLE_ACESSO")
        self.log_alunos_path = os.path.join(self.log_path, "ALUNOS")
        for p in [self.log_path, self.log_alunos_path]:
            if not os.path.exists(p): os.makedirs(p)
        
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
        
        btn_st = {"height": 48, "corner_radius": 12, "font": ("Inter", 13, "bold")}
        ctk.CTkButton(self.sidebar, text="🖥️  MONITORAR", fg_color=COR_PRIMARY, text_color="#000", hover_color="#ff8533", command=self.saltar_monitor, **btn_st).pack(pady=(10, 8), padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="🔄  ATUALIZAR", fg_color=COR_CARD, text_color=COR_TEXTO, border_width=1, border_color=COR_CARD_HIGH, command=self.carregar_alunos, **btn_st).pack(pady=8, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="📑  HISTÓRICO", fg_color=COR_CARD, text_color=COR_TEXTO, border_width=1, border_color=COR_CARD_HIGH, command=self.abrir_historico, **btn_st).pack(pady=8, padx=20, fill="x")
        
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COR_CARD_HIGH).pack(fill="x", pady=20, padx=30)
        
        # Botões de Liberar (Manual)
        ctk.CTkButton(self.sidebar, text="🔓  ENTRADA", fg_color="#1a120b", text_color=COR_PRIMARY, border_width=1, border_color=COR_PRIMARY, command=lambda: self.abrir_catraca("0"), **btn_st).pack(pady=6, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="🔒  SAÍDA", fg_color="#121212", text_color=COR_TEXT_SEC, border_width=1, border_color=COR_CARD_HIGH, command=lambda: self.abrir_catraca("1"), **btn_st).pack(pady=6, padx=20, fill="x")

        # Botão Diagnóstico reposicionado para não sumir
        ctk.CTkButton(self.sidebar, text="⚙️  DIAGNÓSTICO", fg_color="transparent", text_color=COR_TEXT_SEC, hover_color=COR_CARD, command=self.rodar_diagnostico, **btn_st).pack(pady=(20, 0), padx=20, fill="x")

        self.main = ctk.CTkFrame(self, fg_color="transparent"); self.main.pack(side="right", fill="both", expand=True, padx=40, pady=40)
        
        # Busca Rocks Style
        self.search_f = ctk.CTkFrame(self.main, fg_color=COR_CARD, height=65, corner_radius=15, border_width=1, border_color=COR_CARD_HIGH)
        self.search_f.pack(fill="x", pady=(0, 30)); self.search_f.pack_propagate(False)
        self.e_search = ctk.CTkEntry(self.search_f, placeholder_text="PESQUISAR CLIENTE ROCKS FIT...", fg_color="transparent", border_width=0, font=("Inter", 15), text_color=COR_TEXTO)
        self.e_search.pack(fill="both", expand=True, padx=25); self.e_search.bind("<KeyRelease>", lambda e: self.render_list(self.e_search.get()))

        self.sr = ctk.CTkScrollableFrame(self.main, fg_color="transparent"); self.sr.pack(fill="both", expand=True)

    def rodar_diagnostico(self):
        """ Executa diagnóstico INTERNO profissional para manter o sistema limpo """
        diag = ctk.CTkToplevel(self)
        diag.title("DIAGNÓSTICO ROCKS FIT")
        diag.geometry("500x600")
        diag.attributes("-topmost", True)
        diag.configure(fg_color=COR_BG)
        
        ctk.CTkLabel(diag, text="⚙️ DIAGNÓSTICO DE SISTEMA", font=("Space Grotesk", 22, "bold"), text_color=COR_PRIMARY).pack(pady=30)
        
        results_f = ctk.CTkFrame(diag, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_CARD_HIGH); results_f.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        
        def add_line(txt, status="pending"):
            color = COR_TEXT_SEC
            icon = "⏳"
            if status == "ok": color = COR_SUCCESS; icon = "✅"
            if status == "error": color = COR_ERROR; icon = "❌"
            l = ctk.CTkLabel(results_f, text=f"{icon} {txt}", font=("Inter", 16), text_color=color, anchor="w")
            l.pack(fill="x", padx=25, pady=12)
            return l

        l_net = add_line("INTERNET / CONEXÃO"); diag.update()
        try:
            requests.get("https://google.com", timeout=3)
            l_net.configure(text="✅ INTERNET: OK", text_color=COR_SUCCESS)
        except Exception as e: 
            l_net.configure(text=f"❌ INTERNET: {str(e)[:40]}...", text_color=COR_ERROR)

        l_api = add_line("CONEXÃO COM CRM"); diag.update()
        try:
            r = requests.get(f"{SITE_URL}/api/catraca-sync/?token={SYNC_TOKEN}", timeout=3)
            if r.status_code == 200:
                l_api.configure(text=f"✅ CRM ({SITE_URL}): OK", text_color=COR_SUCCESS)
            else:
                l_api.configure(text=f"❌ CRM: ERRO {r.status_code}", text_color=COR_ERROR)
        except Exception as e:
            l_api.configure(text=f"❌ CRM: {str(e)[:40]}...", text_color=COR_ERROR)

        l_board = add_line("PLACA DA CATRACA"); diag.update()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex((CATRACA_IP, CATRACA_PORTA)) == 0:
                    l_board.configure(text=f"✅ PLACA ({CATRACA_IP}): ONLINE", text_color=COR_SUCCESS)
                else:
                    l_board.configure(text="❌ PLACA: SEM RESPOSTA (IP ERRADO?)", text_color=COR_ERROR)
        except Exception as e:
            l_board.configure(text=f"❌ PLACA: {str(e)[:40]}...", text_color=COR_ERROR)

        l_cam = add_line("CÂMERA E HARDWARE"); diag.update()
        try:
            if hasattr(self, 'monitor') and self.monitor and getattr(self.monitor, 'cap', None):
                ret, _ = self.monitor.cap.read()
                if ret:
                    l_cam.configure(text="✅ CÂMERA: OK (IMAGEM CAPTURADA)", text_color=COR_SUCCESS)
                else:
                    l_cam.configure(text="❌ CÂMERA: NO SIGNAL", text_color=COR_ERROR)
            else:
                l_cam.configure(text="❌ CÂMERA: OFFLINE", text_color=COR_ERROR)
        except Exception as e:
            l_cam.configure(text=f"❌ CÂMERA: {str(e)[:40]}...", text_color=COR_ERROR)

        l_bio = add_line("SENSOR BIOMÉTRICO"); diag.update()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(('127.0.0.1', SERVIDOR_PORTA)) == 0:
                    l_bio.configure(text="✅ BIOMETRIA: MONITOR ATIVO", text_color=COR_SUCCESS)
                else:
                    l_bio.configure(text="❌ BIOMETRIA: SERVIDOR OFFLINE", text_color=COR_ERROR)
        except Exception as e:
            l_bio.configure(text=f"❌ BIOMETRIA: {str(e)[:40]}...", text_color=COR_ERROR)

        ctk.CTkButton(diag, text="FECHAR", font=("Inter", 14, "bold"), fg_color=COR_CARD_HIGH, command=diag.destroy).pack(pady=20)

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
                                    # Para processamento ORB (Grayscale)
                                    img_gray = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
                                    # Para exibição na UI (Circular RGB)
                                    img_pil = Image.open(BytesIO(resp.content))
                                    img_ui = preparar_imagem_circular(img_pil, (60, 60))
                                    photo_ctk = ctk.CTkImage(light_image=img_ui, dark_image=img_ui, size=(50, 50))
                                    
                                    if img_gray is not None:
                                        img_gray = cv2.resize(img_gray, (300, 300))
                                        kp, des = orb.detectAndCompute(img_gray, None)
                                        self.alunos_perfis[a['matricula']] = {
                                            'des': des, 
                                            'data': a, 
                                            'photo_ui': photo_ctk
                                        }
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
            
            # Foto do Aluno na Lista (Gestão)
            perfil = self.alunos_perfis.get(a.get('matricula')) if hasattr(self, 'alunos_perfis') else None
            img_list = perfil.get('photo_ui') if perfil and isinstance(perfil, dict) else None
            
            # Formatação Circular e Cor por Status
            is_ativo = "ATIVO" in str(a.get('status','')).upper()
            cor_status = COR_SUCCESS if is_ativo else COR_ERROR
            
            f_img = ctk.CTkFrame(c, width=60, height=60, corner_radius=30, fg_color="#050505", border_width=2, border_color=cor_status)
            f_img.pack(side="left", padx=15); f_img.pack_propagate(False)
            
            if img_list:
                ctk.CTkLabel(f_img, image=img_list, text="").pack(expand=True)
            else:
                ctk.CTkLabel(f_img, text="👤", font=("Inter", 24)).pack(expand=True)
            
            # Formatação de Data e Dias (Padrão BR)
            venc_formated = "N/A"
            venc_raw = a.get('vencimento')
            if venc_raw:
                try:
                    dt = datetime.strptime(venc_raw, '%Y-%m-%d')
                    venc_formated = dt.strftime('%d/%m/%y')
                except: venc_formated = str(venc_raw)
            
            dias = a.get('dias_restantes', 0)
            txt_venc = f"VENC: {venc_formated} | {dias} DIAS"
            
            # Texto Principal
            lbl_n = ctk.CTkLabel(c, text=a.get('nome','').upper()[:30], font=("Inter", 14, "bold"), text_color=COR_TEXTO)
            lbl_n.place(x=95, y=25)
            
            lbl_v = ctk.CTkLabel(c, text=txt_venc, font=("Inter", 11, "bold"), text_color=COR_TEXT_SEC)
            lbl_v.place(x=95, y=50)
            
            af = ctk.CTkFrame(c, fg_color="transparent"); af.pack(side="right", padx=15)
            
            # Lógica Condicional: Só libera câmera se não tiver foto
            tem_foto = True if a.get('foto_url') else False
            btn_foto_st = {"state": "disabled", "fg_color": "#1a1a1a"} if tem_foto else {"fg_color": COR_CARD_HIGH}
            
            ctk.CTkButton(af, text="📸", width=42, height=42, hover_color=COR_PRIMARY, command=lambda aid=a['id']: self.reg_foto_imediata(aid), **btn_foto_st).pack(side="left", padx=4)
            ctk.CTkButton(af, text="☝️", width=42, height=42, fg_color=COR_CARD_HIGH, hover_color=COR_PRIMARY, command=lambda aid=a['id']: self.iniciar_registro_digital(aid)).pack(side="left", padx=4)

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
        """ Versao Final Blindada: Tenta Porta 1001 (Wireshark) com fallback para 3000/5000 """
        def c():
            # Lista de portas em ordem de probabilidade
            portas_teste = [1001, 3000, 5000]
            comando = b"lgu\x00Liberou Entrada" if s == "0" else b"lgu\x01Liberou Saida"
            
            for pta in portas_teste:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(2) # Timeout curto para busca rapida
                        sock.connect((CATRACA_IP, pta))
                        sock.sendall(comando)
                        sock.recv(1024) # Confirmacao
                        print(f"✅ [SUCESSO] Catraca aberta na porta {pta}")
                        return # SUCESSO! Sai do loop
                except:
                    continue # Tenta a proxima porta
            
            print(f"❌ [FALHA TOTAL] Nenhuma porta (1001, 3000, 5000) respondeu no IP {CATRACA_IP}")
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

    def adicionar_ao_historico(self, d):
        sentido = d.get('s', '0') # 0: Entrada, 1: Saída
        registro = {
            'hora': time.strftime("%H:%M:%S"),
            'nome': d.get('nome', 'ALUNO').upper(),
            'status': "LIBERADO" if d.get('status') in ['ativo', 'alerta', 'liberado'] else "BLOQUEADO",
            'tipo': "ENTRADA" if str(sentido) == "0" else "SAÍDA"
        }
        self.historico_acessos.insert(0, registro) 
        if len(self.historico_acessos) > 50: self.historico_acessos.pop()
        
        # Salva no arquivo de LOG local
        self.salvar_log_local(d, sentido)

    def salvar_log_local(self, d, sentido):
        try:
            agora_dt = datetime.now()
            hoje = agora_dt.strftime("%d-%m-%Y")
            agora = agora_dt.strftime("%H:%M:%S")
            nome = d.get('nome', 'N/D').upper()
            matricula = d.get('matricula', 'N/D')
            tipo = "ENTRADA" if str(sentido) == "0" else "SAÍDA"
            
            linha = f"[{agora}] {tipo} | {matricula} - {nome}\n"
            linha_crm = f"{agora};{tipo};{matricula};{nome}\n"
            
            # 1. Log Diário Geral (.txt para o CRM)
            arquivo_geral = os.path.join(self.log_path, f"DIARIO_{hoje}.txt")
            with open(arquivo_geral, "a", encoding="utf-8") as f:
                f.write(linha)
                
            # 2. Log Individual do Aluno (Específico em .txt)
            if matricula != "N/D":
                arquivo_indiv = os.path.join(self.log_alunos_path, f"{matricula}.txt")
                with open(arquivo_indiv, "a", encoding="utf-8") as f:
                    f.write(f"{hoje} {agora} - {tipo}\n")
            
            # Bip de Confirmação (Cross-platform)
            self.emitir_bip()
                    
        except Exception as e:
            print(f"⚠️ Erro ao salvar log local: {e}")

    def emitir_bip(self):
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(1000, 250)
            else:
                sys.stdout.write('\a')
                sys.stdout.flush()
        except: pass

    def abrir_historico(self):
        hwin = ctk.CTkToplevel(self)
        hwin.title("HISTÓRICO DE ACESSOS - ROCKS FIT")
        hwin.geometry("500x700")
        hwin.attributes("-topmost", True)
        hwin.configure(fg_color=COR_BG)
        
        ctk.CTkLabel(hwin, text="📑 HISTÓRICO RECENTE", font=("Space Grotesk", 20, "bold"), text_color=COR_PRIMARY).pack(pady=20)
        
        frame = ctk.CTkScrollableFrame(hwin, fg_color=COR_CARD, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        if not self.historico_acessos:
            ctk.CTkLabel(frame, text="NENHUM ACESSO REGISTRADO", font=("Inter", 12), text_color=COR_TEXT_SEC).pack(pady=40)
        
        for reg in self.historico_acessos:
            cor = COR_SUCCESS if reg['status'] == "LIBERADO" else COR_ERROR
            item = ctk.CTkFrame(frame, fg_color="#080808", height=60, corner_radius=10)
            item.pack(fill="x", pady=4, padx=5); item.pack_propagate(False)
            ctk.CTkLabel(item, text=f"{reg['hora']} - {reg['nome']}\n{reg['status']}", font=("Inter", 11, "bold"), text_color=cor, justify="left").pack(side="left", padx=15)

    def auto_sync(self): self.carregar_alunos(); self.after(300000, self.auto_sync)

if __name__ == "__main__":
    try:
        app = AppRecepcao()
        app.mainloop()
    except Exception as e:
        with open("ERRO_SISTEMA.txt", "w", encoding="utf-8") as f: f.write(str(e))
