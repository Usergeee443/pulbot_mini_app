import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', ''),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', ''),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', ''),
}

BOT_TOKEN = os.getenv('BOT_TOKEN', '')

CLICK_SECRET_KEY = os.getenv('CLICK_SECRET_KEY', '')
CLICK_SERVICE_ID = os.getenv('CLICK_SERVICE_ID', '')
CLICK_MERCHANT_ID = os.getenv('CLICK_MERCHANT_ID', '')
CLICK_MERCHANT_USER_ID = os.getenv('CLICK_MERCHANT_USER_ID', '')

TARIFF_LIMITS = {
    'Bepul': {
        'transactions_per_month': 50,
        'ai_requests_per_day': 0,
        'advanced_analytics': False,
        'export_data': False,
        'custom_categories': 5,
        'charts_count': 1,
    },
    'Plus': {
        'transactions_per_month': -1,
        'ai_requests_per_day': 0,
        'advanced_analytics': True,
        'export_data': True,
        'custom_categories': -1,
        'charts_count': 5,
    },
    'PRO': {
        'transactions_per_month': -1,
        'ai_requests_per_day': -1,
        'advanced_analytics': True,
        'export_data': True,
        'custom_categories': -1,
        'charts_count': 10,
    },
}

PLUS_PACKAGES = {
    'T300V100': {
        'code': 'T300V100',
        'title': 'Mini',
        'tagline': "300 ta matn, 100 ta ovoz",
        'text_limit': 300,
        'voice_limit': 100,
        'price': 9900,
        'badge': "Boshlang'ich",
    },
    'T750V250': {
        'code': 'T750V250',
        'title': 'Optimal',
        'tagline': "750 ta matn, 250 ta ovoz",
        'text_limit': 750,
        'voice_limit': 250,
        'price': 19990,
        'badge': 'Eng ommabop',
    },
    'T1750V600': {
        'code': 'T1750V600',
        'title': 'Pro',
        'tagline': "1750 ta matn, 600 ta ovoz",
        'text_limit': 1750,
        'voice_limit': 600,
        'price': 39990,
        'badge': 'Eng ko\'p imkoniyat',
    },
}

PLUS_PACKAGE_SEQUENCE = ['T300V100', 'T750V250', 'T1750V600']

PROMO_CODES = {
    '50FRIEND50': {
        'discount_percent': 60,
        'limit': 10,
        'plan_type': 'PLUS',
        'description': "Do'stlar uchun 60% chegirma",
        'is_active': True,
    },
}
