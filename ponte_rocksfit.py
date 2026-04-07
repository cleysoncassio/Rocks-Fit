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

# --- 🚀 GESTÃO ROCKS FIT v2.9.3 ---
SITE_URL = "http://192.168.0.102:8000"       # IP da rede local (Linux -> Windows)
SYNC_TOKEN = "rocksfit@2024"                 
CATRACA_IP = "169.254.37.150"              
CATRACA_PORTA = 1001                       
SERVIDOR_PORTA = 5000                      

# --- 📂 DETECÇÃO INTELIGENTE DE CAMINHOS (MÚLTIPLOS FALLBACKS) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = os.path.expanduser("~")  # C:\Users\ccs no Windows, /home/ccs no Linux

def _encontrar_arquivo(nome_relativo, fallbacks_extras=None):
    """Tenta múltiplos caminhos para encontrar um arquivo crítico."""
    candidatos = [
        os.path.join(BASE_DIR, nome_relativo),
        os.path.join(HOME_DIR, nome_relativo),
        os.path.join(os.getcwd(), nome_relativo),
        os.path.join("/home/ccs/Modelos/Rocks-Fit", nome_relativo),
    ]
    if fallbacks_extras:
        candidatos.extend(fallbacks_extras)
    for c in candidatos:
        if os.path.exists(c):
            print(f"[PATH] Encontrado: {c}")
            return c
    print(f"[PATH] NÃO ENCONTRADO: {nome_relativo}")
    for c in candidatos:
        print(f"  Tentei: {c}")
    return candidatos[0]

CAMINHO_CACHE = _encontrar_arquivo(os.path.join("rks-catraca", "alunos_local.json"))
CAMINHO_LOGO  = _encontrar_arquivo(os.path.join("media", "images", "rkslogo.png"))

# Paleta Cinza Chumbo Premium
COR_BG = "#333333"         
COR_CARD = "#2A2A2A"       
COR_TEXTO = "#FFFFFF"      
COR_LARANJA = "#FF9500"    
COR_TEXT_SEC = "#AAAAAA"   

try:
    import cv2
    OPENCV_OK = True
    # Carregar classificador de faces (Padrão OpenCV)
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except:
    OPENCV_OK = False

ctk.set_appearance_mode("dark") 

