import subprocess
import threading
import time
import os

class BiometriaFPrint:
    def __init__(self, site_url, sync_token):
        self.site_url = site_url
        self.sync_token = sync_token
        self.running = False
        self._lock = threading.Lock()
        self.fingers = [
            "left-thumb", "left-index-finger", "left-middle-finger", "left-ring-finger", "left-pinky",
            "right-thumb", "right-index-finger", "right-middle-finger", "right-ring-finger", "right-pinky"
        ]

    def enroll(self, matricula, finger="right-index-finger"):
        """
        Inicia o processo de captura da digital para um aluno e um dedo específico.
        """
        import getpass
        current_user = getpass.getuser()
        print(f"🎬 [FPRINT] Iniciando captura: {finger} para Aluno {matricula}")
        
        try:
            # Tenta limpar registros prévios do sistema para este dedo
            subprocess.run(["fprintd-delete", "-f", finger, current_user], capture_output=True, timeout=2)
        except: pass

        try:
            # fprintd-enroll para o dedo escolhido
            # No Linux, fprintd-enroll aguarda interativamente 3 a 5 toques.
            process = subprocess.Popen(
                ["fprintd-enroll", "-f", finger, current_user],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            return process
        except Exception as e:
            print(f"❌ [FPRINT] Erro ao iniciar enroll: {e}")
            return None

    def verify(self, matricula, finger="right-index-finger"):
        """
        Verifica se a digital no sensor pertence ao aluno.
        Nota: fprintd-verify é bloqueante e aguarda um toque.
        """
        import getpass
        current_user = getpass.getuser()
        try:
            # Timeout curto para não travar a aplicação se o sensor falhar
            result = subprocess.run(
                ["fprintd-verify", "-f", finger, current_user],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "verify-match" in result.stdout:
                return True
            return False
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"❌ [FPRINT] Erro na verificação: {e}")
            return False

    def check_exists(self, matricula, finger):
        """
        Verifica se existe um registro local para a digital deste aluno e dedo.
        """
        base_path = "BIOMETRIA_DATA/ALUNOS"
        return os.path.exists(f"{base_path}/{matricula}_{finger}.finger")

    def get_enrolled_fingers(self, matricula):
        """
        Retorna lista de dedos já cadastrados para este aluno com base nos arquivos locais.
        """
        enrolled = []
        base_path = "BIOMETRIA_DATA/ALUNOS"
        if not os.path.exists(base_path): return []
        
        for finger in self.fingers:
            if os.path.exists(f"{base_path}/{matricula}_{finger}.finger"):
                enrolled.append(finger)
        return enrolled

    def guardar_arquivo_local(self, matricula, finger="right-index-finger"):
        """
        Registra localmente que o dedo foi cadastrado.
        """
        diretorio_destino = "BIOMETRIA_DATA/ALUNOS"
        os.makedirs(diretorio_destino, exist_ok=True)
        destino = f"{diretorio_destino}/{matricula}_{finger}.finger"
        
        try:
            with open(destino, 'w') as f:
                f.write(f"ENROLLED_AT_{time.strftime('%Y-%m-%d_%H:%M:%S')}")
            return True
        except Exception as e:
            print(f"❌ [FPRINT] Erro ao salvar registro local: {e}")
            return False

    def apagar_digital_local(self, matricula, finger):
        """
        Remove o registro local e tenta limpar do sistema fprintd.
        """
        import getpass
        current_user = getpass.getuser()
        path = f"BIOMETRIA_DATA/ALUNOS/{matricula}_{finger}.finger"
        
        sucesso = False
        if os.path.exists(path):
            try:
                os.remove(path)
                sucesso = True
            except: pass
            
        try:
            # Tenta remover do fprintd também
            subprocess.run(["fprintd-delete", "-f", finger, current_user], capture_output=True, timeout=3)
        except: pass
        
        return sucesso
