import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.development')
django.setup()

from django.db import connection

def deep_clean():
    print("🔥 Iniciando limpeza profunda e correção de chaves estrangeras...")
    
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF;')
        
        # Tabelas que estão travando a integridade por apontarem para o modelo antigo
        tables_to_drop = [
            'django_admin_log', 
            'auth_user_groups', 
            'auth_user_user_permissions', 
            'auth_user'
        ]
        
        for table in tables_to_drop:
            try:
                print(f"🗑️ Removendo tabela legada: {table}")
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
            except Exception as e:
                print(f"⚠️ Erro ao remover {table}: {e}")
        
        cursor.execute('PRAGMA foreign_keys = ON;')
        
    print("\n✅ Tabelas legadas removidas!")
    print("🚀 Agora o Django recriará a tabela de Histórico (Log) apontando para o Usuário correto.")

if __name__ == "__main__":
    deep_clean()