class JanelaMonitor(ctk.CTkToplevel):
    """ TELA DO ALUNO: COM CÂMERA E IDENTIFICAÇÃO (FACE ID) """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Módulo de Identificação - Rocks Fit")
        self.geometry("1000x800")
        self.configure(fg_color=COR_LARANJA)
        self.parent = parent
        self.rodando = True
        self.setup_ui()
        if OPENCV_OK:
            self.cap = cv2.VideoCapture(0)
            threading.Thread(target=self.loop_camera, daemon=True).start()

    def setup_ui(self):
        # Logo Superior
        try:
            self.logo_mon = ctk.CTkImage(Image.open(CAMINHO_LOGO), size=(120, 120))
            ctk.CTkLabel(self, image=self.logo_mon, text="").pack(pady=10)
        except:
            ctk.CTkLabel(self, text="ROCKS FIT", font=("Impact", 36), text_color="white").pack(pady=10)

        ctk.CTkLabel(self, text="CENTRAL DE IDENTIFICAÇÃO BIOMÉTRICA", font=("Impact", 28), text_color="white").pack(pady=5)

        # Container Principal
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=30, pady=10)

        # Área da Câmera (Esquerda)
        self.cam_f = ctk.CTkFrame(self.container, width=640, height=480, fg_color="black", corner_radius=20, border_width=5, border_color="white")
        self.cam_f.pack(side="left", padx=10, fill="both", expand=True)
        self.cam_f.pack_propagate(False)
        self.lbl_cam = ctk.CTkLabel(self.cam_f, text="INICIANDO CÂMERA...", text_color="white", font=("Arial", 18))
        self.lbl_cam.pack(expand=True)

        # Área de Info (Direita)
        self.info_f = ctk.CTkFrame(self.container, width=300, fg_color="transparent")
        self.info_f.pack(side="right", fill="both", padx=10)

        self.card_foto = ctk.CTkFrame(self.info_f, width=220, height=220, corner_radius=110, border_width=5, border_color="white", fg_color="white")
        self.card_foto.pack(pady=20); self.card_foto.pack_propagate(False)
        self.lbl_aluno_foto = ctk.CTkLabel(self.card_foto, text="👤", font=("Arial", 100), text_color="#CCC")
        self.lbl_aluno_foto.pack(expand=True)

        self.lbl_nome = ctk.CTkLabel(self.info_f, text="AGUARDANDO...", font=("Arial", 28, "bold"), text_color="white", wraplength=280)
        self.lbl_nome.pack(pady=10)
        
        self.lbl_status = ctk.CTkLabel(self.info_f, text="APROXIME-SE PARA VALIDAR", font=("Arial", 16), text_color="#EEE")
        self.lbl_status.pack()

    def loop_camera(self):
        while self.rodando:
            ret, frame = self.cap.read()
            if ret:
                # Detecção de Face (Efeito Visual)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 4)
                
                for (x, y, w, h) in faces:
                    # Desenha o quadrado "Face ID" (Verde neon)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 255, 50), 3)
                    # Texto indicativo
                    cv2.putText(frame, "SCANEANDO...", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2)

                # Converter para imagem do CTk
                img = Image.fromarray(cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)).resize((640, 480))
                self.photo = ImageTk.PhotoImage(img)
                self.after(0, lambda: self.lbl_cam.configure(image=self.photo, text=""))
            time.sleep(0.03)

    def indentificar_aluno(self, d):
        self.lbl_nome.configure(text=d.get('nome', 'ALUNO').upper())
        self.lbl_status.configure(text="LIBERADO COM SUCESSO!", text_color="#00FF00")
        if d.get('foto_url'): threading.Thread(target=self.carregar_foto, args=(d.get('foto_url'),), daemon=True).start()
        threading.Timer(6, self.reset).start()

    def carregar_foto(self, url):
        try:
            r = requests.get(url, timeout=5)
            i = Image.open(BytesIO(r.content)).resize((220, 220), Image.Resampling.LANCZOS)
            p = ImageTk.PhotoImage(i); self.lbl_aluno_foto.configure(image=p, text=""); self.lbl_aluno_foto.image = p
        except: pass

    def reset(self):
        self.lbl_nome.configure(text="AGUARDANDO...")
        self.lbl_status.configure(text="APROXIME-SE PARA VALIDAR", text_color="#EEE")
        self.lbl_aluno_foto.configure(image=None, text="👤")

    def fechar(self):
        self.rodando = False
        if OPENCV_OK: self.cap.release()
        self.destroy()

class JanelaGestao(ctk.CTkToplevel):
    def __init__(self, parent, aluno):
        super().__init__(parent)
        self.aluno = aluno; self.parent = parent
        self.title("Perfil do Aluno")
        self.geometry("400x500"); self.configure(fg_color=COR_BG)
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text=self.aluno['nome'].upper(), font=("Arial", 18, "bold"), text_color=COR_LARANJA, wraplength=350).pack(pady=30)
        ctk.CTkLabel(self, text=f"STATUS: {self.aluno['status']}", text_color="green" if "ATIVO" in self.aluno['status'] else "red").pack()
        
        ctk.CTkButton(self, text="📸 REGISTRAR FOTO", fg_color="#555", command=self.reg_foto).pack(pady=20, padx=50, fill="x")
        ctk.CTkButton(self, text="☝️ VINCULAR DIGITAL", fg_color="#555", command=self.reg_bio).pack(pady=5, padx=50, fill="x")

    def reg_foto(self):
        # Captura o frame que está rodando no monitor agora
        if self.parent.monitor and self.parent.monitor.winfo_exists():
            ret, frame = self.parent.monitor.cap.read()
            if ret:
                _, b = cv2.imencode('.jpg', frame)
                b64 = f"data:image/jpeg;base64,{base64.b64encode(b).decode('utf-8')}"
                self.parent.salva_foto_api(self.aluno['id'], b64)
        self.destroy()

    def reg_bio(self): self.parent.iniciar_registro_digital(self.aluno['id']); self.destroy()

