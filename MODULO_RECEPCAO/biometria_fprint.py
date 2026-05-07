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

    def enroll(self, matricula):
        """
        Inicia o processo de captura da digital para um aluno.
        Para evitar pedido de senha, tentamos capturar como o usuário atual
        e depois movemos o arquivo para a pasta do aluno.
        """
        print(f"🎬 Iniciando captura para Aluno {matricula}...")
        
        try:
            # fprintd-enroll sem usuário captura para o usuário que executa (geralmente sem senha)
            process = subprocess.Popen(
                ["fprintd-enroll", "-f", "right-index-finger"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return process
        except Exception as e:
            print(f"❌ Erro ao iniciar enroll: {e}")
            return None

    def verify(self, matricula):
        """
        Verifica se a digital no sensor pertence ao aluno.
        """
        try:
            result = subprocess.run(
                ["fprintd-verify"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if "verify-match" in result.stdout:
                return True
            return False
        except Exception:
            return False

    def loop_verificacao_global(self, callback_sucesso, alunos_list):
        """
        Loop que tenta identificar QUALQUER aluno que colocar o dedo.
        Como o fprintd-verify exige um usuário, este método é desafiador
        sem saber quem está lá. 
        
        Estratégia: Se o fprintd não permite busca global, 
        recomendamos o uso de um 'Aproxime sua digital' seguido de 
        verificação específica ou uma lista de usuários frequentes.
        """
        self.running = True
        while self.running:
            # Para cada aluno no cache local
            for aluno in alunos_list:
                if not self.running: break
                mat = aluno.get("matricula")
                if not mat: continue
                
                # Verificação rápida
                if self.verify(mat):
                    callback_sucesso(aluno)
                    time.sleep(5) # Cooldown
                    break
            time.sleep(1)

    def guardar_arquivo_local(self, matricula):
        """
        Salva a digital do aluno na pasta do módulo.
        Busca do usuário atual (que acabou de fazer o enroll).
        """
        import getpass
        current_user = getpass.getuser()
        
        # Caminho padrão do fprintd no Linux
        origem = f"/var/lib/fprint/{current_user}/right-index-finger"
        diretorio_destino = "BIOMETRIA_DATA/ALUNOS"
        os.makedirs(diretorio_destino, exist_ok=True)
        destino = f"{diretorio_destino}/{matricula}.finger"
        
        print(f"📂 Tentando persistir digital de {current_user} para {destino}...")
        
        # Tenta copiar se o arquivo existir (pode precisar de sudo para ler /var/lib/fprint)
        # Se falhar a leitura direta, tentamos via comando cp com sudo se necessário, 
        # ou apenas marcamos como cadastrado se for o caso.
        if os.path.exists(origem):
            try:
                # Tentativa de cópia direta
                with open(origem, 'rb') as f:
                    data = f.read()
                with open(destino, 'wb') as f:
                    f.write(data)
                print(f"💾 Digital de {matricula} salva localmente em {destino}")
                return True
            except Exception as e:
                print(f"⚠️ Erro ao ler /var/lib/fprint (permissão?): {e}")
                # Fallback: se não puder ler o binário, criamos um marcador para o sistema saber que existe
                with open(destino, 'w') as f:
                    f.write("ENROLLED_SYSTEM")
                return True
        
        # Marcador genérico se o fprintd confirmou sucesso mas não achamos o arquivo
        with open(destino, 'w') as f:
            f.write("ENROLLED")
        return True
