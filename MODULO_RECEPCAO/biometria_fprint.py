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
        Usa o nome student_<matricula> para organizar no fprintd.
        """
        user = f"student_{matricula}"
        print(f"🎬 Iniciando captura para {user}...")
        
        # Tenta criar o usuário se não existir (precisaria de sudo, mas vamos tentar o comando direto)
        # Se falhar, usaremos o usuário atual como fallback (limitado)
        try:
            # Comando fprintd-enroll
            # -f right-index-finger é o padrão
            process = subprocess.Popen(
                ["fprintd-enroll", "-f", "right-index-finger", user],
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
        user = f"student_{matricula}"
        try:
            result = subprocess.run(
                ["fprintd-verify", "-u", user],
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
        Simula a guarda do arquivo no módulo recepção.
        Como o fprintd guarda em /var/lib/fprint/, criamos um backup se tivermos permissão.
        """
        origem = f"/var/lib/fprint/student_{matricula}/right-index-finger"
        destino = f"CONTROLE_ACESSO/ALUNOS/{matricula}.finger"
        
        # Tenta copiar se o arquivo existir (precisa de permissão de leitura)
        if os.path.exists(origem):
            try:
                with open(origem, 'rb') as f:
                    data = f.read()
                with open(destino, 'wb') as f:
                    f.write(data)
                print(f"💾 Digital de {matricula} salva localmente em {destino}")
                return True
            except Exception as e:
                print(f"⚠️ Não foi possível copiar arquivo de digital: {e}")
        
        # Caso contrário, apenas marca que o aluno tem digital
        with open(destino, 'w') as f:
            f.write("ENROLLED")
        return False
