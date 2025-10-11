import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Ma'lumotlar bazasi sozlamalari
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'pulbot_mini_app')
}

# Bot sozlamalari
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Flask sozlamalari
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', 8080))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# OpenAI sozlamalari
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')

# Tarif tizimi
TARIFF_LIMITS = {
    'FREE': {
        'transactions_per_month': 50,
        'ai_requests_per_day': 0,
        'advanced_analytics': False,
        'export_data': False,
        'custom_categories': 5,
        'charts_count': 1
    },
    'PREMIUM': {
        'transactions_per_month': -1,  # Unlimited
        'ai_requests_per_day': 0,
        'advanced_analytics': True,
        'export_data': True,
        'custom_categories': -1,  # Unlimited
        'charts_count': 5
    },
    'MAX': {
        'transactions_per_month': -1,  # Unlimited
        'ai_requests_per_day': -1,  # Unlimited
        'advanced_analytics': True,
        'export_data': True,
        'custom_categories': -1,  # Unlimited
        'charts_count': 10
    }
}

# Qo'shimcha sozlamalar
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Mini app URL
MINI_APP_URL = f"{WEBHOOK_URL}/miniapp" if WEBHOOK_URL and WEBHOOK_URL != 'YOUR_NGROK_URL_HERE' else f'http://localhost:{FLASK_PORT}/miniapp'
