"""
===========================================
 ROCKS FIT - DIAGNÓSTICO DE SISTEMA v1.0
===========================================
Rode este arquivo para descobrir POR QUE
os alunos não aparecem no Gestor.

Como rodar:
  ./.venv/bin/python diagnostico_rksfit.py
===========================================
"""
import os
import sys
import json
import socket

print("=" * 55)
print("  ROCKS FIT - DIAGNÓSTICO COMPLETO DO SISTEMA")
print("=" * 55)

# --- 1. CAMINHOS ---
print("\n[1/5] ANÁLISE DE CAMINHOS")
print(f"  Python executável : {sys.executable}")
print(f"  __file__          : {os.path.abspath(__file__)}")
print(f"  CWD (pasta atual) : {os.getcwd()}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"  BASE_DIR detectado: {BASE_DIR}")

# --- 2. CACHE ---
print("\n[2/5] VERIFICAÇÃO DO CACHE LOCAL")
# Tenta encontrar o arquivo no root ou na pasta rks-catraca
paths_to_try = [
    os.path.join(BASE_DIR, "alunos_local.json"),
    os.path.join(BASE_DIR, "rks-catraca", "alunos_local.json"),
    os.path.join(BASE_DIR, "..", "alunos_local.json")
]
CAMINHO_CACHE = next((p for p in paths_to_try if os.path.exists(p)), paths_to_try[0])

print(f"  Arquivo cache     : {CAMINHO_CACHE}")
print(f"  Arquivo existe?   : {os.path.exists(CAMINHO_CACHE)}")

if os.path.exists(CAMINHO_CACHE):
    try:
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        alunos = data.get('alunos', [])
        print(f"  ✅ CACHE OK! {len(alunos)} alunos encontrados:")
        for a in alunos:
            print(f"     -> ID:{a['id']} | {a['nome']} | {a['status']}")
    except Exception as e:
        print(f"  ❌ ERRO AO LER CACHE: {e}")
else:
    print(f"  ❌ CACHE NÃO ENCONTRADO!")
    print(f"  Conteúdo de {BASE_DIR}:")
    for item in os.listdir(BASE_DIR):
        print(f"     {item}")

# --- 3. LOGO ---
print("\n[3/5] VERIFICAÇÃO DA LOGO")
logo_paths = [
    os.path.join(BASE_DIR, "media", "images", "rkslogo.png"),
    os.path.join(BASE_DIR, "rkslogo.png")
]
CAMINHO_LOGO = next((p for p in logo_paths if os.path.exists(p)), logo_paths[0])
print(f"  Logo path         : {CAMINHO_LOGO}")
print(f"  Logo existe?      : {os.path.exists(CAMINHO_LOGO)}")

# --- 4. API ---
print("\n[4/5] TESTE DA API PRODUÇÃO")
try:
    import requests
    SITE_URL = "https://academiarocksfit.com.br"
    r = requests.get(f"{SITE_URL}/api/aluno-list-full/?token=rocksfit@2024", timeout=10)
    print(f"  Status HTTP       : {r.status_code}")
    if r.status_code == 200:
        alunos_api = r.json().get('alunos', [])
        print(f"  ✅ API OK! {len(alunos_api)} alunos:")
        for a in alunos_api:
            print(f"     -> ID:{a['id']} | {a['nome']} | {a['status']}")
    else:
        print(f"  ❌ API ERRO: {r.text[:200]}")
except Exception as e:
    print(f"  ❌ API FALHOU: {e}")

# --- 5. CATRACA ---
print("\n[5/6] TESTE DE CONEXÃO COM A CATRACA")
CATRACA_IP   = "169.254.37.150"
CATRACA_PORT = 3000
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    resultado = s.connect_ex((CATRACA_IP, CATRACA_PORT))
    s.close()
    if resultado == 0:
        print(f"  ✅ CATRACA ONLINE ({CATRACA_IP}:{CATRACA_PORT})")
    else:
        print(f"  ⚠️  CATRACA OFFLINE (código: {resultado})")
except Exception as e:
    print(f"  ❌ CATRACA ERRO: {e}")

# --- 6. BIOMETRIA ---
print("\n[6/6] TESTE DE BIOMETRIA DIGITAL")
try:
    import win32com.client
    readers = win32com.client.Dispatch("DPFP.OneTouch.ReadersCollection.1")
    count = readers.Count
    if count > 0:
        print(f"  ✅ HARDWARE DETECTADO: {count} leitor(es) encontrado(s).")
        for i in range(count):
            print(f"     -> {readers.Item(i+1).Description}")
    else:
        print("  ⚠️  HARDWARE NÃO DETECTADO: Verifique se o leitor USB está conectado.")
except Exception as e:
    print(f"  ❌ SDK BIOMÉTRICO (OneTouch) NÃO CONFIGURADO: {e}")
    print("     DICA: Certifique-se de estar usando Windows e ter o pywin32 instalado.")

print("\n" + "=" * 55)
print("  FIM DO DIAGNÓSTICO - Cole o resultado acima!")
print("=" * 55)
input("\nPressione ENTER para fechar...")
