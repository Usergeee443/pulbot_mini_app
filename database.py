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
        query = """
        CREATE TABLE IF NOT EXISTS payments (
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
        return self.execute_query(query)
    
    def create_payment_record(self, user_id, merchant_trans_id, amount, tariff, payment_method='click'):
        """Yangi to'lov yozuvi yaratish"""
        query = """
        INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        """
        return self.execute_query(query, (user_id, merchant_trans_id, amount, tariff, payment_method))
    
    def update_payment_prepare(self, merchant_trans_id, click_trans_id):
        """To'lov prepare holatini yangilash"""
        from datetime import datetime
        query = """
        UPDATE payments 
        SET click_trans_id = %s, 
            status = 'prepared',
            prepare_time = %s
        WHERE merchant_trans_id = %s
        """
        return self.execute_query(query, (click_trans_id, datetime.now(), merchant_trans_id))
    
    def update_payment_complete(self, merchant_trans_id, status='confirmed', error_code=0, error_note='Success'):
        """To'lov complete holatini yangilash"""
        from datetime import datetime
        query = """
        UPDATE payments 
        SET status = %s,
            error_code = %s,
            error_note = %s,
            complete_time = %s
        WHERE merchant_trans_id = %s
        """
        return self.execute_query(query, (status, error_code, error_note, datetime.now(), merchant_trans_id))
    
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
        """Tarifni faollashtirish va muddatini belgilash"""
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=30 * months)
        
        query = """
        UPDATE users 
        SET tariff = %s,
            tariff_expires_at = %s,
            updated_at = NOW()
        WHERE user_id = %s
        """
        return self.execute_query(query, (tariff, expires_at, user_id))
    
    def get_user_tariff(self, user_id):
        """Foydalanuvchi tarifini olish"""
        query = "SELECT tariff FROM users WHERE user_id = %s"
        result = self.execute_query(query, (user_id,))
        if result:
            user = result[0]
            return user['tariff'] or 'Plus'  # Default: Plus
        return 'Plus'  # Default: Plus
    
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
