import os
import sys
import subprocess
import shutil

def reparar():
    print("--- INICIANDO REPARO DO AMBIENTE BIOMÉTRICO (ROCKS FIT) ---")
    
    # 1. Limpar cache de componentes (gen_py) que causa conflito de classes
    gen_py = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'gen_py')
    if os.path.exists(gen_py):
        print(f"Limpando cache COM em: {gen_py}")
        try:
            shutil.rmtree(gen_py, ignore_errors=True)
            print("✅ Cache limpo.")
        except:
            print("⚠️ Não foi possível limpar todo o cache. Certifique-se que nenhum Python está aberto.")
    
    # 2. Tentar localizar e rodar o post-install do pywin32
    print("Localizando scripts de registro de hardware...")
    python_dir = os.path.dirname(sys.executable)
    scripts_path = os.path.join(python_dir, "Scripts", "pywin32_postinstall.py")
    
    # Caso alternativo (se estiver em venv)
    if not os.path.exists(scripts_path):
        scripts_path = os.path.join(sys.prefix, "Scripts", "pywin32_postinstall.py")

    if os.path.exists(scripts_path):
        print(f"Executando registro em: {scripts_path}")
        try:
            # Executa com permissão de administrador se possível
            subprocess.run([sys.executable, scripts_path, "-install"], check=True)
            print("✅ Componentes de hardware registrados no Windows.")
        except Exception as e:
            print(f"❌ Erro ao registrar componentes: {e}")
            print("Dica: Tente abrir o CMD como ADMINISTRADOR e rode o script novamente.")
    else:
        print("⚠️ Script de registro (pywin32_postinstall.py) não encontrado.")
        print(f"Verifique sua instalação em: {python_dir}")

    print("\n" + "="*60)
    print("  PASSOS FINAIS PARA REMOVER O CONFLITO:")
    print("="*60)
    print("  1. Verifique se o Next Fit não está na bandeja (perto do relógio).")
    print("  2. Desconecte e reconecte o leitor USB.")
    print("  3. REINICIE o computador (essencial para resetar o serviço biométrico).")
    print("="*60)

if __name__ == "__main__":
    reparar()
