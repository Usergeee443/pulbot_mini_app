from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
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
    return render_template('index.html')

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
        limits = TARIFF_LIMITS.get(tariff, TARIFF_LIMITS['FREE'])
        
        return jsonify({
            'success': True,
            'data': {
                'tariff': tariff,
                'limits': limits
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/advice')
def get_ai_advice():
    """AI maslahat olish"""
    try:
        prompt = request.args.get('prompt', '')
        if not prompt:
            return jsonify({'success': False, 'message': 'Prompt kiritilmagan'})
        
        client = get_openai_client()
        if not client:
            return jsonify({'success': False, 'message': 'AI xizmati mavjud emas'})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Siz moliyaviy maslahatchi. Foydalanuvchilarga moliyaviy maslahatlar bering. Javobni o'zbek tilida bering."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({
            'success': True,
            'data': {
                'response': response.choices[0].message.content
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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
    app.run(host='0.0.0.0', port=port, debug=True)