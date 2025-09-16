from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import logging
from database import db
from config import FLASK_HOST, FLASK_PORT, SECRET_KEY
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
        result = db.add_transaction(
            data['user_id'],
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
    """Qarzlar ro'yxatini olish"""
    try:
        query = """
        SELECT * FROM transactions 
        WHERE user_id = %s AND transaction_type = 'debt'
        ORDER BY created_at DESC
        """
        debts = db.execute_query(query, (user_id,))
        return jsonify({'success': True, 'data': debts or []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Ma'lumotlar bazasiga ulanish
    if db.connect():
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
    else:
        print("Ma'lumotlar bazasiga ulanib bo'lmadi!")
