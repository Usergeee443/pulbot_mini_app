import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool
from config import DB_CONFIG
import logging
import threading

class Database:
    def __init__(self):
        self.pool = None
        self.lock = threading.Lock()
        self._create_pool()
    
    def _create_pool(self):
        """Connection pool yaratish"""
        try:
            pool_config = DB_CONFIG.copy()
            pool_config.update({
                'pool_name': 'balans_ai_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                'autocommit': True
            })
            self.pool = MySQLConnectionPool(**pool_config)
            logging.info("Ma'lumotlar bazasi connection pool yaratildi")
        except Error as e:
            logging.error(f"Connection pool yaratishda xatolik: {e}")
    
    def connect(self):
        """Connection pool mavjudligini tekshirish"""
        return self.pool is not None
    
    def get_connection(self):
        """Pool dan connection olish"""
        try:
            if self.pool:
                return self.pool.get_connection()
        except Error as e:
            logging.error(f"Connection olishda xatolik: {e}")
        return None
    
    def disconnect(self):
        """Pool ni yopish"""
        if self.pool:
            try:
                # Pool ni to'g'ridan-to'g'ri yopib bo'lmaydi, lekin referensni o'chiramiz
                self.pool = None
                logging.info("Ma'lumotlar bazasi pool referensi o'chirildi")
            except Exception as e:
                logging.error(f"Pool yopishda xatolik: {e}")
    
    def execute_query(self, query, params=None):
        """Query bajarish"""
        connection = None
        cursor = None
        try:
            with self.lock:
                connection = self.get_connection()
                if not connection:
                    return None
                
                cursor = connection.cursor(dictionary=True)
                cursor.execute(query, params)
                
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall()
                else:
                    connection.commit()
                    result = cursor.rowcount
                
                return result
        except Error as e:
            logging.error(f"Query bajarishda xatolik: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
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
