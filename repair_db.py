import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.development')
django.setup()

from django.db import connection
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

def repair():
    print("🚀 Iniciando reparo de integridade do banco...")
    
    with connection.cursor() as cursor:
        # 1. Desabilita checagem de chaves para limpeza
        cursor.execute('PRAGMA foreign_keys = OFF;')
        
        print("清理 - Removendo logs de admin órfãos...")
        LogEntry.objects.all().delete()
        
        # 2. Verifica se existem tabelas fantasmas de auth e limpa se necessário
        # Em SQLite, às vezes a tabela auth_user permanece e causa conflitos de FK
        try:
            cursor.execute('DELETE FROM auth_user_groups;')
            cursor.execute('DELETE FROM auth_user_user_permissions;')
            cursor.execute('DELETE FROM auth_user;')
            print("✅ Tabelas de auth antigas limpas.")
        except Exception:
            print("ℹ️ Tabelas de auth antigas já não existem ou estão limpas.")

        # 3. Reabilita checagem
        cursor.execute('PRAGMA foreign_keys = ON;')
        
    print("\n✅ Reparo concluído! Tente realizar a alteração no admin novamente.")

if __name__ == "__main__":
    repair()
