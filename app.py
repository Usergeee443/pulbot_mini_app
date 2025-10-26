from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import requests
from datetime import datetime, timedelta
from database import Database
from config import DB_CONFIG, TARIFF_LIMITS, OPENAI_API_KEY

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

@app.route('/payment')
def payment():
    """To'lov sahifasi"""
    return render_template('payment.html')

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
"""
            except Exception as e:
                print(f"Statistika olishda xatolik: {e}")
        
        # AI so'rovi yuborish
        full_prompt = context + "\n\nFoydalanuvchi savoli: " + prompt if context else prompt
        
        system_message = """Siz Balans AI — moliyaviy yordamchi. Foydalanuvchilarga o'zbek tilida moliyaviy maslahatlar bering.
Agar foydalanuvchi balansi, statistikasi yoki moliyaviy holati haqida so'rasa, yuqorida berilgan ma'lumotlarni ishlating.
Javobni qisqa, tushunarli va foydali qiling. Raqamlarni aniq va tushunarli ko'rsating.
Javobni faqat o'zbek tilida bering."""
        
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
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
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

if __name__ == '__main__':
    # Database jadvallarini yaratish
    try:
        db.create_ai_requests_table()
        db.create_goals_table()
        print("Database jadvallari yaratildi")
    except Exception as e:
        print(f"Database xatoligi: {e}")
    
    # Flask app ishga tushirish
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Flask app ishga tushmoqda: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)