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

# Global database instance
db = Database()
