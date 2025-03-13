import os

DATA_DIR = os.path.expanduser('~/pgadmin4')
SQLITE_PATH = os.path.join(DATA_DIR, 'pgadmin4.db')
LOG_FILE = os.path.join(DATA_DIR, 'pgadmin4.log')
SESSION_DB_PATH = os.path.join(DATA_DIR, 'sessions')
STORAGE_DIR = os.path.join(DATA_DIR, 'storage')