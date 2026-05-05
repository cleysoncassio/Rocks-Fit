"""
Management command: fix_db_permissions

Concede permissões completas ao usuário da aplicação em todas as tabelas
do schema public do PostgreSQL. Deve ser executado:
  - Durante o build (build.sh)
  - Durante o startup (start.sh) ANTES do Gunicorn subir
  - Manualmente quando necessário: python manage.py fix_db_permissions
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Concede permissões completas ao usuário atual em todas as tabelas PostgreSQL."

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("[fix_db_permissions] Iniciando correção de permissões...")

        # Verificar se é PostgreSQL
        db_engine = connection.settings_dict.get("ENGINE", "")
        if "postgresql" not in db_engine and "postgis" not in db_engine:
            self.stdout.write(
                self.style.WARNING(
                    f"[fix_db_permissions] Banco não é PostgreSQL ({db_engine}). Pulando."
                )
            )
            return

        # Obter usuário e banco corrente
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user, current_database();")
                row = cursor.fetchone()
                current_user, current_db = row
                self.stdout.write(
                    f"[fix_db_permissions] Banco: {current_db} | Usuário: {current_user}"
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[fix_db_permissions] Falha ao identificar usuário: {e}"))
            return

        # Lista de comandos SQL para corrigir permissões
        # Inclui: tabelas, sequências, funções e privilégios padrão para tabelas futuras
        grant_commands = [
            # Permissões imediatas sobre objetos existentes
            f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{current_user}\";",
            f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{current_user}\";",
            f"GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO \"{current_user}\";",
            # Permissões padrão para novas tabelas criadas por migrações futuras
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"{current_user}\";",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \"{current_user}\";",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO \"{current_user}\";",
        ]

        erros = []
        for cmd in grant_commands:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(cmd)
                self.stdout.write(self.style.SUCCESS(f"  ✅ {cmd[:80]}..."))
            except Exception as e:
                erros.append((cmd, str(e)))
                self.stdout.write(self.style.WARNING(f"  ⚠️  {cmd[:80]}... FALHOU: {e}"))

        # Verificar se tabelas críticas ficaram acessíveis
        critical_tables = [
            "blog_trainer",
            "blog_plan",
            "blog_program",
            "blog_schedule",
            "blog_aluno",
            "blog_controleacesso",
        ]
        self.stdout.write("\n[fix_db_permissions] Verificando acessibilidade das tabelas críticas...")
        all_ok = True
        for table in critical_tables:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT 1 FROM {table} LIMIT 1;")
                self.stdout.write(self.style.SUCCESS(f"  ✅ {table}: OK"))
            except Exception as e:
                all_ok = False
                self.stdout.write(self.style.ERROR(f"  ❌ {table}: FALHOU — {e}"))

        self.stdout.write("=" * 60)
        if not erros and all_ok:
            self.stdout.write(
                self.style.SUCCESS(
                    "[fix_db_permissions] ✅ Todas as permissões concedidas e verificadas com sucesso!"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"[fix_db_permissions] ⚠️  Concluído com {len(erros)} erro(s) de GRANT e "
                    f"{'FALHA' if not all_ok else 'OK'} na verificação. "
                    "O usuário pode não ter privilégio de GRANT (apenas o owner pode)."
                )
            )
            # Instrução de fallback para o operador
            self.stdout.write(
                "\n[fix_db_permissions] SOLUÇÃO MANUAL (rodar no psql como superusuário):\n"
                f"  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {current_user};\n"
                f"  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {current_user};\n"
                f"  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {current_user};\n"
            )
