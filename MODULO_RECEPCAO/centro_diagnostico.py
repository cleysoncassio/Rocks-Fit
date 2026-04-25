import customtkinter as ctk
import os
import sys
import socket
import threading
import time
import cv2
from PIL import Image, ImageTk

# --- CONFIGURAÇÕES ---
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 3000
COR_BG = "#0c0c0c"
COR_PRIMARY = "#f27121"
COR_CARD = "#1a1a1a"
COR_TEXTO = "#FFFFFF"
COR_SUCCESS = "#4caf50"
COR_ERROR = "#f44336"

class CentroDiagnostico(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ROCKS FIT - CENTRO DE DIAGNÓSTICO")
        self.geometry("900x700")
        self.configure(fg_color=COR_BG)
        
        self.cap = None
        self.camera_rodando = False
        
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=30, pady=20)
        
        ctk.CTkLabel(header, text="DIAGNÓSTICO", font=("Space Grotesk", 32, "bold"), text_color=COR_TEXTO if hasattr(self, 'COR_TEXTO') else "#FFF").pack(side="left")
        ctk.CTkLabel(header, text="ROCKS FIT", font=("Space Grotesk", 24, "bold"), text_color=COR_PRIMARY).pack(side="left", padx=10, pady=(8,0))

        # Main Container
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # --- 1. TESTE DE CATRACA ---
        self.card_catraca = self.criar_card(container, "🔒 TESTE DE CONEXÃO - CATRACA")
        self.btn_test_catraca = ctk.CTkButton(self.card_catraca, text="TESTAR CONEXÃO", command=self.testar_catraca, fg_color=COR_PRIMARY, text_color="#000")
        self.btn_test_catraca.pack(pady=10)
        self.status_catraca = ctk.CTkLabel(self.card_catraca, text="Aguardando teste...", font=("Inter", 12))
        self.status_catraca.pack()

        # --- 2. TESTE DE BIOMETRIA DIGITAL ---
        self.card_bio = self.criar_card(container, "☝️ TESTE DE HARDWARE - DIGITAL")
        self.btn_test_bio = ctk.CTkButton(self.card_bio, text="VERIFICAR LEITOR", command=self.testar_biometria, fg_color=COR_PRIMARY, text_color="#000")
        self.btn_test_bio.pack(pady=10)
        self.status_bio = ctk.CTkLabel(self.card_bio, text="Aguardando verificação...", font=("Inter", 12))
        self.status_bio.pack()

        # --- 3. TESTE DE BIOMETRIA FACIAL ---
        self.card_facial = self.create_facial_card(container)

    def criar_card(self, parent, titulo):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color="#333")
        card.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(card, text=titulo, font=("Inter", 16, "bold"), text_color=COR_PRIMARY).pack(pady=(15, 5))
        return card

    def create_facial_card(self, parent):
        card = self.criar_card(parent, "📸 TESTE DE SCANNER FACIAL")
        
        self.cam_preview = ctk.CTkLabel(card, text="CÂMERA DESLIGADA", width=320, height=240, fg_color="#000", corner_radius=10)
        self.cam_preview.pack(pady=10)
        
        self.btn_cam = ctk.CTkButton(card, text="LIGAR CÂMERA", command=self.toggle_camera, fg_color=COR_PRIMARY, text_color="#000")
        self.btn_cam.pack(pady=10)
        
        self.status_facial = ctk.CTkLabel(card, text="Verifique se a câmera USB está conectada.", font=("Inter", 11), text_color="#888")
        self.status_facial.pack(pady=(0, 15))
        return card

    def testar_catraca(self):
        self.status_catraca.configure(text="Tentando conectar...", text_color="#FFF")
        def run():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                res = s.connect_ex((CATRACA_IP, CATRACA_PORTA))
                s.close()
                if res == 0:
                    self.after(0, lambda: self.status_catraca.configure(text=f"✅ ONLINE: {CATRACA_IP}:{CATRACA_PORTA}", text_color=COR_SUCCESS))
                else:
                    self.after(0, lambda: self.status_catraca.configure(text=f"❌ OFFLINE (Código: {res})", text_color=COR_ERROR))
            except Exception as e:
                self.after(0, lambda: self.status_catraca.configure(text=f"❌ ERRO: {str(e)}", text_color=COR_ERROR))
        threading.Thread(target=run, daemon=True).start()

    def testar_biometria(self):
        self.status_bio.configure(text="Iniciando SDK...", text_color="#FFF")
        try:
            import win32com.client
            readers = win32com.client.Dispatch("DPFP.OneTouch.ReadersCollection.1")
            count = readers.Count
            if count > 0:
                self.status_bio.configure(text=f"✅ OK: {readers.Item(1).Description}", text_color=COR_SUCCESS)
            else:
                self.status_bio.configure(text="❌ LEITOR NÃO ENCONTRADO", text_color=COR_ERROR)
        except Exception as e:
            self.status_bio.configure(text=f"❌ ERRO DE SDK: {str(e)[:40]}...", text_color=COR_ERROR)

    def toggle_camera(self):
        if not self.camera_rodando:
            # Tenta encontrar a câmera disponível (0, 1 ou 2)
            for index in [0, 1, 2]:
                self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if self.cap.isOpened():
                    print(f"Câmera de diagnóstico OK no índice {index}")
                    break
            
            if not self.cap or not self.cap.isOpened():
                self.status_facial.configure(text="❌ NÃO FOI POSSÍVEL ENCONTRAR NENHUMA CÂMERA", text_color=COR_ERROR)
                return
            self.camera_rodando = True
            self.btn_cam.configure(text="DESLIGAR CÂMERA", fg_color="#333", text_color="#FFF")
            threading.Thread(target=self.face_loop, daemon=True).start()
        else:
            self.camera_rodando = False
            if self.cap: self.cap.release()
            self.cam_preview.configure(image="", text="CÂMERA DESLIGADA")
            self.btn_cam.configure(text="LIGAR CÂMERA", fg_color=COR_PRIMARY, text_color="#000")

    def face_loop(self):
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        while self.camera_rodando:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 165, 255), 2)
                    cv2.putText(frame, "ROCKS SCAN", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
                
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 240))
                self.after(0, lambda: self.cam_preview.configure(image=ctk_img, text=""))
                self.after(0, lambda: self.status_facial.configure(text=f"✅ CÂMERA OK - {len(faces)} face(s) detectada(s)", text_color=COR_SUCCESS))
                self.img_ref = ctk_img
            time.sleep(0.01)

if __name__ == "__main__":
    app = CentroDiagnostico()
    app.mainloop()
