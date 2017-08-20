import os

ROOT_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), os.pardir)
INSTANCE_PATH = os.path.join(ROOT_PATH, 'instance')
DB_PATH = os.path.join(INSTANCE_PATH, 'db.sqlite3')

API_KEY = None

DEFAULT_TIMEZONE = 'Europe/Moscow'
SVOBODA_CHAT_ID = None

INSTAGRAM_CLIENT_ID = None
INSTAGRAM_CLIENT_SECRET = None

HTTP_HOST = '127.0.0.1'
HTTP_PORT = 5053

SERVER_NAME = None
PREFERRED_URL_SCHEME = None
