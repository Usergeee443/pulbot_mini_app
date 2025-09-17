from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import logging
from database import db
from config import FLASK_HOST, FLASK_PORT, SECRET_KEY, TARIFF_LIMITS
from ai_service import ai_service
import json
from datetime import datetime

# Flask ilovasini yaratish
app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

# Logging sozlash
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    """Asosiy sahifa"""
    return redirect(url_for('miniapp'))

@app.route('/miniapp')
def miniapp():
    """Mini app asosiy sahifasi"""
    return render_template('index.html')

@app.route('/api/user/<int:user_id>')
def get_user_data(user_id):
    """Foydalanuvchi ma'lumotlarini olish"""
    try:
        user_data = db.get_user_data(user_id)
        if user_data:
            return jsonify({'success': True, 'data': user_data[0]})
        return jsonify({'success': False, 'message': 'Foydalanuvchi topilmadi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transactions/<int:user_id>')
def get_transactions(user_id):
    """Tranzaksiyalarni olish"""
    try:
        transactions = db.get_transactions(user_id)
        return jsonify({'success': True, 'data': transactions or []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    """Tranzaksiya qo'shish"""
    try:
        data = request.get_json()
        user_id = data['user_id']
        
        # Limitni tekshirish
        tariff = db.get_user_tariff(user_id)
        limits = TARIFF_LIMITS[tariff]
        
        if limits['transactions_per_month'] != -1:
            monthly_count = db.get_monthly_transaction_count(user_id)
            if monthly_count >= limits['transactions_per_month']:
                return jsonify({
                    'success': False, 
                    'message': f'Oylik limit tugadi ({monthly_count}/{limits["transactions_per_month"]}). Premium ga o\'ting!',
                    'limit_exceeded': True
                })
        
        result = db.add_transaction(
            user_id,
            data['amount'],
            data['category'],
            data.get('description', ''),
            data['transaction_type']
        )
        if result:
            return jsonify({'success': True, 'message': 'Tranzaksiya qo\'shildi'})
        return jsonify({'success': False, 'message': 'Xatolik yuz berdi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Tranzaksiyani yangilash"""
    try:
        data = request.get_json()
        result = db.update_transaction(
            transaction_id,
            data['amount'],
            data['category'],
            data.get('description', '')
        )
        if result:
            return jsonify({'success': True, 'message': 'Tranzaksiya yangilandi'})
        return jsonify({'success': False, 'message': 'Xatolik yuz berdi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Tranzaksiyani o'chirish"""
    try:
        result = db.delete_transaction(transaction_id)
        if result:
            return jsonify({'success': True, 'message': 'Tranzaksiya o\'chirildi'})
        return jsonify({'success': False, 'message': 'Xatolik yuz berdi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/statistics/<int:user_id>')
def get_statistics(user_id):
    """Moliyaviy statistikalarni olish"""
    try:
        # Tranzaksiyalarni olish
        transactions = db.get_transactions(user_id, 1000)  # Ko'proq ma'lumot olish
        
        if not transactions:
            return jsonify({
                'success': True, 
                'data': {
                    'total_income': 0,
                    'total_expense': 0,
                    'total_debt': 0,
                    'balance': 0,
                    'monthly_data': [],
                    'category_data': [],
                    'recent_transactions': []
                }
            })
        
        # Asosiy statistikalar
        total_income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
        total_expense = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
        total_debt = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'debt')
        balance = total_income - total_expense - total_debt
        
        # Oylik ma'lumotlar (so'nggi 12 oy)
        from collections import defaultdict
        monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0, 'debt': 0})
        
        for t in transactions:
            date_key = t['created_at'].strftime('%Y-%m')
            monthly_data[date_key][t['transaction_type']] += float(t['amount'])
        
        # Kategoriyalar bo'yicha ma'lumotlar
        category_data = defaultdict(lambda: {'income': 0, 'expense': 0, 'debt': 0})
        for t in transactions:
            category_data[t['category']][t['transaction_type']] += float(t['amount'])
        
        # So'nggi tranzaksiyalar
        recent_transactions = transactions[:10]
        
        return jsonify({
            'success': True,
            'data': {
                'total_income': total_income,
                'total_expense': total_expense,
                'total_debt': total_debt,
                'balance': balance,
                'monthly_data': [
                    {
                        'month': month,
                        'income': data['income'],
                        'expense': data['expense'],
                        'debt': data['debt']
                    } for month, data in sorted(monthly_data.items())[-12:]
                ],
                'category_data': [
                    {
                        'category': category,
                        'income': data['income'],
                        'expense': data['expense'],
                        'debt': data['debt'],
                        'total': data['income'] + data['expense'] + data['debt']
                    } for category, data in category_data.items()
                ],
                'recent_transactions': recent_transactions
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/debts/<int:user_id>')
def get_debts(user_id):
    """Batafsil qarzlar ro'yxatini olish"""
    try:
        # Batafsil qarzlar
        debts = db.get_debts_detailed(user_id)
        
        # Qarzlar xulosasi
        summary = db.get_debt_summary(user_id)
        
        return jsonify({
            'success': True, 
            'data': {
                'debts': debts or [],
                'summary': summary
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user/tariff/<int:user_id>')
def get_user_tariff(user_id):
    """Foydalanuvchi tarif ma'lumotlarini olish"""
    try:
        print(f"DEBUG: Tarif so'ralgan user_id: {user_id}")
        
        # To'g'ridan-to'g'ri ma'lumotlar bazasidan olish
        query = "SELECT user_id, tariff FROM users WHERE user_id = %s"
        raw_result = db.execute_query(query, (user_id,))
        print(f"DEBUG: Raw DB result: {raw_result}")
        
        tariff = db.get_user_tariff(user_id)
        print(f"DEBUG: get_user_tariff natija: {tariff}")
        
        limits = TARIFF_LIMITS[tariff]
        
        # Oylik tranzaksiyalar sonini hisoblash
        monthly_transactions = db.get_monthly_transaction_count(user_id)
        
        # AI so'rovlar sonini hisoblash
        from datetime import datetime, timedelta
        today = datetime.now().date()
        query = """
        SELECT COUNT(*) as count FROM ai_requests 
        WHERE user_id = %s AND DATE(created_at) = %s
        """
        ai_result = db.execute_query(query, (user_id, today))
        daily_ai_requests = ai_result[0]['count'] if ai_result else 0
        
        return jsonify({
            'success': True,
            'data': {
                'tariff': tariff,
                'limits': limits,
                'usage': {
                    'monthly_transactions': monthly_transactions,
                    'daily_ai_requests': daily_ai_requests
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user/upgrade', methods=['POST'])
def upgrade_user():
    """Foydalanuvchini Premium ga o'tkazish"""
    try:
        data = request.get_json()
        user_id = data['user_id']
        
        # 30 kunlik Premium
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=30)
        
        result = db.update_user_tariff(user_id, 'PREMIUM', expires_at)
        
        if result:
            return jsonify({
                'success': True, 
                'message': 'Premium tarifga muvaffaqiyatli o\'tkazildi',
                'expires_at': expires_at.isoformat()
            })
        return jsonify({'success': False, 'message': 'Xatolik yuz berdi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/analysis/<int:user_id>')
def get_ai_analysis(user_id):
    """AI tahlil so'rovi"""
    try:
        # Tranzaksiyalarni olish
        transactions = db.get_transactions(user_id, 1000)
        
        # AI tahlil qilish
        result = ai_service.analyze_financial_data(user_id, transactions)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/advice', methods=['POST'])
def get_ai_advice():
    """AI maslahat so'rovi"""
    try:
        data = request.get_json()
        user_id = data['user_id']
        category = data['category']
        amount = data['amount']
        
        result = ai_service.get_spending_advice(user_id, category, amount)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/report/<int:user_id>')
def get_ai_report(user_id):
    """AI hisobot yaratish"""
    try:
        result = ai_service.generate_financial_report(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/check-limits/<int:user_id>')
def check_user_limits(user_id):
    """Foydalanuvchi limitlarini tekshirish"""
    try:
        tariff = db.get_user_tariff(user_id)
        limits = TARIFF_LIMITS[tariff]
        
        # Tranzaksiyalar limiti
        monthly_transactions = db.get_monthly_transaction_count(user_id)
        can_add_transaction = (limits['transactions_per_month'] == -1 or 
                              monthly_transactions < limits['transactions_per_month'])
        
        # AI so'rovlar limiti
        can_use_ai, ai_message = ai_service.check_ai_limit(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'tariff': tariff,
                'can_add_transaction': can_add_transaction,
                'transactions_left': (limits['transactions_per_month'] - monthly_transactions 
                                    if limits['transactions_per_month'] != -1 else -1),
                'can_use_ai': can_use_ai,
                'ai_message': ai_message,
                'advanced_analytics': limits['advanced_analytics'],
                'export_data': limits['export_data']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/advanced-stats/<int:user_id>')
def get_advanced_statistics(user_id):
    """Kengaytirilgan statistikalar - eng ko'p/kam harajatlar, kunlik statistika"""
    try:
        # Barcha tranzaksiyalarni olish
        transactions = db.get_transactions(user_id, 1000)
        
        if not transactions:
            return jsonify({
                'success': True,
                'data': {
                    'highest_expense': None,
                    'lowest_expense': None,
                    'most_expensive_day': None,
                    'daily_stats': [],
                    'category_breakdown': [],
                    'weekly_comparison': []
                }
            })
        
        # Faqat xarajatlarni ajratish
        expenses = [t for t in transactions if t['transaction_type'] == 'expense']
        
        # Eng yuqori va eng past xarajat
        highest_expense = max(expenses, key=lambda x: x['amount']) if expenses else None
        lowest_expense = min(expenses, key=lambda x: x['amount']) if expenses else None
        
        # Kunlik statistika
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        daily_expenses = defaultdict(float)
        daily_income = defaultdict(float)
        category_totals = defaultdict(float)
        
        for t in transactions:
            date_str = t['created_at'].strftime('%Y-%m-%d')
            if t['transaction_type'] == 'expense':
                daily_expenses[date_str] += float(t['amount'])
                category_totals[t['category']] += float(t['amount'])
            elif t['transaction_type'] == 'income':
                daily_income[date_str] += float(t['amount'])
        
        # Eng ko'p harajat qilingan kun
        most_expensive_day = max(daily_expenses.items(), key=lambda x: x[1]) if daily_expenses else None
        
        # Oxirgi 7 kunlik statistika
        today = datetime.now().date()
        daily_stats = []
        
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            daily_stats.append({
                'date': date_str,
                'expenses': daily_expenses.get(date_str, 0),
                'income': daily_income.get(date_str, 0),
                'day_name': date.strftime('%A')
            })
        
        daily_stats.reverse()  # Eski kunlardan yangi kunlarga
        
        # Kategoriya bo'yicha taqsimot (eng ko'p 5 tasi)
        category_breakdown = sorted(
            [{'category': cat, 'amount': amount} for cat, amount in category_totals.items()],
            key=lambda x: x['amount'],
            reverse=True
        )[:5]
        
        return jsonify({
            'success': True,
            'data': {
                'highest_expense': {
                    'amount': float(highest_expense['amount']),
                    'category': highest_expense['category'],
                    'description': highest_expense['description'],
                    'date': highest_expense['created_at'].strftime('%Y-%m-%d')
                } if highest_expense else None,
                'lowest_expense': {
                    'amount': float(lowest_expense['amount']),
                    'category': lowest_expense['category'],
                    'description': lowest_expense['description'],
                    'date': lowest_expense['created_at'].strftime('%Y-%m-%d')
                } if lowest_expense else None,
                'most_expensive_day': {
                    'date': most_expensive_day[0],
                    'amount': most_expensive_day[1]
                } if most_expensive_day else None,
                'daily_stats': daily_stats,
                'category_breakdown': category_breakdown
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Ma'lumotlar bazasiga ulanish
    if db.connect():
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
    else:
        print("Ma'lumotlar bazasiga ulanib bo'lmadi!")
