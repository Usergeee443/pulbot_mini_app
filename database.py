import logging
from contextlib import contextmanager
from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from config import DB_CONFIG


class Database:
    def __init__(self) -> None:
        self.connection_config = DB_CONFIG.copy()
        self.connection_config.update(
            {
                'charset': 'utf8mb4',
                'cursorclass': DictCursor,
                'autocommit': True,
            }
        )

    @contextmanager
    def _get_connection(self):
        connection = pymysql.connect(**self.connection_config)
        try:
            yield connection
        finally:
            connection.close()

    def _execute(self, query, params=None, fetchone=False, fetchall=False):
        with self._get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                if cursor.description:
                    result = cursor.fetchone() if fetchone else cursor.fetchall()
                    return result
                return cursor.rowcount

    def create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            tariff VARCHAR(50) DEFAULT 'Bepul',
            tariff_expires_at DATETIME NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self._execute(query)

    def create_payments_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            click_trans_id VARCHAR(100) UNIQUE,
            merchant_trans_id VARCHAR(255) NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            tariff VARCHAR(50) NOT NULL,
            package_code VARCHAR(50),
            payment_method ENUM('click', 'payme', 'test') DEFAULT 'click',
            status ENUM('pending', 'prepared', 'confirmed', 'cancelled', 'failed') DEFAULT 'pending',
            error_code INT DEFAULT 0,
            error_note VARCHAR(255),
            prepare_time TIMESTAMP NULL,
            complete_time TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_merchant_trans_id (merchant_trans_id)
        )
        """
        self._execute(query)

    def create_user_package_limits_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_package_limits (
            user_id BIGINT PRIMARY KEY,
            package_code VARCHAR(50) NOT NULL,
            text_limit INT NOT NULL,
            voice_limit INT NOT NULL,
            text_used INT DEFAULT 0,
            voice_used INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        self._execute(query)

    def create_plus_package_purchases_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS plus_package_purchases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            package_code VARCHAR(50) NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            merchant_trans_id VARCHAR(255) NOT NULL,
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_package (package_code)
        )
        """
        self._execute(query)

    def ensure_payments_package_column(self):
        try:
            self._execute("ALTER TABLE payments ADD COLUMN package_code VARCHAR(50) NULL")
        except Exception as exc:
            text = str(exc)
            if 'Duplicate column name' in text:
                logging.debug('payments.package_code already exists')
            elif 'Unknown table' in text or "doesn't exist" in text:
                logging.debug('payments table not found when adding package_code column')
            else:
                logging.debug(f'ensure_payments_package_column: {exc}')

    def create_payment_record(self, user_id, merchant_trans_id, amount, tariff, payment_method='click', package_code=None):
        if package_code:
            query = (
                "INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, package_code, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'pending')"
            )
            params = (user_id, merchant_trans_id, amount, tariff, payment_method, package_code)
        else:
            query = (
                "INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, status) "
                "VALUES (%s, %s, %s, %s, %s, 'pending')"
            )
            params = (user_id, merchant_trans_id, amount, tariff, payment_method)
        self._execute(query, params)

    def update_payment_prepare(self, merchant_trans_id, click_trans_id):
        query = (
            "UPDATE payments SET click_trans_id = %s, status = 'prepared', prepare_time = NOW() "
            "WHERE merchant_trans_id = %s"
        )
        self._execute(query, (click_trans_id, merchant_trans_id))

    def update_payment_complete(self, merchant_trans_id, status='confirmed', error_code=0, error_note='Success'):
        query = (
            "UPDATE payments SET status = %s, error_code = %s, error_note = %s, complete_time = NOW() "
            "WHERE merchant_trans_id = %s"
        )
        self._execute(query, (status, error_code, error_note, merchant_trans_id))

    def get_payment_by_click_trans_id(self, click_trans_id):
        query = "SELECT * FROM payments WHERE click_trans_id = %s"
        return self._execute(query, (click_trans_id,), fetchone=True)

    def assign_user_package(self, user_id, package_code, text_limit, voice_limit):
        query = """
        INSERT INTO user_package_limits (user_id, package_code, text_limit, voice_limit, text_used, voice_used)
        VALUES (%s, %s, %s, %s, 0, 0)
        ON DUPLICATE KEY UPDATE
            package_code = VALUES(package_code),
            text_limit = VALUES(text_limit),
            voice_limit = VALUES(voice_limit),
            text_used = 0,
            voice_used = 0,
            updated_at = CURRENT_TIMESTAMP
        """
        self._execute(query, (user_id, package_code, text_limit, voice_limit))

    def log_package_purchase(self, user_id, package_code, amount, merchant_trans_id):
        query = """
        INSERT INTO plus_package_purchases (user_id, package_code, amount, merchant_trans_id)
        VALUES (%s, %s, %s, %s)
        """
        self._execute(query, (user_id, package_code, amount, merchant_trans_id))

    def get_user_package_limits(self, user_id):
        query = "SELECT * FROM user_package_limits WHERE user_id = %s"
        return self._execute(query, (user_id,), fetchone=True)

    def get_last_payment(self, user_id, tariff_code):
        query = """
        SELECT amount, complete_time, created_at
        FROM payments
        WHERE user_id = %s AND tariff = %s AND status = 'confirmed'
        ORDER BY COALESCE(complete_time, created_at) DESC
        LIMIT 1
        """
        return self._execute(query, (user_id, tariff_code), fetchone=True)

    def activate_tariff(self, user_id, tariff, months=1):
        self.create_users_table()
        query = """
        INSERT INTO users (user_id, tariff, tariff_expires_at)
        VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s MONTH))
        ON DUPLICATE KEY UPDATE
            tariff = VALUES(tariff),
            tariff_expires_at = VALUES(tariff_expires_at),
            updated_at = CURRENT_TIMESTAMP
        """
        self._execute(query, (user_id, tariff, months))

    def get_user_tariff(self, user_id):
        self.create_users_table()
        query = "SELECT tariff, tariff_expires_at FROM users WHERE user_id = %s"
        row = self._execute(query, (user_id,), fetchone=True)
        if not row:
            return {'tariff': 'Bepul', 'expires_at': None}

        expires_at = row.get('tariff_expires_at')
        tariff = row.get('tariff') or 'Bepul'

        if expires_at and expires_at <= datetime.now():
            return {'tariff': 'Bepul', 'expires_at': expires_at}

        return {'tariff': tariff, 'expires_at': expires_at}
