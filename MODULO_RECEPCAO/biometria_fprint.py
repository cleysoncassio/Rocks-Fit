import subprocess
import threading
import time
import os
import shutil

class BiometriaFPrint:
    """
    ARQUITETURA ROCKS-FIT: Gerenciador Industrial de Biometria
    Implementa Padrão Singleton e Máquina de Estados para Hardware.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BiometriaFPrint, cls).__new__(cls)
            return cls._instance

    def __init__(self, site_url=None, sync_token=None):
        if hasattr(self, '_initialized'): return
        self._initialized = True
        
        self.site_url = site_url
        self.sync_token = sync_token
        self.state = "IDLE" # IDLE, BUSY, ENROLLING, VERIFYING, ERROR
        self.verify_proc = None
        self.current_user = os.getenv("USER") or os.getenv("LOGNAME") or "root"
        self.paused = False
        
        self.fingers = [
            "left-thumb", "left-index-finger", "left-middle-finger", "left-ring-finger", "left-little-finger",
            "right-thumb", "right-index-finger", "right-middle-finger", "right-ring-finger", "right-little-finger"
        ]
        
        self.driver_disponivel = shutil.which("fprintd-enroll") is not None
        if not self.driver_disponivel:
            print("❌ [SISTEMA] Driver fprintd não detectado no PATH.")

    def _safe_kill(self, name):
        """Termina processos de forma limpa e depois agressiva."""
        try:
            subprocess.run(["pkill", "-u", self.current_user, "-15", name], capture_output=True)
            time.sleep(0.2)
            subprocess.run(["pkill", "-u", self.current_user, "-9", name], capture_output=True)
        except: pass

    def stop_all(self):
        """Libera o hardware de forma atômica."""
        with self._lock:
            self.state = "RELEASING"
            if self.verify_proc:
                try:
                    self.verify_proc.terminate()
                    self.verify_proc.wait(timeout=0.5)
                except:
                    try: self.verify_proc.kill()
                    except: pass
                self.verify_proc = None
            
            self._safe_kill("fprintd-verify")
            self._safe_kill("fprintd-enroll")
            self.state = "IDLE"

    def pause(self):
        self.paused = True
        self.stop_all()

    def resume(self):
        self.paused = False

    def _device_available(self):
        """Verifica se há algum dispositivo biométrico presente via USB (sem Polkit/Senha)."""
        try:
            # 1. Checa USB primeiro (Não exige senha/polkit)
            # IDs comuns: 0483 (ST), 06cb (Synaptics), 138a (Validity), 1491 (Futronic), 1c7a (LighTuning), 27c6 (Goodix)
            res_usb = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=2)
            usb_out = res_usb.stdout.lower()
            
            padrões = ["fingerprint", "biometric", "fprint", "scanner", "1491:", "06cb:", "138a:", "0483:", "1c7a:", "27c6:"]
            if not any(p in usb_out for p in padrões):
                # Se não há USB compatível, nem tenta o fprintd (evita prompt de senha)
                return False

            # 2. Confirmamos presença via fprintd-list (apenas se o hardware USB for detectado)
            # No Debian, usamos o timeout para evitar travamentos em prompts de senha Polkit
            res = subprocess.run(
                ["fprintd-list", self.current_user],
                capture_output=True, text=True, timeout=1.5
            )
            # Se o fprintd retornar erro ou timeout, assumimos que não está disponível ou requer senha
            if res.returncode != 0:
                return False
                
            output = (res.stdout + res.stderr).lower()
            if "no devices" in output or "nosuchdevice" in output:
                return False
            return True
        except (subprocess.TimeoutExpired, Exception):
            return False

    def verify(self, timeout=30):
        """
        Realiza a identificação com lógica de Backoff e Recuperação Automática.
        Retorna None se o hardware não estiver disponível (não sinaliza erro).
        """
        if not self.driver_disponivel: return None

        # --- Pré-verificação de hardware ---
        # Evita o loop infinito de NoSuchDevice sem precisar de limpeza nuclear.
        if not self._device_available():
            self.state = "IDLE"
            return None  # None = hardware ausente, não é erro recuperável agora

        # Estratégia de Retentativa Ultra-Rápida (Industrial)
        # Reduzido de 10 tentativas de 1.5s para 3 tentativas de 0.2s para máxima reatividade
        attempts = 3
        backoff = 0.2
        
        for i in range(attempts):
            if self.paused: return False
            
            # Se não for a primeira tentativa, limpamos tudo de forma rápida
            if i > 0:
                print(f"🔄 [FPRINT] Recuperação super-rápida - Tentativa {i+1}/{attempts}...")
                self.stop_all()
                time.sleep(backoff)
            
            try:
                if self.paused: return False
                self.state = "VERIFYING"
                self.verify_proc = subprocess.Popen(
                    ["fprintd-verify", self.current_user],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE, # Abre o stdin para evitar que trave esperando input
                    text=True
                )
                
                try:
                    # Leitura em tempo real para maior responsividade
                    last_verifying_finger = None
                    while True:
                        if self.verify_proc is None or self.verify_proc.poll() is not None:
                            break
                        
                        line = self.verify_proc.stdout.readline()
                        if not line:
                            time.sleep(0.05)
                            continue
                        
                        if line:
                            clean_line = line.strip()
                            print(f"📠 [DEBUG FPRINT] {clean_line}")
                            
                            # Rastreia qual dedo está sendo verificado no momento
                            if "Verifying:" in clean_line:
                                for f in self.fingers:
                                    if f in clean_line:
                                        last_verifying_finger = f
                                        break

                            if "verify-match" in clean_line:
                                # Se detectamos o dedo na mesma linha ou na linha anterior de status
                                finger_found = None
                                for f in self.fingers:
                                    if f in clean_line:
                                        finger_found = f; break
                                
                                final_finger = finger_found or last_verifying_finger or "unknown-finger"
                                print(f"🎯 [HARDWARE] Match confirmado: {final_finger}")
                                return final_finger

                            elif "verify-no-match" in clean_line:
                                print("👤 [HARDWARE] Digital capturada, mas não reconhecida.")
                                return "NO_MATCH"
                            elif "verify-unknown-error" in clean_line:
                                print("⚠️ [HARDWARE] Erro desconhecido no sensor. Reiniciando tentativa...")
                                self.stop_all()
                                break 
                            elif "Device was already claimed" in clean_line or "busy" in clean_line.lower():
                                print(f"⚠️ [HARDWARE] Recurso ocupado. Retentativa {i+1}/{attempts}...")
                                self.stop_all()
                                time.sleep(1.0) # Espera maior para o fprintd liberar o device no DBus
                                break # Vai para o próximo attempt
                    
                    if self.verify_proc is not None:
                        self.verify_proc.wait(timeout=1.5)
                except (subprocess.TimeoutExpired, AttributeError):
                    self.stop_all()
                    return None
            except Exception as e:
                print(f"❌ [DRV] Falha crítica na verificação: {e}")
                self.stop_all()
                time.sleep(2.0)
                return False
                
        return False

    def enroll(self, matricula, finger="right-index-finger"):
        """Inicia fluxo de cadastro com isolamento de processo."""
        self.stop_all()
        time.sleep(1.0)
        
        print(f"🎬 [FPRINT] Iniciando Enrolment: {matricula} | {finger}")
        self.state = "ENROLLING"
        
        try:
            process = subprocess.Popen(
                ["fprintd-enroll", "-f", finger, self.current_user],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            return process
        except Exception as e:
            print(f"❌ [DRV] Falha ao disparar fprintd-enroll: {e}")
            return None

    def guardar_arquivo_local(self, matricula, finger):
        """Persiste o metadado do mapeamento biométrico."""
        path = f"BIOMETRIA_DATA/ALUNOS/{matricula}_{finger}.finger"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import json
        data = {
            "matricula": matricula,
            "finger": finger,
            "timestamp": time.time(),
            "user": self.current_user
        }
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"💾 [FPRINT] Perfil biométrico salvo: {path}")

    def apagar_digital_local(self, matricula, finger):
        """Remove a digital do banco local e do hardware."""
        path = f"BIOMETRIA_DATA/ALUNOS/{matricula}_{finger}.finger"
        try:
            if os.path.exists(path):
                os.remove(path)
            # Remove do hardware também via CLI (melhor esforço)
            subprocess.run(["fprintd-delete", "-f", finger, self.current_user], capture_output=True)
            return True
        except: return False

    def get_enrolled_fingers(self, matricula):
        """Consulta o banco local para listar dedos cadastrados desta matrícula."""
        enrolled = []
        path_dir = "BIOMETRIA_DATA/ALUNOS"
        if not os.path.exists(path_dir): return []
        
        # Filtra arquivos do tipo: {matricula}_{finger}.finger
        for f in os.listdir(path_dir):
            if f.startswith(f"{matricula}_") and f.endswith(".finger"):
                try:
                    finger = f.split("_", 1)[1].replace(".finger", "")
                    enrolled.append(finger)
                except: continue
        return enrolled
