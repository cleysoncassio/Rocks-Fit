#!/bin/bash
pip install --upgrade pip
pip install -r requirements.txt
python3 -c "from django.db import connection; [cursor.execute(q) for q in ['GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;', 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;', 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;']]"
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py loaddata dados_blog.json