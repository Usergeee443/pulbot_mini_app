from flask import Flask, render_template, jsonify, request, redirect, abort
from flask_cors import CORS
import os
import requests
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from database import Database
from config import DB_CONFIG, TARIFF_LIMITS, OPENAI_API_KEY, CLICK_SECRET_KEY, CLICK_SERVICE_ID, CLICK_MERCHANT_ID, CLICK_MERCHANT_USER_ID

# Flask app yaratish
app = Flask(__name__)
CORS(app)

# Database yaratish
db = Database()

# OpenAI client (lazy loading)
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"OpenAI client yaratishda xatolik: {e}")
    return openai_client

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/miniapp')
def miniapp():
    # URL dan user_id ni olish
    user_id = request.args.get('user_id')
    if user_id:
        # User ID ni template ga uzatish
        return render_template('index.html', user_id=user_id)
    return render_template('index.html')

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    """Real to'lov sahifasi - Plus yoki Pro tarif"""
    if request.method == 'GET':
        return render_template('payment.html')
    
    try:
        user_id = request.form.get('user_id', CLICK_MERCHANT_USER_ID)
        tariff = request.form.get('tariff', 'PLUS').upper()
        months = request.form.get('months')
        
        if not months or months not in ['1', '12']:
            return jsonify({
                'error': 'Invalid months selection'
            }), 400
        
        if tariff not in ['PLUS', 'PRO']:
            return jsonify({
                'error': 'Invalid tariff selection'
            }), 400
        
        months = int(months)
        user_id = int(user_id)
        
        # Narxni belgilash (TEST uchun: Plus=1000, Pro=2000)
        prices = {
            'PLUS': {
                1: 1000,  # TEST: 1000 so'm
                12: int(1000 * 12 * 0.9)  # TEST: 10% chegirma
            },
            'PRO': {
                1: 2000,  # TEST: 2000 so'm
                12: int(2000 * 12 * 0.9)  # TEST: 10% chegirma
            }
        }
        amount = prices.get(tariff, prices['PLUS']).get(months, 29990)
        
        # Merchant trans ID yaratish
        import time
        timestamp = int(time.time())
        merchant_trans_id = f"{user_id}_{tariff}_{months}_{timestamp}"
        
        # Database'ga to'lov yozuvini yaratish
        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, tariff, 'click')
        except Exception as e:
            logging.error(f"Error creating payment record: {e}")
        
        # Click.uz URL yaratish
        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"  # Backend uchun yashirin
            f"&customer={urllib.parse.quote(str(user_id))}"  # Buyurtma raqami (faqat user_id)
            f"&return_url={urllib.parse.quote('https://balansai.onrender.com/payment-success')}"
        )
        
        logging.info(f"Payment redirect: user_id={user_id}, tariff={tariff}, months={months}, amount={amount}")
        logging.info(f"Merchant Trans ID: {merchant_trans_id}")
        logging.info(f"Click URL: {click_url}")
        click_logger.info(f"PAYMENT: user_id={user_id}, tariff={tariff}, months={months}, amount={amount}, merchant_trans_id={merchant_trans_id}")
        
        return redirect(click_url)
    except Exception as e:
        logging.error(f"Payment error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/payment-pro', methods=['GET', 'POST'])
def payment_pro():
    """Faqat PRO uchun alohida sahifa"""
    if request.method == 'GET':
        return render_template('payment_pro.html')

    try:
        user_id = request.form.get('user_id', CLICK_MERCHANT_USER_ID)
        months = request.form.get('months')

        if not months or months not in ['1', '12']:
            return jsonify({'error': 'Invalid months selection'}), 400

        months = int(months)
        user_id = int(user_id)

        # TEST narxlar: PRO 1 oy = 2000, 12 oy = 2000*12*0.9
        prices = { 1: 2000, 12: int(2000 * 12 * 0.9) }
        amount = prices.get(months, 2000)

        # Merchant trans ID (har doim PRO)
        import time
        timestamp = int(time.time())
        merchant_trans_id = f"{user_id}_PRO_{months}_{timestamp}"

        # DB yozish
        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, 'PRO', 'click')
        except Exception as e:
            logging.error(f"Error creating payment record (PRO): {e}")

        # Click URL
        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"
            f"&customer={urllib.parse.quote(str(user_id))}"
            f"&return_url={urllib.parse.quote('https://balansai.onrender.com/payment-success')}"
        )

        logging.info(f"PAYMENT_PRO: user_id={user_id}, months={months}, amount={amount}, merchant_trans_id={merchant_trans_id}")
        logging.info(f"Click URL PRO: {click_url}")
        click_logger.info(f"PAYMENT_PRO: user_id={user_id}, months={months}, amount={amount}, merchant_trans_id={merchant_trans_id}")
        return redirect(click_url)
    except Exception as e:
        logging.error(f"Payment PRO error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/payment-success', methods=['GET'])
def payment_success():
    """To'lov muvaffaqiyatli bo'lganidan keyin sahifa"""
    payment_id = request.args.get('paymentId')
    payment_status = request.args.get('paymentStatus')
    
    return render_template('payment_success.html', 
                         payment_id=payment_id, 
                         payment_status=payment_status)

@app.route('/test-payment', methods=['GET', 'POST'])
def test_payment():
    """Click.uz test to'lov sahifasi"""
    # Simple protection: require key in query (?key=...) or header X-Test-Key
    TEST_PAYMENT_KEY = os.getenv('TEST_PAYMENT_KEY', '')
    if TEST_PAYMENT_KEY:
        provided_key = request.args.get('key') or request.headers.get('X-Test-Key')
        if provided_key != TEST_PAYMENT_KEY:
            return abort(404)
    if request.method == 'GET':
        return render_template('payment_test.html')
    
    # POST so'rov - Click.uz'ga redirect
    try:
        user_id = request.form.get('user_id', CLICK_MERCHANT_USER_ID)
        months = request.form.get('months')
        
        if not months or months not in ['1', '3', '6']:
            return jsonify({
                'error': 'Invalid months selection'
            }), 400
        
        months = int(months)
        user_id = int(user_id)
        
        # Narxni belgilash (REAL narxlar)
        prices = {
            1: 29990,  # 1 oy - PLUS tarif
            3: 79990,  # 3 oy - PLUS tarif
            6: 149990  # 6 oy - PLUS tarif
        }
        amount = prices.get(months, 29990)
        
        # Merchant trans ID yaratish
        import time
        timestamp = int(time.time())
        merchant_trans_id = f"{user_id}_PLUS_{months}_{timestamp}"
        
        # Database'ga to'lov yozuvini yaratish
        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, 'PLUS', 'click')
        except Exception as e:
            logging.error(f"Error creating payment record: {e}")
        
        # Click.uz URL yaratish
        # Click.uz dokumentatsiyasiga ko'ra: transaction_param ishlatiladi (merchant_trans_id emas!)
        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"
            f"&amount={amount}"
            f"&return_url={urllib.parse.quote('https://balansai.onrender.com/test-payment')}"
        )
        
        logging.info(f"Test payment redirect: user_id={user_id}, months={months}, amount={amount}")
        logging.info(f"Merchant Trans ID: {merchant_trans_id}")
        logging.info(f"Click URL: {click_url}")
        click_logger.info(f"TEST_PAYMENT: user_id={user_id}, months={months}, amount={amount}, merchant_trans_id={merchant_trans_id}")
        
        # Click.uz'ga redirect
        return redirect(click_url)
        
    except Exception as e:
        logging.error(f"Test payment error: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/terms')
def terms():
    """Foydalanish shartlari"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Maxfiylik siyosati"""
    return render_template('privacy.html')

# Asosiy API endpoints
@app.route('/api/statistics/<int:user_id>')
def get_statistics(user_id):
    """Foydalanuvchi statistikalarini olish"""
    try:
        # Asosiy statistikalar
        income_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'income'"
        expense_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'expense'"
        debt_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'debt'"
        
        income_result = db.execute_query(income_query, (user_id,))
        expense_result = db.execute_query(expense_query, (user_id,))
        debt_result = db.execute_query(debt_query, (user_id,))
        
        total_income = income_result[0]['total'] if income_result else 0
        total_expense = expense_result[0]['total'] if expense_result else 0
        total_debt = debt_result[0]['total'] if debt_result else 0
        
        balance = total_income - total_expense - total_debt
        
        # Oylik ma'lumotlar
        monthly_income_query = """
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'income' 
        AND MONTH(created_at) = MONTH(CURRENT_DATE()) 
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
        """
        monthly_expense_query = """
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'expense' 
        AND MONTH(created_at) = MONTH(CURRENT_DATE()) 
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
        """
        
        monthly_income_result = db.execute_query(monthly_income_query, (user_id,))
        monthly_expense_result = db.execute_query(monthly_expense_query, (user_id,))
        
        monthly_income = monthly_income_result[0]['total'] if monthly_income_result else 0
        monthly_expense = monthly_expense_result[0]['total'] if monthly_expense_result else 0
        
        # Kategoriya ma'lumotlari
        category_query = """
        SELECT category, COALESCE(SUM(amount), 0) as total 
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'expense' 
        GROUP BY category 
        ORDER BY total DESC 
        LIMIT 5
        """
        category_result = db.execute_query(category_query, (user_id,))
        
        # So'nggi tranzaksiyalar
        recent_transactions_query = """
        SELECT * FROM transactions 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        recent_transactions = db.execute_query(recent_transactions_query, (user_id,))
        
        # transaction_type ni type ga qo'shish
        if recent_transactions:
            for t in recent_transactions:
                if 'transaction_type' in t and 'type' not in t:
                    t['type'] = t['transaction_type']
        
        return jsonify({
            'success': True,
            'data': {
                'balance': float(balance),
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'total_debt': float(total_debt),
                'monthly_income': float(monthly_income),
                'monthly_expense': float(monthly_expense),
                'category_data': category_result or [],
                'recent_transactions': recent_transactions or []
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/debts/<int:user_id>')
def get_debts(user_id):
    """Foydalanuvchi qarzlarini olish"""
    try:
        # Qarzlar ro'yxati
        debts_query = """
        SELECT * FROM transactions 
        WHERE user_id = %s AND transaction_type = 'debt' 
        ORDER BY created_at DESC
        """
        debts = db.execute_query(debts_query, (user_id,))
        
        # Qarzlar xulosasi
        debt_summary_query = """
        SELECT 
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'debt'
        """
        debt_summary = db.execute_query(debt_summary_query, (user_id,))
        
        # transaction_type ni type ga qo'shish
        if debts:
            for t in debts:
                if 'transaction_type' in t and 'type' not in t:
                    t['type'] = t['transaction_type']
        
        return jsonify({
            'success': True,
            'data': {
                'debts': debts or [],
                'summary': debt_summary[0] if debt_summary else {'count': 0, 'total': 0}
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user/tariff/<int:user_id>')
def get_user_tariff(user_id):
    """Foydalanuvchi tarifini olish"""
    try:
        tariff = db.get_user_tariff(user_id)
        limits = TARIFF_LIMITS.get(tariff, TARIFF_LIMITS['Plus'])  # Default: Plus
        
        return jsonify({
            'success': True,
            'data': {
                'tariff': tariff,
                'limits': limits
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tariffs')
def get_tariffs():
    """Barcha tariflarni olish"""
    try:
        tariffs = [
            {
                'code': 'Bepul',
                'name': 'Bepul',
                'monthly_price': 0,
                'features': [
                    '50 ta tranzaksiya/oy',
                    '1 ta grafik',
                    'Oddiy statistika',
                    'AI yordamchisi yo\'q'
                ]
            },
            {
                'code': 'Plus',
                'name': 'Plus',
                'monthly_price': 99900,
                'features': [
                    'Cheksiz tranzaksiya',
                    '5 ta grafik',
                    'Batafsil statistika',
                    'Eksport funksiyasi',
                    'AI yordamchisi yo\'q'
                ]
            },
            {
                'code': 'Max',
                'name': 'Max',
                'monthly_price': 199900,
                'features': [
                    'Cheksiz tranzaksiya',
                    '10 ta grafik',
                    'Batafsil statistika',
                    'Eksport funksiyasi',
                    'AI yordamchisi bilan',
                    'Ovozli suhbat'
                ]
            }
        ]
        
        discount_rates = {
            1: 0,   # 1 oy: chegirma yo'q
            3: 5,   # 3 oy: 5% chegirma
            6: 10,  # 6 oy: 10% chegirma
            12: 20  # 12 oy: 20% chegirma
        }
        
        return jsonify({
            'success': True,
            'data': {
                'tariffs': tariffs,
                'discount_rates': discount_rates
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/payment/process', methods=['POST'])
def process_payment():
    """To'lovni amalga oshirish (webhook)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        tariff = data.get('tariff')
        months = data.get('months', 1)
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'test')
        
        if not user_id or not tariff or not amount:
            return jsonify({
                'success': False,
                'message': 'Ma\'lumotlar to\'liq emas'
            }), 400
        
        # Muddati hisoblash
        expires_at = datetime.now() + timedelta(days=30 * months)
        
        # Tarifni yangilash
        db.update_user_tariff(user_id, tariff)
        
        # To'lov tarixini saqlash (agar kerak bo'lsa)
        # payment_history jadvalini yaratishingiz kerak
        
        return jsonify({
            'success': True,
            'message': 'To\'lov muvaffaqiyatli amalga oshirildi',
            'data': {
                'tariff': tariff,
                'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                'months': months
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/config')
def get_config():
    """Frontend uchun konfiguratsiya"""
    try:
        # Faqat zarur konfiguratsiyalarni yuborish (API keylar secret qolishi kerak)
        return jsonify({
            'success': True,
            'data': {
                'openaiApiKey': None  # Security uchun client tarafida API key qo'llanilmaydi
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """Text to speech (server-side)"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'success': False, 'message': 'Text required'})
        
        # OpenAI client yaratish
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Raqamlarni yaxshiroq o'qish uchun formatlash
        # Raqamlarni so'zga aylantirish
        import re
        
        # Raqamlarni formatlash
        def format_numbers(text):
            # Million va ming bo'lgan raqamlarni yaxshiroq formatlash
            text = re.sub(r'(\d+)\.(\d+)', r'\1 nuqta \2', text)  # Nuqta bilan raqamlar
            text = re.sub(r'(\d+)%', r'\1 foiz', text)  # Foiz
            text = re.sub(r'(\d+)\s+so\'m', r'\1 so\'m', text)  # So'm
            text = re.sub(r'(\d{1,3})(\d{3})(\d{3})', r'\1 million \2 ming \3', text)  # Million
            text = re.sub(r'(\d{1,3})(\d{3})', r'\1 ming \2', text)  # Ming
            return text
        
        formatted_text = format_numbers(text)
        
        # TTS API chaqirish - o'zbek tiliga yaqin ovoz
        response = client.audio.speech.create(
            model="tts-1",
            voice="echo",  # Yaxshiroq ovoz
            input=formatted_text,
            speed=1.0
        )
        
        # Audio faylni qaytarish
        import base64
        audio_base64 = base64.b64encode(response.content).decode('utf-8')
        
        return jsonify({
            'success': True,
            'audio': audio_base64
        })
        
    except Exception as e:
        print(f"TTS error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/advice')
def get_ai_advice():
    """AI maslahat olish"""
    try:
        prompt = request.args.get('prompt', '')
        user_id = request.args.get('user_id')
        
        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt kiritilmagan'})
        
        # OpenAI API key tekshirish
        if not OPENAI_API_KEY:
            return jsonify({'success': False, 'message': 'AI xizmati konfiguratsiya qilinmagan'})
        
        # OpenAI client yaratish
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"OpenAI client yaratishda xatolik: {e}")
            return jsonify({'success': False, 'message': f'AI client xatoligi: {str(e)}'})
        
        # User tarifini tekshirish - MAX tarif uchun
        user_tariff = 'Bepul'  # Default
        user_name = 'Foydalanuvchi'  # Default name
        if user_id:
            try:
                user_tariff = db.get_user_tariff(user_id)
                # Foydalanuvchi nomini olish
                user_query = "SELECT first_name FROM users WHERE user_id = %s LIMIT 1"
                user_result = db.execute_query(user_query, (user_id,))
                if user_result:
                    user_name = user_result[0].get('first_name', 'Foydalanuvchi')
            except:
                pass
        
        # REPLY SYSTEM - Ha/Yo'q javoblarni tekshirish
        reply_type = None
        if prompt.lower().strip() in ['ha', 'yes', 'yo\'q', 'no', 'bekor', 'cancel', 'ok', 'go', 'tamom']:
            if prompt.lower().strip() in ['ha', 'yes', 'ok', 'go']:
                reply_type = 'yes'
            else:
                reply_type = 'no'
        
        # AVTOMATIK KIRITISH ANIQLANISHI (MAX tarif uchun)
        auto_transaction = None
        if user_tariff.upper() == 'MAX' and user_id and reply_type is None:
            auto_transaction = detect_and_add_transaction(client, prompt, user_id)
        
        # User statistikalarini olish
        context = ""
        recent_transactions = []
        if user_id:
            try:
                # Balans va statistikani olish
                income_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'income'"
                expense_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'expense'"
                debt_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'debt'"
                
                income_result = db.execute_query(income_query, (user_id,))
                expense_result = db.execute_query(expense_query, (user_id,))
                debt_result = db.execute_query(debt_query, (user_id,))
                
                total_income = income_result[0]['total'] if income_result else 0
                total_expense = expense_result[0]['total'] if expense_result else 0
                total_debt = debt_result[0]['total'] if debt_result else 0
                balance = total_income - total_expense - total_debt
                
                # Oylik statistika
                monthly_income_query = """
                SELECT COALESCE(SUM(amount), 0) as total 
                FROM transactions 
                WHERE user_id = %s AND transaction_type = 'income' 
                AND MONTH(created_at) = MONTH(CURRENT_DATE()) 
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                """
                monthly_expense_query = """
                SELECT COALESCE(SUM(amount), 0) as total 
                FROM transactions 
                WHERE user_id = %s AND transaction_type = 'expense' 
                AND MONTH(created_at) = MONTH(CURRENT_DATE()) 
                AND YEAR(created_at) = YEAR(CURRENT_DATE())
                """
                
                monthly_income_result = db.execute_query(monthly_income_query, (user_id,))
                monthly_expense_result = db.execute_query(monthly_expense_query, (user_id,))
                
                monthly_income = monthly_income_result[0]['total'] if monthly_income_result else 0
                monthly_expense = monthly_expense_result[0]['total'] if monthly_expense_result else 0
                
                # Kategoriya ma'lumotlari
                category_query = """
                SELECT category, COALESCE(SUM(amount), 0) as total 
                FROM transactions 
                WHERE user_id = %s AND transaction_type = 'expense' 
                GROUP BY category 
                ORDER BY total DESC 
                LIMIT 10
                """
                category_result = db.execute_query(category_query, (user_id,))
                
                # So'nggi tranzaksiyalar
                recent_query = """
                SELECT * FROM transactions 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 20
                """
                recent_transactions = db.execute_query(recent_query, (user_id,))
                
                # Context shunaslantirish
                context = f"""
📊 FOYDALANUVCHI MOLIYAVIY MA'LUMOTLARI:

💰 Balans: {balance:,.0f} so'm
📈 Umumiy daromad: {total_income:,.0f} so'm
📉 Umumiy xarajat: {total_expense:,.0f} so'm
💳 Qarzlar: {total_debt:,.0f} so'm

📅 BU OY:
📈 Oylik daromad: {monthly_income:,.0f} so'm
📉 Oylik xarajat: {monthly_expense:,.0f} so'm
💾 Bu oy tejash: {monthly_income - monthly_expense:,.0f} so'm

📋 XARAJATLAR BO'YICHA KATEGORIYA:
"""
                if category_result:
                    for i, cat in enumerate(category_result[:5], 1):
                        context += f"{i}. {cat['category']}: {cat['total']:,.0f} so'm\n"
                else:
                    context += "- Ma'lumot yo'q\n"
                
            except Exception as e:
                print(f"Statistika olishda xatolik: {e}")
        
        # ADVANCED System Prompt for MAX tariff
        if user_tariff.upper() == 'MAX':
            system_message = f"""🤖 BALANS AI — SHAXSIY MOLIYA YORDAMCHISI

Siz {user_name} ning ishonchli shaxsiy buxgalteri. Siz:

1️⃣ TAHLILIY VA PROFESSIONAL:
   • Moliyaviy ma'lumotlarini chuqur tahlil qilib, poyabzal maslaha bering
   • Raqamlarni aniq va asosli ko'rsating
   • Trendarni, o'zgarishlari va qonun-qo'idalarni izohlang

2️⃣ MULTI-STEP JAVOBLAR (4 BOSQICH):
   1. Asosiy javob: moliyaviy tahlil (statistika, trend bilan)
   2. Tahliliy izoh: aniqlanmish muammolar, o'nersiz xarajatlar
   3. Tavsilot: ruhlantiruvchi gap, ijobiy natijalar
   4. Rekomendatsiya: konkret harakat yoki tavsiya

3️⃣ AVTOMATIK KIRITISH ANIQLANISHI:
   • "25 mingga kofe oldim" → xarajat, Oziq-ovqat kategoriyasi
   • "100 ming qarz berdim" → qarz, Boshqa kategoriyasi
   • "1.5 million maosh oldim" → daromad, Maosh kategoriyasi

4️⃣ REPLY TIZIMI:
   • "ha", "go", "ok" → navbatdagi bosqichni boshlash
   • "yo'q", "bekor" → boshqa yechimni taklif qilish

5️⃣ SHAXSIYLASHTIRISH:
   • Foydalanuvchi ismi ({user_name}), do'stona ton
   • "Salom, {user_name}! Bugun balansingiz ____ so'm..."
   • Har safar tabriklash va motivatsiya berish

6️⃣ O'ZBEK TILIDA:
   • Qisqa, tushunarli, melodikli javoblar
   • Emojis haddan tashqari emas
   • "Men AI man" demang - odam sifatida gapirish

HOZIRGI FOYDALANUVCHI KONTEKSTI:
""" + context
        else:
            # Oddiy tarif uchun sodda system message
            system_message = """Siz Balans AI — moliyaviy yordamchi. Foydalanuvchilarga o'zbek tilida moliyaviy maslahatlar bering.
Agar foydalanuvchi balansi, statistikasi yoki moliyaviy holati haqida so'rasa, yuqorida berilgan ma'lumotlarni ishlating.
Javobni qisqa, tushunarli va foydali qiling. Raqamlarni aniq va tushunarli ko'rsating.
Javobni faqat o'zbek tilida bering.""" + "\n\n" + context
        
        # AI so'rovi yuborish
        full_prompt = prompt
        
        # REPLY SYSTEM - specific prompts
        if reply_type == 'yes':
            full_prompt = f"Foydalanuvchi 'HA' javob berdi - keyingi bosqichni boshlash. Qo'shimcha savol yoki tavsiya: {prompt}"
        elif reply_type == 'no':
            full_prompt = f"Foydalanuvchi 'YO'Q' javob berdi - boshqa yechimni taklif qilish. Javob: {prompt}"
        
        # Avtomatik kiritish aniqlanmasa, AI ga ayting
        if auto_transaction and auto_transaction.get('success'):
            full_prompt += f"\n\n(Avtomatik aniqlangan: {auto_transaction.get('message')})"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            max_tokens=1500,
            temperature=0.8,
            top_p=0.9
        )
        
        ai_response = response.choices[0].message.content
        
        # Avtomatik kiritish natijasini javobga qo'shish
        if auto_transaction and auto_transaction.get('success'):
            ai_response = f"✅ {auto_transaction.get('message')}\n\n{ai_response}"
        
        print(f"AI Response: {ai_response}")
        
        return jsonify({
            'success': True,
            'data': {
                'response': ai_response
            }
        })
    except Exception as e:
        print(f"AI advice xatolik: {e}")
        return jsonify({'success': False, 'message': f'AI xatoligi: {str(e)}'})

def detect_and_add_transaction(client, text, user_id):
    """Avtomatik kiritish aniqlanishi va qo'shilishi"""
    try:
        # GPT-o'zi multi-langual parse qilishi uchun
        import re
        
        # So'mli raqamlarni qidirish
        amount_patterns = [
            r'(\d+)\s*(?:ming|миң)',  # ming (1000)
            r'(\d+)\s*(?:million|миллион)',  # million
            r'(\d+)',  # ordinary numbers
        ]
        
        # Kategoriyalar
        categories = {
            'oziq': ['kofe', 'ovqat', 'restoran', 'supermarket', 'bazaar'],
            'transport': ['metro', 'taxi', 'transport', 'benzin'],
            'kiyim': ['kiyim', 'kiyinish', 'do\'kon'],
            'entertainment': ['kino', 'o\'yin', 'kulgi', 'sport'],
            'utilities': ['su', 'elektr', 'gaz', 'internet', 'telefon'],
            'health': ['doktor', 'dori', 'shifoxona'],
            'education': ['ta\'lim', 'kurs', 'kitob'],
        }
        
        # Kiritish tipa aniqlanishi
        transaction_type = 'expense'
        if any(word in text.lower() for word in ['daromad', 'maosh', 'oylik', 'pul', 'qarz berdi']):
            transaction_type = 'income' if 'daromad' in text.lower() or 'maosh' in text.lower() else 'debt'
        
        # Summa qidirish
        amount = 0
        for pattern in amount_patterns:
            match = re.search(pattern, text)
            if match:
                amount = int(match.group(1))
                if 'million' in pattern:
                    amount *= 1000000
                elif 'ming' in pattern:
                    amount *= 1000
                break
        
        if amount == 0:
            return {'success': False, 'message': 'Summa aniqlanmadi'}
        
        # Kategoriya aniqlanishi
        category = 'Boshqa'
        text_lower = text.lower()
        for cat, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                category = cat.capitalize()
                break
        
        # Tavsif
        description = f"AI orqali qo'shilgan: {text[:50]}"
        
        # Database ga qo'shish
        db.add_transaction(user_id, amount, category, description, transaction_type)
        
        return {
            'success': True,
            'message': f"{transaction_type.capitalize()} - {amount:,} so'm - {category}"
        }
        
    except Exception as e:
        print(f"Auto-detect error: {e}")
        return {'success': False, 'message': 'Aniqlab bo\'lmadi'}

@app.route('/api/realtime-session', methods=['POST'])
def create_realtime_session():
    """OpenAI Realtime session yaratish"""
    try:
        # Request dan user_id va voice ni olish (optional)
        user_id = request.json.get('user_id') if request.json else None
        voice = request.json.get('voice', 'marin') if request.json else 'marin'  # Default voice
        
        # User statistikalarini olish
        context = ""
        if user_id:
            try:
                # Balans va statistikani olish
                income_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'income'"
                expense_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'expense'"
                debt_query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = %s AND transaction_type = 'debt'"
                
                income_result = db.execute_query(income_query, (user_id,))
                expense_result = db.execute_query(expense_query, (user_id,))
                debt_result = db.execute_query(debt_query, (user_id,))
                
                total_income = income_result[0]['total'] if income_result else 0
                total_expense = expense_result[0]['total'] if expense_result else 0
                total_debt = debt_result[0]['total'] if debt_result else 0
                balance = total_income - total_expense - total_debt
                
                context = f"""
Foydalanuvchi moliyaviy ma'lumotlari:
- Joriy balans: {balance:,.0f} so'm
- Umumiy daromad: {total_income:,.0f} so'm
- Umumiy xarajat: {total_expense:,.0f} so'm
- Qarzlar: {total_debt:,.0f} so'm

Bu ma'lumotlarni foydalanuvchi so'raganda berib turing.
"""
            except Exception as e:
                print(f"Statistika olishda xatolik: {e}")
        
        # OpenAI Realtime session yaratish
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Professional Realtime API konfiguratsiyasi
        payload = {
            'model': 'gpt-4o-realtime-preview',
            'instructions': f'''Siz Balans AI — ovoz orqali jonli muloqot qiluvchi shaxsiy moliya yordamchisiz.
Siz foydalanuvchiga daromad, xarajat, byudjet va tejash bo'yicha yo'l-yo'riq berasiz.
Har doim tabiiy o'zbek tilida, qisqa, samimiy va ohangdor javob bering.
Gap 5–15 so'zdan oshmasin, ohangda tabassum sezilsin.
Kerak bo'lsa, foydalanuvchidan oddiy savol qaytaring.
"Men AI man" yoki "sun'iy intellektman" demang.
Sizni odam sifatida qabul qilishlari kerak.

{context}

Misol javoblar:
- Salom! Qandaysiz, bugun moliya haqida gaplashamizmi?
- Xa, tushunaman. Asosan qaysi toifadagi xarajat oshdi?
- Ajoyib! Bugun xarajatlaringiz kamroq ekan.''',
            'voice': voice  # Tanlangan ovoz
        }
        
        response = requests.post(
            'https://api.openai.com/v1/realtime/sessions',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # session_id va client_secret ni qaytarish
            session_id = data.get('id', '')
            
            # client_secret ni olish
            client_secret = ''
            if 'client_secret' in data:
                if isinstance(data['client_secret'], dict):
                    client_secret = data['client_secret'].get('value', '')
                else:
                    client_secret = str(data['client_secret'])
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'client_secret': client_secret
            })
        else:
            print(f"Session creation error: {response.text}")
            return jsonify({
                'success': False,
                'error': response.text
            }), response.status_code
            
    except Exception as e:
        print(f"Realtime session error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/add-test-data/<int:user_id>')
def add_test_data(user_id):
    """Test ma'lumotlari qo'shish"""
    try:
        # Foydalanuvchini yaratish
        db.add_user(user_id, 'Test User', 'Test', 'test_user')
        
        # Test tranzaksiyalar qo'shish
        test_transactions = [
            (user_id, 2000000, 'Ish haqi', 'Oylik maosh', 'income'),
            (user_id, 800000, 'Freelance', 'Loyiha', 'income'),
            (user_id, 600000, 'Bonus', 'Qo\'shimcha', 'income'),
            (user_id, 500000, 'Oziq-ovqat', 'Supermarket', 'expense'),
            (user_id, 200000, 'Transport', 'Metro', 'expense'),
            (user_id, 300000, 'Kiyim', 'Do\'kon', 'expense'),
            (user_id, 150000, 'O\'yin-kulgi', 'Kino', 'expense'),
            (user_id, 400000, 'Qarz', 'Do\'stga qarz', 'debt'),
            (user_id, 600000, 'Qarz', 'Bank krediti', 'debt'),
            (user_id, 250000, 'Oziq-ovqat', 'Restoran', 'expense')
        ]
        
        for transaction in test_transactions:
            db.add_transaction(*transaction)
        
        return jsonify({'success': True, 'message': 'Test ma\'lumotlari qo\'shildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ==================== CLICK.UZ TO'LOV TIZIMI ====================

# Click.uz log fayli uchun alohida handler
click_logger = logging.getLogger('click')
click_logger.setLevel(logging.INFO)

# /var/log/click.log ga yozish uchun handler (agar mumkin bo'lsa)
try:
    import sys
    # Production uchun /var/log/click.log
    click_file_handler = logging.FileHandler('/var/log/click.log', mode='a', encoding='utf-8')
except (PermissionError, FileNotFoundError):
    # Development uchun click_logs.txt
    click_file_handler = logging.FileHandler('click_logs.txt', mode='a', encoding='utf-8')

click_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
click_logger.addHandler(click_file_handler)
click_logger.propagate = True  # Render.com stdout'ga ham yozish uchun

def verify_click_signature(params, secret_key):
    """
    Click.uz sign_string ni tekshirish (MD5)
    MD5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
    """
    try:
        click_trans_id = str(params.get('click_trans_id', ''))
        service_id = str(params.get('service_id', ''))
        merchant_trans_id = str(params.get('merchant_trans_id', ''))
        amount = str(params.get('amount', ''))
        action = str(params.get('action', ''))
        sign_time = str(params.get('sign_time', ''))
        
        # MD5 hash yaratish
        sign_string = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
        
        received_sign = params.get('sign_string', '')
        
        return calculated_sign == received_sign
    except Exception as e:
        return False

@app.route('/api/click/prepare', methods=['GET', 'POST'])
def click_prepare():
    """
    Click.uz Prepare URL
    To'lovni boshlashdan oldin tekshiruv
    """
    # GET so'rov - debug/test uchun
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Click.uz Prepare Endpoint is ready",
            "method": "POST",
            "callback_url": "https://balansai.onrender.com/api/click/prepare",
            "description": "Bu endpoint Click.uz serveridan POST so'rovi bilan chaqiriladi"
        }), 200
    
    try:
        # Formadan ma'lumotlarni olish
        params = request.form.to_dict()
        
        # Minimal logging
        click_logger.info(f"PREPARE_REQUEST: {params}")
        
        # Majburiy maydonlarni tekshirish
        required_fields = ['click_trans_id', 'service_id', 'merchant_trans_id', 'amount', 'action', 'sign_time', 'sign_string']
        for field in required_fields:
            if field not in params:
                return jsonify({
                    "error": -8,
                    "error_note": f"Missing parameter: {field}"
                }), 400
        
        # Sign string ni tekshirish
        if not verify_click_signature(params, CLICK_SECRET_KEY):
            return jsonify({
                "error": -1,
                "error_note": "SIGN CHECK FAILED"
            }), 400
        
        # Service ID ni tekshirish
        if params.get('service_id') != CLICK_SERVICE_ID:
            return jsonify({
                "error": -5,
                "error_note": "Service ID not found"
            }), 400
        
        # Merchant ID ni tekshirish (agar mavjud bo'lsa)
        if 'merchant_id' in params and params.get('merchant_id') != CLICK_MERCHANT_ID:
            return jsonify({
                "error": -6,
                "error_note": "Merchant ID not found"
            }), 400
        
        # Summa tekshiruvi (minimal 1000 so'm)
        try:
            amount = float(params.get('amount', 0))
            if amount < 1000:
                return jsonify({
                    "error": -2,
                    "error_note": "Incorrect parameter amount"
                }), 400
        except ValueError:
            return jsonify({
                "error": -2,
                "error_note": "Incorrect parameter amount"
            }), 400
        
        # Action tekshiruvi (0 yoki 1 bo'lishi kerak)
        action = params.get('action')
        if action not in ['0', '1']:
            return jsonify({
                "error": -3,
                "error_note": "Action not found"
            }), 400
        
        # Merchant trans ID ni parse qilish (format: user_id_tariff_timestamp)
        merchant_trans_id = params.get('merchant_trans_id') or params.get('transaction_param', '')
        click_trans_id = params.get('click_trans_id')
        
        # Database update (synchronous, minimal) — click_trans_id ni darhol saqlash
        if merchant_trans_id and len(merchant_trans_id.split('_')) >= 2:
            try:
                db.update_payment_prepare(merchant_trans_id, click_trans_id)
            except Exception as _:
                # DB xatosi bo'lsa ham Click'ga darhol javob beramiz
                pass
        
        # Muvaffaqiyatli javob - Click.uz to'g'ri format talab qiladi
        merchant_prepare_id = int(datetime.now().timestamp())
        response = {
            "error": 0,
            "error_note": "Success",
            "click_trans_id": int(click_trans_id),
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": merchant_prepare_id
        }
        click_logger.info(f"PREPARE_RESPONSE: {response}")
        
        # JSON javobni tez qaytarish (timeout oldini olish uchun)
        return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Click Prepare error: {e}")
        return jsonify({
            "error": -9,
            "error_note": "Transaction not found"
        }), 500

@app.route('/api/click/complete', methods=['GET', 'POST'])
def click_complete():
    """
    Click.uz Complete URL
    To'lov yakunlangandan keyin natijani qaytarish
    """
    # GET so'rov - debug/test uchun
    if request.method == 'GET':
        return jsonify({
            "status": "ok",
            "message": "Click.uz Complete Endpoint is ready",
            "method": "POST",
            "callback_url": "https://balansai.onrender.com/api/click/complete",
            "description": "Bu endpoint Click.uz serveridan POST so'rovi bilan chaqiriladi"
        }), 200
    
    try:
        # Formadan ma'lumotlarni olish
        params = request.form.to_dict()
        
        # Debug logging
        click_logger.info(f"COMPLETE_REQUEST: {params}")
        logging.info(f"COMPLETE_ALL_PARAMS: {params}")
        logging.info(f"COMPLETE_KEYS: {list(params.keys())}")
        
        # Majburiy maydonlar
        required_fields = ['click_trans_id', 'amount', 'action', 'sign_time', 'sign_string', 'error']
        for field in required_fields:
            if field not in params:
                return jsonify({
                    "error": -8,
                    "error_note": f"Missing parameter: {field}"
                }), 400
        
        # Parametrlarni olish
        click_trans_id = params.get('click_trans_id', '')
        merchant_trans_id = params.get('merchant_trans_id', '') or params.get('transaction_param', '')
        amount = params.get('amount', '')
        action = params.get('action', '')
        sign_time = params.get('sign_time', '')
        received_sign = params.get('sign_string', '')
        
        logging.info(f"RAW_PARAMS: merchant_trans_id={params.get('merchant_trans_id')}, transaction_param={params.get('transaction_param')}, final={merchant_trans_id}")
        
        # Complete endpoint signature formulasi (Click.uz rasmiy hujjati)
        # MD5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
        service_id = params.get('service_id', CLICK_SERVICE_ID)
        merchant_prepare_id = params.get('merchant_prepare_id', '')
        
        # To'g'ri formula - merchant_prepare_id bilan
        sign_string_correct = f"{click_trans_id}{service_id}{CLICK_SECRET_KEY}{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
        calculated_sign_correct = hashlib.md5(sign_string_correct.encode('utf-8')).hexdigest()
        
        # Signature tekshiruvi
        signature_valid = (calculated_sign_correct == received_sign)
        
        logging.info(f"SIGNATURE: valid={signature_valid}, calculated={calculated_sign_correct}, received={received_sign}")
        logging.info(f"SIGN_PARAMS: click_trans_id={click_trans_id}, service_id={service_id}, merchant_trans_id={merchant_trans_id}, merchant_prepare_id={merchant_prepare_id}, amount={amount}, action={action}, sign_time={sign_time}")
        
        # Signature validation (strict, unless explicitly allowed via env)
        if not signature_valid:
            allow_debug = os.getenv('CLICK_ALLOW_DEBUG_SIGNATURE', 'false').lower() == 'true'
            logging.warning(f"Signature invalid: allow_debug={allow_debug}")
            if not allow_debug:
                return jsonify({"error": -1, "error_note": "SIGN CHECK FAILED"}), 400
        
        # Error code
        error_code = int(params.get('error', -1))
        logging.info(f"ERROR_CODE: {error_code}")
        
        if error_code == 0:
            # Darhol javob qaytarish (eng tez ko'rsatish)
            response = {
                "click_trans_id": int(click_trans_id),
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": int(datetime.now().timestamp()),
                "error": 0,
                "error_note": "Success"
            }
            click_logger.info(f"COMPLETE_RESPONSE: {response}")
            logging.info(f"✅ SENDING SUCCESS RESPONSE: {response}")
            
            # Background update (thread)
            def background_update():
                try:
                    local_merchant_trans_id = merchant_trans_id
                    local_click_trans_id = click_trans_id
                    
                    # merchant_trans_id topish
                    if not local_merchant_trans_id or not local_merchant_trans_id.strip():
                        payment = db.get_payment_by_click_trans_id(local_click_trans_id)
                        if payment and payment.get('merchant_trans_id'):
                            local_merchant_trans_id = payment['merchant_trans_id']
                        else:
                            # Oxirgi pending topish
                            query = "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC LIMIT 1"
                            result = db.execute_query(query)
                            if result and len(result) > 0:
                                local_merchant_trans_id = result[0].get('merchant_trans_id', '')
                                if local_merchant_trans_id:
                                    db.update_payment_prepare(local_merchant_trans_id, local_click_trans_id)
                    
                    if local_merchant_trans_id and local_merchant_trans_id.strip():
                        parts = local_merchant_trans_id.split('_')
                        if len(parts) >= 2:
                            user_id = int(parts[0])
                            tariff = parts[1].upper()
                            months = 1
                            if len(parts) >= 3 and parts[2].isdigit():
                                months = int(parts[2])
                            db.update_payment_complete(local_merchant_trans_id, status='confirmed', error_code=error_code, error_note='Success')
                            db.activate_tariff(user_id, tariff, months)
                            logging.info(f"✅ Background: {local_merchant_trans_id} - activated")
                except Exception as e:
                    logging.error(f"❌ Background error: {e}")
            
            thread = threading.Thread(target=background_update)
            thread.daemon = True
            thread.start()
            
            return jsonify(response), 200
        else:
            # To'lov muvaffaqiyatsiz - background'da update
            def bg_fail_update():
                try:
                    db.update_payment_complete(merchant_trans_id, status='failed', error_code=error_code, error_note='Transaction cancelled')
                except:
                    pass
            thread = threading.Thread(target=bg_fail_update)
            thread.daemon = True
            thread.start()
            
            response = {
                "click_trans_id": int(click_trans_id),
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": int(datetime.now().timestamp()),
                "error": error_code,
                "error_note": "Transaction cancelled"
            }
            click_logger.info(f"COMPLETE_RESPONSE_FAILED: {response}")
            return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Click Complete error: {e}")
        return jsonify({
            "error": -9,
            "error_note": "Transaction not found"
        }), 500

@app.route('/api/payment-history/<int:user_id>', methods=['GET'])
def get_payment_history(user_id):
    """
    Foydalanuvchi to'lovlari tarixini olish
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        payments = db.get_user_payments(user_id, limit)
        
        return jsonify({
            'success': True,
            'payments': payments
        }), 200
    except Exception as e:
        logging.error(f"Get payment history error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/create-payment', methods=['POST'])
def create_payment():
    """
    Yangi to'lov yozuvi yaratish (frontend dan chaqiriladi)
    """
    try:
        data = request.json
        user_id = data.get('user_id')
        tariff = data.get('tariff')
        amount = data.get('amount')
        months = data.get('months', 1)
        payment_method = data.get('payment_method', 'click')
        
        # Merchant trans ID yaratish
        import time
        timestamp = int(time.time())
        merchant_trans_id = f"{user_id}_{tariff.upper()}_{months}_{timestamp}"
        
        # Database'ga yozish
        db.create_payment_record(user_id, merchant_trans_id, amount, tariff, payment_method)
        
        logging.info(f"Payment record created: {merchant_trans_id}")
        
        return jsonify({
            'success': True,
            'merchant_trans_id': merchant_trans_id,
            'message': 'To\'lov yozuvi yaratildi'
        }), 200
    except Exception as e:
        logging.error(f"Create payment error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/click/manual-complete/<merchant_trans_id>', methods=['POST'])
def manual_complete_payment(merchant_trans_id):
    """
    Manual to'lovni confirmed qilish (debug uchun)
    Faqat production'da ishlatilmagan bo'lishi kerak
    """
    try:
        # merchant_trans_id format: {user_id}_{tariff}_{months}_{timestamp}
        parts = merchant_trans_id.split('_')
        
        if len(parts) >= 2:
            user_id = int(parts[0])
            tariff = parts[1].upper()
            months = 1
            if len(parts) >= 3 and parts[2].isdigit():
                months = int(parts[2])
            
            # Database'da to'lovni confirmed holatiga o'tkazish
            db.update_payment_complete(merchant_trans_id, status='confirmed', error_code=0, error_note='Manually completed')
            
            # Foydalanuvchi tarifini faollashtirish
            db.activate_tariff(user_id, tariff, months)
            
            return jsonify({
                'success': True,
                'message': f'Tariff activated: user_id={user_id}, tariff={tariff}, months={months}',
                'merchant_trans_id': merchant_trans_id
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid merchant_trans_id format'
            }), 400
            
    except Exception as e:
        logging.error(f"Manual complete error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== CLICK.UZ END ====================

if __name__ == '__main__':
    # Database jadvallarini yaratish
    try:
        db.create_ai_requests_table()
        db.create_goals_table()
        db.create_payments_table()
        print("✅ Database jadvallari yaratildi")
    except Exception as e:
        print(f"❌ Database xatoligi: {e}")
    
    # Flask app ishga tushirish
    port = int(os.environ.get('PORT', 8081))
    print(f"🚀 Flask app ishga tushmoqda: http://localhost:{port}")
    print(f"🔐 Click.uz endpoints:")
    print(f"   - Prepare: https://balansai.onrender.com/api/click/prepare")
    print(f"   - Complete: https://balansai.onrender.com/api/click/complete")
    print(f"📋 Click credentials:")
    print(f"   - Service ID: {CLICK_SERVICE_ID}")
    print(f"   - Merchant ID: {CLICK_MERCHANT_ID}")
    print(f"   - Merchant User ID: {CLICK_MERCHANT_USER_ID}")
    print(f"💳 Merchant Trans ID format: user_id_tariff_months_timestamp")
    print(f"   Example: 123456_PLUS_1_1730034567")
    print(f"✅ Click.uz integratsiyasi tayyor!")
    app.run(host='0.0.0.0', port=port, debug=False)