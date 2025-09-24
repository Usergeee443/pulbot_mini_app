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
            connection = pymysql.connect(**self.connection_config)
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
        VALUES (%s, %s, %s, %s, 'PREMIUM', NOW())
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
    
    def get_user_tariff(self, user_id):
        """Foydalanuvchi tarifini olish"""
        query = "SELECT tariff FROM users WHERE user_id = %s"
        result = self.execute_query(query, (user_id,))
        if result:
            user = result[0]
            return user['tariff'] or 'FREE'
        return 'FREE'
    
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
