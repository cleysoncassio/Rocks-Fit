import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.development')
django.setup()

from django.db import connection

def check_integrity():
    with connection.cursor() as cursor:
        print("🔍 Verificando violações de Chaves Estrangeiras...")
        cursor.execute('PRAGMA foreign_key_check;')
        violations = cursor.fetchall()
        
        if not violations:
            print("✅ Nenhuma violação óbvia encontrada pelo PRAGMA.")
        else:
            print(f"⚠️ Encontradas {len(violations)} violações:")
            for v in violations:
                # v = (table, rowid, parent_table, fkid)
                print(f"Tabela: {v[0]}, RowID: {v[1]}, Aponta para: {v[2]}, FK index: {v[3]}")

        print("\n📊 Listando Tabelas que referenciam o Usuário...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fks = cursor.fetchall()
            for fk in fks:
                if 'user' in fk[2].lower():
                    print(f"A tabela '{table_name}' possui FK para '{fk[2]}' no campo '{fk[3]}'")

if __name__ == "__main__":
    check_integrity()
