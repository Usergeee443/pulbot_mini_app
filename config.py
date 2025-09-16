import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Ma'lumotlar bazasi sozlamalari
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Flask sozlamalari
FLASK_HOST = os.getenv('FLASK_HOST')
FLASK_PORT = int(os.getenv('FLASK_PORT'))
SECRET_KEY = os.getenv('SECRET_KEY')

# Qo'shimcha sozlamalar
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ENVIRONMENT = os.getenv('ENVIRONMENT')

# Mini app URL
MINI_APP_URL = f"{WEBHOOK_URL}/miniapp" if WEBHOOK_URL and WEBHOOK_URL != 'YOUR_NGROK_URL_HERE' else f'http://localhost:{FLASK_PORT}/miniapp'
