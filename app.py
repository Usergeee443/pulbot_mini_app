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

@app.route('/api/charts/<int:user_id>')
def get_charts_data(user_id):
    """Grafiklar uchun ma'lumotlar"""
    try:
        # Oylik statistika (oxirgi 6 oy)
        monthly_query = """
        SELECT 
            DATE_FORMAT(created_at, '%Y-%m') as month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions 
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month
        """
        monthly_data = db.execute_query(monthly_query, (user_id,))
        
        # Haftalik statistika (oxirgi 4 hafta)
        weekly_query = """
        SELECT 
            YEARWEEK(created_at) as week,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions 
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 4 WEEK)
        GROUP BY YEARWEEK(created_at)
        ORDER BY week
        """
        weekly_data = db.execute_query(weekly_query, (user_id,))
        
        # Kunlik statistika (oxirgi 30 kun)
        daily_query = """
        SELECT 
            DATE(created_at) as date,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions 
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        daily_data = db.execute_query(daily_query, (user_id,))
        
        # Kategoriyalar bo'yicha taqsimot
        category_query = """
        SELECT 
            category,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
            COUNT(*) as count
        FROM transactions 
        WHERE user_id = %s
        GROUP BY category
        ORDER BY expense DESC
        LIMIT 10
        """
        category_data = db.execute_query(category_query, (user_id,))
        
        return jsonify({
            'monthly': monthly_data,
            'weekly': weekly_data,
            'daily': daily_data,
            'categories': category_data
        })
        
    except Exception as e:
        print(f"Charts data xatoligi: {e}")
        return jsonify({'error': 'Grafik ma\'lumotlari yuklanmadi'}), 500

@app.route('/add-test-data/<int:user_id>')
def add_test_data(user_id):
    """Test ma'lumotlari qo'shish"""
    try:
        # Test tranzaksiyalar qo'shish
        test_transactions = [
            (user_id, 'income', 500000, 'Ish haqi', 'Ish', '2024-09-20 10:00:00'),
            (user_id, 'expense', 50000, 'Oziq-ovqat', 'Oziq-ovqat', '2024-09-20 12:00:00'),
            (user_id, 'expense', 30000, 'Transport', 'Transport', '2024-09-20 18:00:00'),
            (user_id, 'income', 100000, 'Qo\'shimcha daromad', 'Qo\'shimcha', '2024-09-21 14:00:00'),
            (user_id, 'expense', 150000, 'Kiyim-kechak', 'Kiyim', '2024-09-21 16:00:00'),
            (user_id, 'expense', 25000, 'Internet', 'Kommunal', '2024-09-22 09:00:00'),
            (user_id, 'income', 75000, 'Freelance', 'Qo\'shimcha', '2024-09-22 20:00:00'),
            (user_id, 'expense', 80000, 'Restoran', 'Oziq-ovqat', '2024-09-23 19:00:00'),
            (user_id, 'expense', 40000, 'Benzin', 'Transport', '2024-09-23 21:00:00'),
            (user_id, 'income', 200000, 'Bonus', 'Ish', '2024-09-24 11:00:00')
        ]
        
        for transaction in test_transactions:
            query = """
            INSERT INTO transactions (user_id, type, amount, description, category, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            db.execute_query(query, transaction)
        
        # Test qarzlar qo'shish
        test_debts = [
            (user_id, 'Ahmad', 'Bergan qarz', 100000, '2024-09-25', '2024-10-25'),
            (user_id, 'Sardor', 'Olgan qarz', 50000, '2024-09-20', '2024-10-20')
        ]
        
        for debt in test_debts:
            query = """
            INSERT INTO debts (user_id, person_name, debt_type, amount, due_date, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """
            db.execute_query(query, debt)
        
        return jsonify({'success': True, 'message': 'Test ma\'lumotlari qo\'shildi'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Goals API endpoints
@app.route('/api/goals/<int:user_id>')
def get_goals(user_id):
    """Foydalanuvchi maqsadlarini olish"""
    try:
        query = """
        SELECT id, name, target_amount, current_amount, deadline, category, status, created_at
        FROM goals 
        WHERE user_id = %s 
        ORDER BY created_at DESC
        """
        goals = db.execute_query(query, (user_id,))
        
        return jsonify({
            'success': True,
            'goals': goals or []
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/goals/<int:user_id>', methods=['POST'])
def create_goal(user_id):
    """Yangi maqsad yaratish"""
    try:
        data = request.get_json()
        
        query = """
        INSERT INTO goals (user_id, name, target_amount, current_amount, deadline, category, status)
        VALUES (%s, %s, %s, 0, %s, %s, 'active')
        """
        db.execute_query(query, (
            user_id,
            data['name'],
            data['target_amount'],
            data['deadline'],
            data['category']
        ))
        
        return jsonify({'success': True, 'message': 'Maqsad yaratildi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/goals/<int:goal_id>', methods=['PUT'])
def update_goal(goal_id):
    """Maqsadni yangilash"""
    try:
        data = request.get_json()
        
        query = """
        UPDATE goals 
        SET name = %s, target_amount = %s, deadline = %s, category = %s
        WHERE id = %s
        """
        db.execute_query(query, (
            data['name'],
            data['target_amount'],
            data['deadline'],
            data['category'],
            goal_id
        ))
        
        return jsonify({'success': True, 'message': 'Maqsad yangilandi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/goals/<int:goal_id>/add', methods=['POST'])
def add_to_goal(goal_id):
    """Maqsadga pul qo'shish"""
    try:
        data = request.get_json()
        amount = data['amount']
        
        # Maqsadga pul qo'shish
        query = """
        UPDATE goals 
        SET current_amount = current_amount + %s
        WHERE id = %s
        """
        db.execute_query(query, (amount, goal_id))
        
        # Maqsad yakunlanganligini tekshirish
        check_query = """
        SELECT target_amount, current_amount 
        FROM goals 
        WHERE id = %s
        """
        result = db.execute_query(check_query, (goal_id,))
        
        if result and result[0]['current_amount'] >= result[0]['target_amount']:
            # Maqsadni yakunlangan deb belgilash
            complete_query = """
            UPDATE goals 
            SET status = 'completed' 
            WHERE id = %s
            """
            db.execute_query(complete_query, (goal_id,))
        
        return jsonify({'success': True, 'message': 'Pul qo\'shildi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    """Maqsadni o'chirish"""
    try:
        query = "DELETE FROM goals WHERE id = %s"
        db.execute_query(query, (goal_id,))
        
        return jsonify({'success': True, 'message': 'Maqsad o\'chirildi'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Ma'lumotlar bazasiga ulanish
    if db.connect():
        # Goals jadvalini yaratish
        db.create_goals_table()
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
    else:
        print("Ma'lumotlar bazasiga ulanib bo'lmadi!")