class JanelaConfiguracoes(ctk.CTkToplevel):
    """ PAINEL DE TESTES E DIAGNÓSTICO """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Configurações e Testes de Hardware")
        self.geometry("600x500")
        self.configure(fg_color=COR_BG)
        self.rodando_cam = False
        self.setup_ui()

    def setup_ui(self):
        self.tabs = ctk.CTkTabview(self, segmented_button_selected_color=COR_LARANJA)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tc = self.tabs.add(" 🗄️ CATRACA ")
        self.tm = self.tabs.add(" 📸 CÂMERA ")
        self.tb = self.tabs.add(" ☝️ BIOMETRIA ")

        # --- TESTE CATRACA ---
        ctk.CTkLabel(self.tc, text="PAINEL DE COMANDO DA CATRACA", font=("Arial", 14, "bold")).pack(pady=20)
        ctk.CTkButton(self.tc, text="TESTAR PULSO ENTRADA", fg_color="green", command=lambda: self.parent.abrir_catraca("0")).pack(pady=5)
        ctk.CTkButton(self.tc, text="TESTAR PULSO SAÍDA", fg_color="#555", command=lambda: self.parent.abrir_catraca("1")).pack(pady=5)
        self.lbl_status_rede = ctk.CTkLabel(self.tc, text=f"IP Alvo: {CATRACA_IP}:{CATRACA_PORTA}", text_color="gray")
        self.lbl_status_rede.pack(pady=20)

        # --- TESTE CÂMERA ---
        self.f_cam = ctk.CTkFrame(self.tm, width=320, height=240, fg_color="black")
        self.f_cam.pack(pady=10); self.f_cam.pack_propagate(False)
        self.lbl_test_cam = ctk.CTkLabel(self.f_cam, text="CÂMERA DESATIVADA")
        self.lbl_test_cam.pack(expand=True)
        self.btn_cam = ctk.CTkButton(self.tm, text="ATIVAR PREVIEW TESTE", command=self.toggle_cam)
        self.btn_cam.pack(pady=10)

        # --- TESTE BIOMETRIA ---
        ctk.CTkLabel(self.tb, text="LOG DE RECEBIMENTO BRUTO (PORTA 5000)", font=("Arial", 12, "bold")).pack(pady=10)
        self.txt_bio = ctk.CTkTextbox(self.tb, fg_color="#111", text_color="lime", height=200)
        self.txt_bio.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.tb, text="Aproxime uma TAG ou Dedo para testar o sinal.", text_color="gray").pack()

    def toggle_cam(self):
        if self.parent.monitor and self.parent.monitor.winfo_exists():
            self.lbl_test_cam.configure(text="FECHE O MONITOR DO ALUNO\nPARA TESTAR AQUI")
            return
        
        if not self.rodando_cam:
            self.rodando_cam = True
            self.cap_test = cv2.VideoCapture(0)
            self.btn_cam.configure(text="DESATIVAR PREVIEW", fg_color="red")
            threading.Thread(target=self.loop_test_cam, daemon=True).start()
        else:
            self.rodando_cam = False
            self.btn_cam.configure(text="ATIVAR PREVIEW TESTE", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            if hasattr(self, 'cap_test'): self.cap_test.release()
            self.lbl_test_cam.configure(image=None, text="CÂMERA DESATIVADA")

    def loop_test_cam(self):
        while self.rodando_cam:
            ret, frame = self.cap_test.read()
            if ret:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((320, 240))
                p = ImageTk.PhotoImage(img)
                self.after(0, lambda: self.lbl_test_cam.configure(image=p, text=""))
                self.after(0, lambda: setattr(self, 'photo_test', p))
            time.sleep(0.05)

    def log_raw_bio(self, data):
        self.txt_bio.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] RECV: {data}\n")
        self.txt_bio.see("end")

    def fechar(self):
        self.rodando_cam = False
        if hasattr(self, 'cap_test'): self.cap_test.release()
        self.destroy()

