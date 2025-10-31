import pymysql
import pymysql.cursors
from config import DB_CONFIG
import logging
import threading
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.connection_config = DB_CONFIG.copy()
        self.connection_config.update({
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': True
        })
        self.lock = threading.Lock()
        logging.info("Ma'lumotlar bazasi konfiguratsiyasi yaratildi")
    
    def connect(self):
        """Ma'lumotlar bazasiga ulanish imkoniyatini tekshirish"""
        try:
            # Render.com uchun max_connections ni kamaytiramiz
            config = self.connection_config.copy()
            config['connect_timeout'] = 10
            config['read_timeout'] = 10
            config['write_timeout'] = 10
            
            connection = pymysql.connect(**config)
            connection.close()
            logging.info("Ma'lumotlar bazasiga ulanish muvaffaqiyatli")
            return True
        except Exception as e:
            logging.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Context manager orqali connection olish"""
        connection = None
        try:
            connection = pymysql.connect(**self.connection_config)
            yield connection
        except Exception as e:
            logging.error(f"Connection olishda xatolik: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
    
    def disconnect(self):
        """Disconnect funksiyasi (PyMySQL da kerak emas)"""
        logging.info("Database disconnect chaqirildi")
    
    def execute_query(self, query, params=None):
        """Query bajarish"""
        try:
            with self.lock:
                with self.get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(query, params)
                        
                        if query.strip().upper().startswith('SELECT'):
                            result = cursor.fetchall()
                        else:
                            connection.commit()
                            result = cursor.rowcount
                        
                        return result
        except Exception as e:
            logging.error(f"Query bajarishda xatolik: {e}")
            return None
    
    def get_user_data(self, user_id):
        """Foydalanuvchi ma'lumotlarini olish"""
        query = "SELECT * FROM users WHERE user_id = %s"
        return self.execute_query(query, (user_id,))
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Yangi foydalanuvchi qo'shish"""
        query = """
        INSERT INTO users (user_id, username, first_name, last_name, tariff, created_at) 
        VALUES (%s, %s, %s, %s, 'Plus', NOW())
        ON DUPLICATE KEY UPDATE 
        username = VALUES(username), 
        first_name = VALUES(first_name), 
        last_name = VALUES(last_name)
        """
        return self.execute_query(query, (user_id, username, first_name, last_name))
    
    def update_user_info(self, user_id, username=None, first_name=None, last_name=None):
        """Foydalanuvchi ma'lumotlarini yangilash"""
        query = """
        UPDATE users 
        SET username = %s, first_name = %s, last_name = %s 
        WHERE user_id = %s
        """
        return self.execute_query(query, (username, first_name, last_name, user_id))
    
    def get_transactions(self, user_id, limit=50):
        """Tranzaksiyalarni olish"""
        query = """
        SELECT * FROM transactions 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    def get_todos(self, user_id):
        """To-Do vazifalarni olish"""
        query = """
        SELECT * FROM todos 
        WHERE user_id = %s 
        ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))
    
    def get_goals(self, user_id):
        """Maqsadlarni olish"""
        query = """
        SELECT * FROM goals 
        WHERE user_id = %s 
        ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))
    
    def add_transaction(self, user_id, amount, category, description, transaction_type):
        """Tranzaksiya qo'shish"""
        query = """
        INSERT INTO transactions (user_id, amount, category, description, transaction_type)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, amount, category, description, transaction_type))
    
    def update_transaction(self, transaction_id, amount, category, description):
        """Tranzaksiyani yangilash"""
        query = """
        UPDATE transactions 
        SET amount = %s, category = %s, description = %s
        WHERE id = %s
        """
        return self.execute_query(query, (amount, category, description, transaction_id))
    
    def delete_transaction(self, transaction_id):
        """Tranzaksiyani o'chirish"""
        query = "DELETE FROM transactions WHERE id = %s"
        return self.execute_query(query, (transaction_id,))
    
    def add_todo(self, user_id, title, description, due_date=None):
        """Todo qo'shish"""
        query = """
        INSERT INTO todos (user_id, title, description, due_date)
        VALUES (%s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, title, description, due_date))
    
    def update_todo(self, todo_id, title, description, due_date=None, is_completed=False):
        """Todo yangilash"""
        query = """
        UPDATE todos 
        SET title = %s, description = %s, due_date = %s, is_completed = %s
        WHERE id = %s
        """
        return self.execute_query(query, (title, description, due_date, is_completed, todo_id))
    
    def delete_todo(self, todo_id):
        """Todo o'chirish"""
        query = "DELETE FROM todos WHERE id = %s"
        return self.execute_query(query, (todo_id,))
    
    def add_goal(self, user_id, title, description, target_amount=None, target_date=None):
        """Maqsad qo'shish"""
        query = """
        INSERT INTO goals (user_id, title, description, target_amount, target_date)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, title, description, target_amount, target_date))
    
    def update_goal(self, goal_id, title, description, target_amount=None, target_date=None, current_progress=None):
        """Maqsadni yangilash"""
        query = """
        UPDATE goals 
        SET title = %s, description = %s, target_amount = %s, target_date = %s, current_progress = %s
        WHERE id = %s
        """
        return self.execute_query(query, (title, description, target_amount, target_date, current_progress, goal_id))
    
    def delete_goal(self, goal_id):
        """Maqsadni o'chirish"""
        query = "DELETE FROM goals WHERE id = %s"
        return self.execute_query(query, (goal_id,))
    
    def create_ai_requests_table(self):
        """AI so'rovlar jadvali yaratish"""
        query = """
        CREATE TABLE IF NOT EXISTS ai_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            request_type VARCHAR(50) NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_request_type (request_type),
            INDEX idx_created_at (created_at)
        )
        """
        return self.execute_query(query)
    
    def create_goals_table(self):
        """Maqsadlar jadvalini yaratish"""
        query = """
        CREATE TABLE IF NOT EXISTS goals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name VARCHAR(255) NOT NULL,
            target_amount DECIMAL(15,2) NOT NULL,
            current_amount DECIMAL(15,2) DEFAULT 0,
            deadline DATE NOT NULL,
            category VARCHAR(100) NOT NULL,
            status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_status (status),
            INDEX idx_deadline (deadline)
        )
        """
        return self.execute_query(query)
    
    def create_payments_table(self):
        """To'lovlar jadvalini yaratish"""
        try:
            # Avval eski jadvalni tekshirish va o'chirish (agar kerak bo'lsa)
            try:
                self.execute_query("DROP TABLE IF EXISTS payments")
                logging.info("Eski payments jadvali o'chirildi")
            except:
                pass
            
            # Yangi jadvalni yaratish
            query = """
            CREATE TABLE payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                click_trans_id VARCHAR(100) UNIQUE,
                merchant_trans_id VARCHAR(255) NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                tariff VARCHAR(50) NOT NULL,
                payment_method ENUM('click', 'payme', 'test') DEFAULT 'click',
                status ENUM('pending', 'prepared', 'confirmed', 'cancelled', 'failed') DEFAULT 'pending',
                error_code INT DEFAULT 0,
                error_note VARCHAR(255),
                prepare_time TIMESTAMP NULL,
                complete_time TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_click_trans_id (click_trans_id),
                INDEX idx_merchant_trans_id (merchant_trans_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            )
            """
            result = self.execute_query(query)
            logging.info("Payments jadvali yaratildi")
            return result
        except Exception as e:
            logging.error(f"Payments jadvali yaratishda xatolik: {e}")
            # Agar jadval allaqachon mavjud bo'lsa, xato bermaslik
            return None
    
    def create_payment_record(self, user_id, merchant_trans_id, amount, tariff, payment_method='click'):
        """Yangi to'lov yozuvi yaratish"""
        query = """
        INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        """
        return self.execute_query(query, (user_id, merchant_trans_id, amount, tariff, payment_method))
    
    def update_payment_prepare(self, merchant_trans_id, click_trans_id):
        """To'lov prepare holatini yangilash (UZT vaqti bilan)"""
        from datetime import datetime, timedelta
        # Uzbekistan vaqti (UTC+5)
        uzb_time = datetime.now() + timedelta(hours=5)
        query = """
        UPDATE payments 
        SET click_trans_id = %s, 
            status = 'prepared',
            prepare_time = %s
        WHERE merchant_trans_id = %s
        """
        return self.execute_query(query, (click_trans_id, uzb_time, merchant_trans_id))
    
    def update_payment_complete(self, merchant_trans_id, status='confirmed', error_code=0, error_note='Success'):
        """To'lov complete holatini yangilash (UZT vaqti bilan)"""
        from datetime import datetime, timedelta
        # Uzbekistan vaqti (UTC+5)
        uzb_time = datetime.now() + timedelta(hours=5)
        query = """
        UPDATE payments 
        SET status = %s,
            error_code = %s,
            error_note = %s,
            complete_time = %s
        WHERE merchant_trans_id = %s
        """
        return self.execute_query(query, (status, error_code, error_note, uzb_time, merchant_trans_id))
    
    def get_payment_by_merchant_trans_id(self, merchant_trans_id):
        """Merchant trans ID bo'yicha to'lovni olish"""
        query = "SELECT * FROM payments WHERE merchant_trans_id = %s"
        result = self.execute_query(query, (merchant_trans_id,))
        return result[0] if result else None
    
    def get_payment_by_click_trans_id(self, click_trans_id):
        """Click trans ID bo'yicha to'lovni olish"""
        query = "SELECT * FROM payments WHERE click_trans_id = %s"
        result = self.execute_query(query, (click_trans_id,))
        return result[0] if result else None
    
    def get_user_payments(self, user_id, limit=10):
        """Foydalanuvchi to'lovlari tarixini olish"""
        query = """
        SELECT * FROM payments 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))
    
    def activate_tariff(self, user_id, tariff, months=1):
        """Tarifni faollashtirish va muddatini belgilash - eng yuqori tarifni saqlaydi"""
        from datetime import datetime, timedelta
        import logging
        
        expires_at = datetime.now() + timedelta(days=30 * months)
        
        # Tarif darajalari
        tariff_priority = {
            'PRO': 3,
            'Pro': 3,
            'PLUS': 2,
            'Plus': 2,
            'Bepul': 1,
            'FREE': 1
        }
        
        # Joriy tarifni olish
        current_query = "SELECT tariff FROM users WHERE user_id = %s"
        current_result = self.execute_query(current_query, (user_id,))
        current_tariff = None
        if current_result:
            current_tariff = current_result[0].get('tariff')
        
        # Eng yuqori tarifni aniqlash - yangi tarifni sotib olganda har doim yangilash
        final_tariff = tariff
        if current_tariff:
            current_priority = tariff_priority.get(current_tariff, 0)
            new_priority = tariff_priority.get(tariff, 0)
            # Agar joriy tarif yuqorida bo'lsa, uni saqlash
            if current_priority > new_priority:
                final_tariff = current_tariff
                logging.info(f"⚠️ activate_tariff: Keeping higher priority tariff: {current_tariff} > {tariff}")
            elif new_priority >= current_priority:
                # Yangi tarif yuqori yoki teng bo'lsa, yangilash
                final_tariff = tariff
                logging.info(f"✅ activate_tariff: Updating tariff: {current_tariff} → {tariff}")
        
        # 1. Users jadvalini yangilash (eng yuqori tarif bilan)
        query = """
        UPDATE users 
        SET tariff = %s,
            tariff_expires_at = %s,
            updated_at = NOW()
        WHERE user_id = %s
        """
        result = self.execute_query(query, (final_tariff, expires_at, user_id))
        logging.info(f"✅ activate_tariff: Updated users table for user_id={user_id}, tariff={final_tariff}, expires_at={expires_at}")
        
        # 2. User_subscriptions jadvaliga qo'shish (agar mavjud bo'lsa)
        # Avval user'ni users jadvalida mavjudligini tekshiramiz
        try:
            # User mavjudligini tekshirish
            user_check = self.get_user_data(user_id)
            if not user_check or len(user_check) == 0:
                # Agar user mavjud bo'lmasa, yaratamiz
                try:
                    self.add_user(user_id)
                    logging.info(f"✅ Created user: {user_id}")
                except Exception as create_err:
                    logging.warning(f"⚠️ Could not create user: {create_err}")
            
            # Jadval mavjudligini tekshirish
            check_query = """
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'user_subscriptions'
            """
            check_result = self.execute_query(check_query)
            
            if check_result and check_result[0]['count'] > 0:
                # Jadval mavjud - yangilash (to'g'ri ustun nomlari bilan)
                subscription_query = """
                INSERT INTO user_subscriptions (user_id, tariff, expires_at, is_active, created_at)
                VALUES (%s, %s, %s, 1, NOW())
                ON DUPLICATE KEY UPDATE 
                    tariff = VALUES(tariff),
                    expires_at = VALUES(expires_at),
                    is_active = 1
                """
                self.execute_query(subscription_query, (user_id, final_tariff, expires_at))
                logging.info(f"✅ activate_tariff: Updated user_subscriptions for user_id={user_id}, tariff={final_tariff}")
            else:
                logging.info(f"⚠️ user_subscriptions table not found, skipping subscription update")
        except Exception as sub_err:
            # Agar jadval mavjud bo'lmasa yoki ustunlar noto'g'ri bo'lsa, xatolikni ignore qilamiz
            logging.warning(f"⚠️ user_subscriptions error (ignored): {sub_err}")
        
        return result
    
    def get_user_tariff(self, user_id):
        """Foydalanuvchi tarifini olish - eng yuqori aktiv obunani qaytaradi"""
        from datetime import datetime
        
        # Tarif darajalari (yuqoridan pastga)
        tariff_priority = {
            'PRO': 3,
            'Pro': 3,
            'PLUS': 2,
            'Plus': 2,
            'Bepul': 1,
            'FREE': 1
        }
        
        # 1. Avval users jadvalidan o'qish
        query = "SELECT tariff, tariff_expires_at FROM users WHERE user_id = %s"
        result = self.execute_query(query, (user_id,))
        user_tariff = None
        if result:
            user = result[0]
            expires_at = user.get('tariff_expires_at')
            # Agar muddat o'tmagan bo'lsa
            if not expires_at or expires_at > datetime.now():
                user_tariff = user.get('tariff')
        
        # 2. User_subscriptions jadvalidan eng yuqori aktiv obunani topish
        try:
            subscription_query = """
            SELECT tariff, expires_at 
            FROM user_subscriptions 
            WHERE user_id = %s AND is_active = 1 AND expires_at > NOW()
            ORDER BY 
                CASE tariff
                    WHEN 'PRO' THEN 3
                    WHEN 'Plus' THEN 2
                    WHEN 'PLUS' THEN 2
                    WHEN 'Bepul' THEN 1
                    ELSE 0
                END DESC,
                expires_at DESC
            LIMIT 1
            """
            subscription_result = self.execute_query(subscription_query, (user_id,))
            
            if subscription_result:
                subscription_tariff = subscription_result[0].get('tariff')
                # Eng yuqori tarifni tanlash
                if user_tariff:
                    user_priority = tariff_priority.get(user_tariff, 0)
                    sub_priority = tariff_priority.get(subscription_tariff, 0)
                    if sub_priority > user_priority:
                        user_tariff = subscription_tariff
                else:
                    user_tariff = subscription_tariff
        except Exception as e:
            logging.warning(f"⚠️ Could not check user_subscriptions: {e}")
        
        # 3. Users jadvalidagi tarifni yangilash (eng yuqori bilan)
        if user_tariff:
            # Agar users jadvalidagi tarif pastroq bo'lsa, yangilash
            current_query = "SELECT tariff FROM users WHERE user_id = %s"
            current_result = self.execute_query(current_query, (user_id,))
            if current_result:
                current_tariff = current_result[0].get('tariff')
                current_priority = tariff_priority.get(current_tariff, 0)
                new_priority = tariff_priority.get(user_tariff, 0)
                
                if new_priority > current_priority:
                    # Eng yuqori tarifni saqlash
                    update_query = "UPDATE users SET tariff = %s, updated_at = NOW() WHERE user_id = %s"
                    self.execute_query(update_query, (user_tariff, user_id))
        
        return user_tariff or 'Bepul'  # Default: Bepul
    
    def update_user_tariff(self, user_id, tariff, expires_at=None):
        """Foydalanuvchi tarifini yangilash"""
        query = """
        UPDATE users 
        SET tariff = %s 
        WHERE user_id = %s
        """
        return self.execute_query(query, (tariff, user_id))
    
    def get_monthly_transaction_count(self, user_id):
        """Oylik tranzaksiyalar sonini olish"""
        from datetime import datetime, timedelta
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        query = """
        SELECT COUNT(*) as count FROM transactions 
        WHERE user_id = %s AND created_at >= %s
        """
        result = self.execute_query(query, (user_id, start_of_month))
        return result[0]['count'] if result else 0
    
    def get_debts_detailed(self, user_id):
        """Batafsil qarzlar ma'lumotlarini olish"""
        query = """
        SELECT 
            id,
            amount,
            category,
            description,
            created_at,
            CASE 
                WHEN amount > 0 THEN 'bergan'
                ELSE 'olgan'
            END as debt_type,
            ABS(amount) as debt_amount
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'debt'
        ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))
    
    def get_debt_summary(self, user_id):
        """Qarzlar xulosasi"""
        query = """
        SELECT 
            COUNT(*) as total_debts,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_given,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_received,
            SUM(amount) as net_balance
        FROM transactions 
        WHERE user_id = %s AND transaction_type = 'debt'
        """
        result = self.execute_query(query, (user_id,))
        return result[0] if result else {
            'total_debts': 0,
            'total_given': 0,
            'total_received': 0,
            'net_balance': 0
        }

# Global database instance
db = Database()

# AI requests jadvali yaratish
try:
    db.create_ai_requests_table()
except:
    pass  # Jadval allaqachon mavjud bo'lsa
