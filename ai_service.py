import openai
from config import OPENAI_API_KEY, TARIFF_LIMITS
from database import db
import logging
from datetime import datetime, timedelta
import json

class AIService:
    def __init__(self):
        self.client = None
        
    def _get_client(self):
        """Lazy loading OpenAI client"""
        if self.client is None:
            try:
                self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                logging.error(f"OpenAI client yaratishda xatolik: {e}")
                self.client = None
        return self.client
        
    def check_ai_limit(self, user_id):
        """Foydalanuvchining AI so'rovlar limitini tekshirish"""
        try:
            # Foydalanuvchi ma'lumotlarini olish
            user_data = db.get_user_data(user_id)
            if not user_data:
                return False, "Foydalanuvchi topilmadi"
            
            user = user_data[0]
            tariff = user.get('tariff', 'FREE')
            daily_limit = TARIFF_LIMITS[tariff]['ai_requests_per_day']
            
            if daily_limit == -1:  # Unlimited
                return True, "Unlimited"
            
            # Bugungi AI so'rovlarni hisoblash
            today = datetime.now().date()
            query = """
            SELECT COUNT(*) as count FROM ai_requests 
            WHERE user_id = %s AND DATE(created_at) = %s
            """
            result = db.execute_query(query, (user_id, today))
            
            if result:
                daily_count = result[0]['count']
                if daily_count >= daily_limit:
                    return False, f"Kunlik limit tugadi ({daily_count}/{daily_limit})"
            
            return True, f"Qolgan so'rovlar: {daily_limit - (result[0]['count'] if result else 0)}"
            
        except Exception as e:
            logging.error(f"AI limit tekshirishda xatolik: {e}")
            return False, "Xatolik yuz berdi"
    
    def log_ai_request(self, user_id, request_type, prompt, response):
        """AI so'rovini loglash"""
        try:
            query = """
            INSERT INTO ai_requests (user_id, request_type, prompt, response, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """
            db.execute_query(query, (user_id, request_type, prompt, response, datetime.now()))
        except Exception as e:
            logging.error(f"AI so'rovni loglashda xatolik: {e}")
    
    def analyze_financial_data(self, user_id, transactions):
        """Moliyaviy ma'lumotlarni tahlil qilish"""
        try:
            # Limit tekshirish
            can_use, message = self.check_ai_limit(user_id)
            if not can_use:
                return {"success": False, "message": message}
            
            # Ma'lumotlarni tayyorlash
            if not transactions:
                return {"success": False, "message": "Tahlil qilish uchun tranzaksiyalar yo'q"}
            
            # Tranzaksiyalarni AI uchun formatlash
            data_summary = self.prepare_financial_summary(transactions)
            
            prompt = f"""
Sen professional moliyaviy maslahatchi san. Quyidagi moliyaviy ma'lumotlarni tahlil qil va o'zbek tilida javob ber:

{data_summary}

Iltimos quyidagilarni tahlil qil:
1. Xarajatlar tendentsiyasi
2. Eng ko'p xarajat qilinadigan kategoriyalar
3. Daromad va xarajat balansi
4. Moliyaviy maslahatlar
5. Keyingi oy uchun prognoz

Javobni aniq va tushunarli qilib ber, raqamlar bilan asoslab ber.
"""
            
            client = self._get_client()
            if not client:
                return {"success": False, "message": "AI xizmati vaqtincha ishlamayapti"}
                
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen professional moliyaviy maslahatchi san. O'zbek tilida javob ber."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # So'rovni loglash
            self.log_ai_request(user_id, "financial_analysis", prompt[:500], ai_response[:500])
            
            return {"success": True, "analysis": ai_response}
            
        except Exception as e:
            logging.error(f"AI tahlil qilishda xatolik: {e}")
            return {"success": False, "message": f"AI xatoligi: {str(e)}"}
    
    def get_spending_advice(self, user_id, category, amount):
        """Xarajatlar bo'yicha maslahat berish"""
        try:
            can_use, message = self.check_ai_limit(user_id)
            if not can_use:
                return {"success": False, "message": message}
            
            prompt = f"""
Foydalanuvchi "{category}" kategoriyasida {amount} so'm xarajat qilmoqchi. 
Bu xarajat haqida qisqa maslahat ber:
- Bu xarajat oqilona mi?
- Qanday tejash mumkin?
- Alternativ variantlar

O'zbek tilida 2-3 gapda javob ber.
"""
            
            client = self._get_client()
            if not client:
                return {"success": False, "message": "AI xizmati vaqtincha ishlamayapti"}
                
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen moliyaviy maslahatchi san. Qisqa va foydali maslahatlar ber."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            self.log_ai_request(user_id, "spending_advice", prompt, ai_response)
            
            return {"success": True, "advice": ai_response}
            
        except Exception as e:
            logging.error(f"AI maslahat berishda xatolik: {e}")
            return {"success": False, "message": f"Xatolik: {str(e)}"}
    
    def generate_financial_report(self, user_id, period="month"):
        """Moliyaviy hisobot yaratish"""
        try:
            can_use, message = self.check_ai_limit(user_id)
            if not can_use:
                return {"success": False, "message": message}
            
            # Foydalanuvchi tranzaksiyalarini olish
            transactions = db.get_transactions(user_id, 1000)
            if not transactions:
                return {"success": False, "message": "Hisobot uchun ma'lumotlar yo'q"}
            
            # Hisobot yaratish
            summary = self.prepare_financial_summary(transactions)
            
            prompt = f"""
Quyidagi moliyaviy ma'lumotlar asosida batafsil hisobot yarat:

{summary}

Hisobot quyidagi bo'limlarni o'z ichiga olsin:
1. 📊 Umumiy ko'rsatkichlar
2. 💰 Daromadlar tahlili  
3. 💸 Xarajatlar tahlili
4. 📈 Tendentsiyalar
5. 🎯 Tavsiyalar

Hisobotni professional va tushunarli qilib yoz. O'zbek tilida.
"""
            
            client = self._get_client()
            if not client:
                return {"success": False, "message": "AI xizmati vaqtincha ishlamayapti"}
                
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen professional moliyaviy hisobot tayyorlovchi san."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.5
            )
            
            ai_response = response.choices[0].message.content
            self.log_ai_request(user_id, "financial_report", prompt[:500], ai_response[:500])
            
            return {"success": True, "report": ai_response}
            
        except Exception as e:
            logging.error(f"AI hisobot yaratishda xatolik: {e}")
            return {"success": False, "message": f"Xatolik: {str(e)}"}
    
    def prepare_financial_summary(self, transactions):
        """Moliyaviy ma'lumotlarni AI uchun tayyorlash"""
        try:
            # Asosiy statistikalar
            total_income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
            total_expense = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
            total_debt = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'debt')
            
            # Kategoriyalar bo'yicha
            categories = {}
            for t in transactions:
                cat = t['category']
                if cat not in categories:
                    categories[cat] = {'income': 0, 'expense': 0, 'debt': 0}
                categories[cat][t['transaction_type']] += float(t['amount'])
            
            # Oxirgi 30 kunlik ma'lumotlar
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_transactions = [t for t in transactions 
                                 if datetime.strptime(str(t['created_at']), '%Y-%m-%d %H:%M:%S') >= thirty_days_ago]
            
            summary = f"""
Umumiy statistika:
- Jami daromad: {total_income:,.0f} so'm
- Jami xarajat: {total_expense:,.0f} so'm  
- Jami qarz: {total_debt:,.0f} so'm
- Balans: {total_income - total_expense - total_debt:,.0f} so'm
- Jami tranzaksiyalar: {len(transactions)}

Oxirgi 30 kun:
- Tranzaksiyalar soni: {len(recent_transactions)}

Eng faol kategoriyalar:
"""
            
            # Top 5 kategoriyalarni qo'shish
            sorted_categories = sorted(categories.items(), 
                                     key=lambda x: x[1]['income'] + x[1]['expense'] + x[1]['debt'], 
                                     reverse=True)[:5]
            
            for cat, amounts in sorted_categories:
                total_cat = amounts['income'] + amounts['expense'] + amounts['debt']
                summary += f"- {cat}: {total_cat:,.0f} so'm\n"
            
            return summary
            
        except Exception as e:
            logging.error(f"Financial summary tayyorlashda xatolik: {e}")
            return "Ma'lumotlarni tayyorlashda xatolik"

# Global AI service instance
ai_service = AIService()
