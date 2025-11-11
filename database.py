import logging
from contextlib import contextmanager
from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from config import DB_CONFIG, PROMO_CODES


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
            original_amount DECIMAL(15,2),
            discount_amount DECIMAL(15,2) DEFAULT 0,
            discount_percent INT DEFAULT 0,
            promo_code VARCHAR(50),
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

    def ensure_payments_discount_columns(self):
        columns = [
            ("original_amount", "ADD COLUMN original_amount DECIMAL(15,2) NULL AFTER amount"),
            ("discount_amount", "ADD COLUMN discount_amount DECIMAL(15,2) DEFAULT 0 AFTER original_amount"),
            ("discount_percent", "ADD COLUMN discount_percent INT DEFAULT 0 AFTER discount_amount"),
            ("promo_code", "ADD COLUMN promo_code VARCHAR(50) NULL AFTER discount_percent"),
        ]
        for column, statement in columns:
            try:
                self._execute(f"ALTER TABLE payments {statement}")
            except Exception as exc:
                text = str(exc)
                if 'Duplicate column name' in text:
                    logging.debug(f'payments.{column} already exists')
                elif 'doesn\'t exist' in text or 'Unknown table' in text:
                    logging.debug(f'payments table not found when adding {column}')
                else:
                    logging.debug(f'ensure_payments_discount_columns {column}: {exc}')

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

    def ensure_plus_purchase_amount_column(self):
        try:
            self._execute(
                "ALTER TABLE plus_package_purchases "
                "ADD COLUMN amount DECIMAL(15,2) NOT NULL DEFAULT 0 AFTER package_code"
            )
        except Exception as exc:
            text = str(exc)
            if 'Duplicate column name' in text:
                logging.debug('plus_package_purchases.amount already exists')
            elif 'Unknown table' in text or "doesn't exist" in text:
                logging.debug('plus_package_purchases table not found when adding amount column')
            else:
                logging.debug(f'ensure_plus_purchase_amount_column: {exc}')

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

    def create_promo_codes_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS promo_codes (
            code VARCHAR(64) PRIMARY KEY,
            discount_percent INT NOT NULL,
            usage_limit INT NOT NULL,
            usage_count INT NOT NULL DEFAULT 0,
            plan_type VARCHAR(32) NOT NULL DEFAULT 'PLUS',
            description VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            starts_at DATETIME NULL,
            expires_at DATETIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        self._execute(query)

    def create_promo_code_redemptions_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS promo_code_redemptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(64) NOT NULL,
            user_id BIGINT NOT NULL,
            merchant_trans_id VARCHAR(255) NOT NULL,
            discount_percent INT NOT NULL,
            discount_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
            status ENUM('reserved', 'completed', 'cancelled') DEFAULT 'reserved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_code_trans (code, merchant_trans_id),
            INDEX idx_code_status (code, status),
            INDEX idx_merchant_trans_id (merchant_trans_id)
        )
        """
        self._execute(query)

    def seed_promo_codes(self):
        if not PROMO_CODES:
            return
        for code, meta in PROMO_CODES.items():
            try:
                self._execute(
                    """
                    INSERT INTO promo_codes (code, discount_percent, usage_limit, plan_type, description, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        discount_percent = VALUES(discount_percent),
                        usage_limit = VALUES(usage_limit),
                        plan_type = VALUES(plan_type),
                        description = VALUES(description),
                        is_active = VALUES(is_active),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        code.upper(),
                        int(meta.get('discount_percent', 0)),
                        int(meta.get('limit', 0)),
                        meta.get('plan_type', 'PLUS').upper(),
                        meta.get('description'),
                        bool(meta.get('is_active', True)),
                    ),
                )
            except Exception as exc:
                logging.error(f"Promo code seed error ({code}): {exc}")

    def get_promo_code(self, code):
        query = """
        SELECT code, discount_percent, usage_limit, usage_count, plan_type, is_active, starts_at, expires_at
        FROM promo_codes
        WHERE code = %s
        """
        return self._execute(query, (code.upper(),), fetchone=True)

    def increment_promo_code_usage(self, code):
        query = """
        UPDATE promo_codes
        SET usage_count = usage_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE code = %s
        """
        self._execute(query, (code.upper(),))

    def decrement_promo_code_usage(self, code):
        query = """
        UPDATE promo_codes
        SET usage_count = GREATEST(0, usage_count - 1),
            updated_at = CURRENT_TIMESTAMP
        WHERE code = %s
        """
        self._execute(query, (code.upper(),))

    def upsert_promo_redemption(self, code, user_id, merchant_trans_id, discount_percent, discount_amount):
        query = """
        INSERT INTO promo_code_redemptions (code, user_id, merchant_trans_id, discount_percent, discount_amount, status)
        VALUES (%s, %s, %s, %s, %s, 'reserved')
        ON DUPLICATE KEY UPDATE
            user_id = VALUES(user_id),
            discount_percent = VALUES(discount_percent),
            discount_amount = VALUES(discount_amount),
            status = 'reserved',
            updated_at = CURRENT_TIMESTAMP
        """
        self._execute(
            query,
            (
                code.upper(),
                user_id,
                merchant_trans_id,
                discount_percent,
                discount_amount,
            ),
        )

    def update_promo_redemption_status(self, merchant_trans_id, status):
        query = """
        UPDATE promo_code_redemptions
        SET status = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE merchant_trans_id = %s
        """
        self._execute(query, (status, merchant_trans_id))

    def get_redemption_by_merchant_trans_id(self, merchant_trans_id):
        query = """
        SELECT code, discount_percent, discount_amount, status
        FROM promo_code_redemptions
        WHERE merchant_trans_id = %s
        """
        return self._execute(query, (merchant_trans_id,), fetchone=True)

    def create_payment_record(
        self,
        user_id,
        merchant_trans_id,
        amount,
        tariff,
        payment_method='click',
        package_code=None,
        promo_code=None,
        discount_percent=0,
        discount_amount=0,
        original_amount=None,
    ):
        if package_code:
            query = (
                "INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, package_code, status, promo_code, discount_percent, discount_amount, original_amount) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)"
            )
            params = (
                user_id,
                merchant_trans_id,
                amount,
                tariff,
                payment_method,
                package_code,
                promo_code.upper() if promo_code else None,
                discount_percent,
                discount_amount,
                original_amount,
            )
        else:
            query = (
                "INSERT INTO payments (user_id, merchant_trans_id, amount, tariff, payment_method, status, promo_code, discount_percent, discount_amount, original_amount) "
                "VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)"
            )
            params = (
                user_id,
                merchant_trans_id,
                amount,
                tariff,
                payment_method,
                promo_code.upper() if promo_code else None,
                discount_percent,
                discount_amount,
                original_amount,
            )
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

    def get_payment_by_merchant_trans_id(self, merchant_trans_id):
        query = "SELECT * FROM payments WHERE merchant_trans_id = %s"
        return self._execute(query, (merchant_trans_id,), fetchone=True)

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