class AppRecepcao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ROCKS FIT GESTOR v2.9.3")
        self.geometry("1100x850"); self.configure(fg_color=COR_BG)
        self.monitor = None; self.janela_config = None; self.alunos_data = []; self.aluno_em_registro = None
        
        # --- [DIAGNÓSTICO v2.9.3] ---
        print(f"\n[DIAG] BASE_DIR: {BASE_DIR}")
        print(f"[DIAG] LOGO EXISTE: {os.path.exists(CAMINHO_LOGO)}")
        print(f"[DIAG] CACHE EXISTE: {os.path.exists(CAMINHO_CACHE)}")
        
        self.setup_ui()
        
        # Carregamento Síncrono Inicial (Garante que a lista apareça antes da API responder)
        if os.path.exists(CAMINHO_CACHE):
            try:
                with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
                    self.alunos_data = json.load(f).get('alunos', [])
                print(f"[DIAG] Alunos Carregados do Cache: {len(self.alunos_data)}")
                self.render_list()
                self.after(0, lambda: self.lbl_sync_status.configure(text=f"📂 OFFLINE | CACHE: {len(self.alunos_data)} ALUNOS", text_color="orange"))
            except Exception as e:
                print(f"[DIAG] Erro ao carregar cache síncrono: {e}")

        threading.Thread(target=self.servidor_bio, daemon=True).start()
        self.carregar_alunos()
        self.after(30000, self.auto_sync)

    def setup_ui(self):
        # Header com Grid Responsivo
        self.header = ctk.CTkFrame(self, height=100, fg_color=COR_CARD, corner_radius=0)
        self.header.pack(fill="x")
        self.header.grid_columnconfigure(0, weight=1) # Espaço do Logo
        self.header.grid_columnconfigure(1, weight=0) # Espaço dos Botões
        
        # 🟢 COLUNA 0: LOGO (ALINHADO À ESQUERDA)
        self.logo_f = ctk.CTkFrame(self.header, fg_color="transparent")
        self.logo_f.grid(row=0, column=0, sticky="w", padx=30, pady=10)
        try:
            self.logo_img = ctk.CTkImage(Image.open(CAMINHO_LOGO), size=(60, 60))
            ctk.CTkLabel(self.logo_f, image=self.logo_img, text="").pack(side="left")
        except:
            ctk.CTkLabel(self.logo_f, text="ROCKS FIT", font=("Impact", 36), text_color=COR_LARANJA).pack(side="left")

        # 🔵 COLUNA 1: BOTÕES (ALINHADO À DIREITA)
        self.btn_f = ctk.CTkFrame(self.header, fg_color="transparent")
        self.btn_f.grid(row=0, column=1, sticky="e", padx=20, pady=10)
        
        # Configuração dos botões compactos
        btn_opts = {"width": 110, "height": 40, "font": ("Arial", 11, "bold")}
        
        ctk.CTkButton(self.btn_f, text="🖥️ MONITOR", fg_color=COR_LARANJA, text_color="white", command=self.saltar_monitor, **btn_opts).pack(side="right", padx=3)
        ctk.CTkButton(self.btn_f, text="🔄 SYNC", fg_color="#444", command=self.carregar_alunos, **btn_opts).pack(side="right", padx=3)
        ctk.CTkButton(self.btn_f, text="🔒 SAÍDA", fg_color="#555", command=lambda: self.abrir_catraca("1"), **btn_opts).pack(side="right", padx=3)
        ctk.CTkButton(self.btn_f, text="🔓 ENTRADA", fg_color="green", command=lambda: self.abrir_catraca("0"), **btn_opts).pack(side="right", padx=3)
        ctk.CTkButton(self.btn_f, text="⚙️ CONFIG", fg_color="#555", width=90, height=40, font=("Arial", 11, "bold"), command=self.abrir_config).pack(side="right", padx=3)

        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_selected_color=COR_LARANJA)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=10)
        self.tab_g = self.tabs.add("  GESTÃO DE USUÁRIOS  ")
        self.tab_l = self.tabs.add("  LOGS DE ACESSO  ")

        # Busca e Lista
        self.gestao_f = ctk.CTkFrame(self.tab_g, fg_color="transparent")
        self.gestao_f.pack(fill="both", expand=True)
        
        self.e_search = ctk.CTkEntry(self.gestao_f, placeholder_text="Pesquisar por Nome ou CPF...", height=45); self.e_search.pack(fill="x", pady=10)
        self.e_search.bind("<KeyRelease>", lambda e: self.render_list(self.e_search.get()))
        self.sr = ctk.CTkScrollableFrame(self.gestao_f, fg_color="#1A1A1A"); self.sr.pack(fill="both", expand=True)

        self.area_log = ctk.CTkTextbox(self.tab_l, fg_color="#111", text_color="cyan"); self.area_log.pack(fill="both", expand=True)

        # Footer Status
        self.footer = ctk.CTkFrame(self, height=30, fg_color="#222")
        self.footer.pack(fill="x", side="bottom")
        self.lbl_sync_status = ctk.CTkLabel(self.footer, text="📡 AGUARDANDO SINCRONIZAÇÃO...", font=("Arial", 10), text_color="gray")
        self.lbl_sync_status.pack(side="left", padx=20)

    def saltar_monitor(self):
        if self.monitor and self.monitor.winfo_exists(): self.monitor.fechar()
        self.monitor = JanelaMonitor(self)

    def abrir_config(self):
        if self.janela_config and self.janela_config.winfo_exists(): self.janela_config.lift()
        else: self.janela_config = JanelaConfiguracoes(self)


    def carregar_alunos(self):
        u = f"{SITE_URL}/api/aluno-list-full/?token={SYNC_TOKEN}"

        # Feedback imediato na lista
        self.after(0, self._status_lista, "⏳ Sincronizando com o servidor...", "cyan")

        def f():
            # --- Tenta via API ---
            try:
                print(f"[SYNC] Tentando API: {u}")
                r = requests.get(u, timeout=10)
                print(f"[SYNC] Resposta: HTTP {r.status_code}")
                if r.status_code == 200:
                    dados = r.json().get('alunos', [])
                    self.alunos_data = dados
                    n = len(dados)
                    print(f"[SYNC] OK! {n} alunos carregados via API.")
                    self.after(0, lambda: self.lbl_sync_status.configure(
                        text=f"📡 ONLINE | {n} ALUNOS", text_color="lime"))
                    self.after(0, self.mostrar_todos)
                    return
                else:
                    self.after(0, self._status_lista, f"API retornou erro {r.status_code}", "red")
            except Exception as e:
                print(f"[SYNC] API falhou: {type(e).__name__}: {e}")
                self.after(0, self._status_lista,
                           f"Servidor offline: {type(e).__name__}\nTentando cache local...", "orange")

            # --- Fallback: Arquivo Local ---
            try:
                existe = os.path.exists(CAMINHO_CACHE)
                print(f"[SYNC] Cache path: {CAMINHO_CACHE}")
                print(f"[SYNC] Cache existe: {existe}")
                if existe:
                    with open(CAMINHO_CACHE, 'r', encoding='utf-8') as fl:
                        dados = json.load(fl).get('alunos', [])
                    self.alunos_data = dados
                    n = len(dados)
                    print(f"[SYNC] OFFLINE: {n} alunos do cache.")
                    self.after(0, lambda: self.lbl_sync_status.configure(
                        text=f"📂 OFFLINE | CACHE: {n} ALUNOS", text_color="orange"))
                    self.after(0, self.mostrar_todos)
                else:
                    msg = f"⚠️ Cache não encontrado!\n{CAMINHO_CACHE}"
                    print(f"[SYNC] {msg}")
                    self.after(0, self._status_lista, msg, "red")
                    self.after(0, lambda: self.lbl_sync_status.configure(
                        text="⚠️ CACHE NÃO ENCONTRADO", text_color="red"))
            except Exception as e2:
                msg = f"❌ Erro: {type(e2).__name__}: {e2}"
                print(f"[SYNC] {msg}")
                self.after(0, self._status_lista, msg, "red")

        threading.Thread(target=f, daemon=True).start()

    def _status_lista(self, msg, cor="gray"):
        """Exibe uma mensagem de status centralizada na lista de alunos"""
        for w in self.sr.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.sr, text=msg, font=("Arial", 13),
                     text_color=cor, wraplength=600).pack(pady=80)

    def mostrar_todos(self):
        """Limpa o filtro e exibe todos os alunos"""
        self.e_search.delete(0, ctk.END)
        self.render_list(filter="")


    def render_list(self, filter=None):
        # Sempre lê o campo de busca atual se filter não for especificado
        if filter is None:
            filter = self.e_search.get().strip()
        for w in self.sr.winfo_children(): w.destroy()
        encontrados = 0
        for a in self.alunos_data:
            if filter.lower() in a['nome'].lower() or filter in a['cpf']:
                encontrados += 1

                # Cor da borda pela API ou pelo status textual
                borda_cor_api = a.get('borda_cor', '')
                if borda_cor_api == 'verde':
                    st_c = "#00C853"
                elif borda_cor_api == 'laranja':
                    st_c = "#FF9500"
                else:
                    st_c = "#FF3B30"
                if not borda_cor_api:
                    st_c = "#00C853" if "ATIVO" in a['status'] else "#FF3B30"

                c = ctk.CTkFrame(self.sr, fg_color=COR_CARD, height=90, corner_radius=10,
                                 border_width=2, border_color=st_c)
                c.pack(fill="x", pady=5, padx=10); c.pack_propagate(False)
                c.bind("<Button-1>", lambda e, alu=a: JanelaGestao(self, alu)); c.configure(cursor="hand2")

                # Barra lateral de status
                ctk.CTkFrame(c, width=8, fg_color=st_c).pack(side="left", fill="y")

                # Foto do aluno com borda colorida
                foto_f = ctk.CTkFrame(c, width=70, height=70, fg_color=st_c, corner_radius=35)
                foto_f.pack(side="left", padx=(10, 5), pady=10)
                foto_f.pack_propagate(False)
                try:
                    foto_url = a.get('foto_url')
                    if foto_url:
                        import io
                        resp_foto = requests.get(foto_url, timeout=2)
                        img = Image.open(io.BytesIO(resp_foto.content)).resize((62, 62))
                        imgtk = ctk.CTkImage(img, size=(62, 62))
                        lbl_img = ctk.CTkLabel(foto_f, image=imgtk, text="")
                        lbl_img.image = imgtk
                        lbl_img.place(relx=0.5, rely=0.5, anchor="center")
                    else:
                        ctk.CTkLabel(foto_f, text="📷", font=("Arial", 22)).place(relx=0.5, rely=0.5, anchor="center")
                except:
                    ctk.CTkLabel(foto_f, text="📷", font=("Arial", 22)).place(relx=0.5, rely=0.5, anchor="center")

                # Texto do aluno
                nome_formatado = a['nome'].upper()[:22] + ("..." if len(a['nome']) > 22 else "")
                txt = f"{nome_formatado}\nMAT: {a['matricula']} | VENC: {a['vencimento']}"
                lbl = ctk.CTkLabel(c, text=txt, font=("Arial", 12, "bold"), text_color="white", justify="left")
                lbl.pack(side="left", padx=10)
                lbl.bind("<Button-1>", lambda e, alu=a: JanelaGestao(self, alu))

                # Status badge
                ctk.CTkLabel(c, text=a['status'], font=("Arial", 10, "bold"),
                             text_color=st_c).pack(side="right", padx=15)

        if encontrados == 0:
            ctk.CTkLabel(self.sr, text="NENHUM ALUNO NA LISTA\n(Verifique a conexão ou filtro de busca)",
                         font=("Arial", 14), text_color="gray").pack(pady=100)


    def auto_sync(self): self.carregar_alunos(); self.after(30000, self.auto_sync)

    def abrir_catraca(self, s="0"):
        def c():
            try:
                p = b"lgu" + (b"\x00" if s == "0" else b"\x01") + b"Liberou Acesso"
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as k:
                    k.settimeout(3); k.connect((CATRACA_IP, CATRACA_PORTA)); k.sendall(p); time.sleep(0.4)
            except: pass
        threading.Thread(target=c, daemon=True).start()

    def escrever(self, m, cor="cyan"): self.area_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n"); self.area_log.see("end")

    def salva_foto_api(self, aid, b64):
        threading.Thread(target=lambda: requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'foto': b64, 'token': SYNC_TOKEN}, timeout=10)).start()
        self.escrever("FOTO VINCULADA COM SUCESSO!", "green")

    def iniciar_registro_digital(self, aid): self.aluno_em_registro = aid; self.escrever(f"AGUARDANDO BIOMETRIA PARA {aid}...", "orange")

    def servidor_bio(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sv:
            sv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); sv.bind(('0.0.0.0', SERVIDOR_PORTA)); sv.listen(5)
            while True:
                conn, _ = sv.accept()
                with conn:
                    raw = conn.recv(1024).decode('utf-8', errors='ignore')
                    if raw:
                        # Manda para a janela de config se estiver aberta para teste
                        if self.janela_config and self.janela_config.winfo_exists():
                            self.after(0, lambda: self.janela_config.log_raw_bio(raw))
                        
                        tag = raw.split('|')[1] if '|' in raw else raw.strip()
                        if self.aluno_em_registro: self.vincular_bio(self.aluno_em_registro, tag); self.aluno_em_registro = None
                        else: self.validar(tag)

    def vincular_bio(self, aid, tag):
        try:
            requests.post(f"{SITE_URL}/api/aluno-update-data/", data={'aluno_id': aid, 'digital': tag, 'token': SYNC_TOKEN})
            self.after(0, self.carregar_alunos); self.after(0, lambda: self.escrever(f"DIGITAL VINCULADA!", "green"))
        except: pass

    def validar(self, tag):
        try:
            r = requests.get(f"{SITE_URL}/api/catraca-check/{tag}/?token={SYNC_TOKEN}").json()
            if r.get('status') != 'vencido': 
                self.abrir_catraca("0")
                if self.monitor and self.monitor.winfo_exists(): self.after(0, lambda: self.monitor.indentificar_aluno(r))
            self.after(0, lambda: self.escrever(f"ACESSO: {r.get('nome')} - {r.get('status').upper()}"))
        except: pass

if __name__ == "__main__":
    AppRecepcao().mainloop()
