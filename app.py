from flask import Flask, render_template, jsonify, request, redirect, abort
import os
import requests
import hashlib
import logging
import threading
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from database import Database
from typing import Tuple
from config import (
    CLICK_SECRET_KEY,
    CLICK_SERVICE_ID,
    CLICK_MERCHANT_ID,
    CLICK_MERCHANT_USER_ID,
    BOT_TOKEN,
    PLUS_PACKAGES,
    PLUS_PACKAGE_SEQUENCE,
    TARIFF_LIMITS,
)

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

db = Database()

try:
    db.create_payments_table()
    db.create_user_package_limits_table()
    db.ensure_payments_package_column()
    db.create_plus_package_purchases_table()
    db.ensure_plus_purchase_columns()
    db.ensure_user_package_limit_defaults()
    db.ensure_payments_discount_columns()
    db.create_promo_codes_table()
    db.create_promo_code_redemptions_table()
    db.seed_promo_codes()
except Exception as bootstrap_err:
    logging.warning(f"⚠️ Database bootstrap warning: {bootstrap_err}")


def _normalize_plan(plan_token: str) -> str:
    if not plan_token:
        return ''
    token = plan_token.strip().upper()
    if token in {'PLUS', 'PRO', 'MAX'}:
        return token
    if token == 'ALL':
        return 'ALL'
    return token


def _calculate_discount(amount: Decimal, percent: int) -> Tuple[Decimal, Decimal]:
    percent_value = max(0, min(100, int(percent or 0)))
    discount_amount = (amount * Decimal(percent_value) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    final_amount = amount - discount_amount
    if final_amount < 0:
        final_amount = Decimal('0')
    return discount_amount, final_amount


def _validate_promocode(code: str, plan_type: str, amount: Decimal):
    if not code:
        raise ValueError("Promokod kiritilmadi")
    promo = db.get_promo_code(code)
    if not promo:
        raise ValueError("Bunday promokod topilmadi")
    if not promo.get('is_active'):
        raise ValueError("Promokod faol emas")
    now = datetime.now()
    starts_at = promo.get('starts_at')
    expires_at = promo.get('expires_at')
    if starts_at and now < starts_at:
        raise ValueError("Promokod hali faol emas")
    if expires_at and now > expires_at:
        raise ValueError("Promokod muddati tugagan")
    plan = _normalize_plan(plan_type)
    promo_plan = _normalize_plan(promo.get('plan_type'))
    if promo_plan and promo_plan not in {'', 'ALL'}:
        if plan not in {promo_plan, 'ALL'}:
            raise ValueError("Bu promokod tanlangan tarif uchun amal qilmaydi")
    usage_limit = promo.get('usage_limit', 0) or 0
    usage_count = promo.get('usage_count', 0) or 0
    if usage_limit > 0 and usage_count >= usage_limit:
        raise ValueError("Promokod qo'llanish limiti tugagan")
    discount_percent = int(promo.get('discount_percent') or 0)
    if discount_percent <= 0:
        raise ValueError("Promokodda chegirma ko'rsatilmagan")
    discount_amount, final_amount = _calculate_discount(amount, discount_percent)
    if final_amount <= 0:
        raise ValueError("Promokod noto'g'ri sozlangan")
    return {
        'code': promo.get('code', code).upper(),
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        'final_amount': final_amount,
    }


@app.route('/')
def root():
    return redirect('/payment-plus')


@app.route('/payment-plus', methods=['GET', 'POST'])
def payment_plus():
    if request.method == 'GET':
        packages = []
        for code in PLUS_PACKAGE_SEQUENCE:
            package = PLUS_PACKAGES.get(code)
            if not package:
                continue
            packages.append({
                'code': package['code'],
                'title': package['title'],
                'tagline': package['tagline'],
                'text_limit': package['text_limit'],
                'voice_limit': package['voice_limit'],
                'price': package['price'],
                'badge': package.get('badge')
            })
        return render_template('payment-plus.html', plus_packages=packages)

    try:
        user_id_raw = request.form.get('user_id', CLICK_MERCHANT_USER_ID)
        package_code = (request.form.get('package_code') or '').upper()
        payment_method = (request.form.get('payment_method') or 'click').strip().lower()

        if not package_code or package_code not in PLUS_PACKAGES:
            return jsonify({'error': 'Invalid package selection'}), 400
        if payment_method != 'click':
            return jsonify({'error': "Hozircha faqat Click orqali to'lash mumkin"}), 400

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            logging.error(f"Invalid user_id provided: {user_id_raw}")
            return jsonify({'error': 'Invalid user identifier'}), 400

        package = PLUS_PACKAGES[package_code]
        original_amount = Decimal(str(package['price']))
        discount_amount = Decimal('0')
        discount_percent = 0
        final_amount = original_amount
        promo_code_raw = (request.form.get('promo_code') or '').strip()
        promo_code = promo_code_raw.upper() if promo_code_raw else ''

        if promo_code:
            try:
                promo_eval = _validate_promocode(promo_code, 'PLUS', original_amount)
                discount_amount = promo_eval['discount_amount']
                final_amount = promo_eval['final_amount']
                discount_percent = promo_eval['discount_percent']
                promo_code = promo_eval['code']
            except ValueError as promo_err:
                logging.info(f"Promo validation failed (%s): %s", promo_code, promo_err)
                return jsonify({'error': str(promo_err)}), 400

        amount = int(final_amount)
        if amount <= 0:
            return jsonify({'error': 'Chegirmadan so\'ng to\'lov summasi noto\'g\'ri'}), 400
        original_amount_int = int(original_amount)
        discount_amount_int = int(discount_amount)

        timestamp = int(datetime.now().timestamp())
        merchant_trans_id = f"{user_id}_PLUS_{package_code}_{timestamp}"

        try:
            db.create_payment_record(
                user_id,
                merchant_trans_id,
                amount,
                'PLUS',
                payment_method,
                package_code=package_code,
                promo_code=promo_code if promo_code else None,
                discount_percent=discount_percent,
                discount_amount=discount_amount_int,
                original_amount=original_amount_int,
            )
        except Exception as e:
            logging.error(f"Error creating payment record: {e}")
        else:
            if promo_code:
                try:
                    db.upsert_promo_redemption(
                        promo_code,
                        user_id,
                        merchant_trans_id,
                        discount_percent,
                        discount_amount_int,
                    )
                except Exception as promo_err:
                    logging.error(f"Promo redemption reserve error: {promo_err}")

        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"
            f"&customer={urllib.parse.quote(str(user_id))}"
            f"&return_url={urllib.parse.quote('https://t.me/balansaibot')}"
        )

        logging.info(
            "PAYMENT_PLUS: user_id=%s, package=%s, amount=%s, merchant_trans_id=%s",
            user_id,
            package_code,
            amount,
            merchant_trans_id,
        )
        return redirect(click_url)
    except Exception as e:
        logging.error(f"Payment error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/promocode/validate', methods=['POST'])
def validate_promocode_api():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}
    if not payload:
        payload = request.form.to_dict()

    code_raw = (payload.get('code') or payload.get('promo_code') or '').strip()
    plan_type = (payload.get('plan_type') or payload.get('plan') or 'PLUS').strip()
    amount_raw = payload.get('amount')

    if not code_raw:
        return jsonify({'success': False, 'message': "Promokod kiritilmadi"}), 400
    if amount_raw is None:
        return jsonify({'success': False, 'message': "Summani yuboring"}), 400

    try:
        amount_decimal = Decimal(str(amount_raw))
    except Exception:
        return jsonify({'success': False, 'message': "Summani aniqlab bo'lmadi"}), 400

    if amount_decimal <= 0:
        return jsonify({'success': False, 'message': "Summani to'g'ri yuboring"}), 400

    try:
        promo_eval = _validate_promocode(code_raw, plan_type, amount_decimal)
        return jsonify({
            'success': True,
            'data': {
                'code': promo_eval['code'],
                'discount_percent': promo_eval['discount_percent'],
                'discount_amount': int(promo_eval['discount_amount']),
                'final_amount': int(promo_eval['final_amount']),
            }
        })
    except ValueError as err:
        return jsonify({'success': False, 'message': str(err)}), 400
    except Exception as err:
        logging.error(f"Promocode validation error: {err}")
        return jsonify({'success': False, 'message': "Promokodni tekshirishda xatolik yuz berdi"}), 500


@app.route('/payment-pro', methods=['GET', 'POST'])
def payment_pro():
    if request.method == 'GET':
        return render_template('payment-pro.html')

    try:
        user_id = int(request.form.get('user_id', CLICK_MERCHANT_USER_ID))
        months_raw = request.form.get('months')
        payment_method = (request.form.get('payment_method') or 'click').strip().lower()

        if months_raw not in ['1', '12']:
            return jsonify({'error': 'Invalid months selection'}), 400
        if payment_method != 'click':
            return jsonify({'error': "Hozircha faqat Click orqali to'lash mumkin"}), 400

        months = int(months_raw)
        prices = {1: 49990, 12: int(49990 * 12 * 0.9)}
        original_amount = Decimal(str(prices.get(months, 49990)))
        discount_amount = Decimal('0')
        discount_percent = 0
        final_amount = original_amount

        promo_code_raw = (request.form.get('promo_code') or '').strip()
        promo_code = promo_code_raw.upper() if promo_code_raw else ''
        if promo_code:
            try:
                promo_eval = _validate_promocode(promo_code, 'PRO', original_amount)
                discount_amount = promo_eval['discount_amount']
                final_amount = promo_eval['final_amount']
                discount_percent = promo_eval['discount_percent']
                promo_code = promo_eval['code']
            except ValueError as promo_err:
                logging.info(f"Promo validation failed (%s): %s", promo_code, promo_err)
                return jsonify({'error': str(promo_err)}), 400

        amount = int(final_amount)
        if amount <= 0:
            return jsonify({'error': 'Chegirmadan so\'ng to\'lov summasi noto\'g\'ri'}), 400
        original_amount_int = int(original_amount)
        discount_amount_int = int(discount_amount)

        timestamp = int(datetime.now().timestamp())
        merchant_trans_id = f"{user_id}_PRO_{months}_{timestamp}"

        try:
            db.create_payment_record(
                user_id,
                merchant_trans_id,
                amount,
                'PRO',
                payment_method,
                promo_code=promo_code if promo_code else None,
                discount_percent=discount_percent,
                discount_amount=discount_amount_int,
                original_amount=original_amount_int,
            )
        except Exception as e:
            logging.error(f"Error creating payment record (MAX): {e}")
        else:
            if promo_code:
                try:
                    db.upsert_promo_redemption(
                        promo_code,
                        user_id,
                        merchant_trans_id,
                        discount_percent,
                        discount_amount_int,
                    )
                except Exception as promo_err:
                    logging.error(f"Promo redemption reserve error: {promo_err}")

        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"
            f"&customer={urllib.parse.quote(str(user_id))}"
            f"&return_url={urllib.parse.quote('https://t.me/balansaibot')}"
        )

        logging.info(
            "PAYMENT_MAX: user_id=%s, months=%s, amount=%s, merchant_trans_id=%s",
            user_id,
            months,
            amount,
            merchant_trans_id,
        )
        return redirect(click_url)
    except Exception as e:
        logging.error(f"Payment MAX error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/payment-success')
def payment_success():
    payment_id = request.args.get('paymentId', '')
    payment_status = request.args.get('paymentStatus', '')
    html = (
        "<!DOCTYPE html><html lang='uz'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        "<title>To'lov muvaffaqiyatli</title>"
        "<style>body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI',sans-serif;"
        "background:#F8F9FA;display:flex;align-items:center;justify-content:center;"
        "height:100vh;margin:0;color:#0F172A;} .card{background:#fff;padding:32px;border-radius:24px;"
        "box-shadow:0 18px 38px rgba(15,23,42,0.12);text-align:center;max-width:320px;width:100%;}"
        ".title{font-size:24px;font-weight:700;margin-bottom:8px;} .meta{font-size:14px;color:#6B7280;"
        "margin-top:12px;}</style></head><body>"
        "<div class='card'><div class='title'>To'lov muvaffaqiyatli</div>"
        "<div>Sizning obunangiz faollashtirildi.</div>"
        f"<div class='meta'>ID: {payment_id}</div>"
        f"<div class='meta'>Holat: {payment_status}</div>"
        "</div></body></html>"
    )
    return html


@app.route('/test-payment', methods=['GET', 'POST'])
def test_payment():
    test_key = os.getenv('TEST_PAYMENT_KEY', '')
    if test_key:
        provided = request.args.get('key') or request.headers.get('X-Test-Key')
        if provided != test_key:
            return abort(404)

    if request.method == 'GET':
        return jsonify({'message': 'Test payment form mavjud emas', 'success': True})

    try:
        user_id = int(request.form.get('user_id', CLICK_MERCHANT_USER_ID))
        package_code = (request.form.get('package_code') or '').upper()

        if package_code not in PLUS_PACKAGES:
            return jsonify({'error': 'Invalid package selection'}), 400

        package = PLUS_PACKAGES[package_code]
        amount = package['price']
        merchant_trans_id = f"{user_id}_PLUS_{package_code}_{int(datetime.now().timestamp())}"

        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, 'PLUS', 'click', package_code=package_code)
        except Exception as e:
            logging.error(f"Error creating payment record: {e}")

        import urllib.parse
        click_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={CLICK_SERVICE_ID}"
            f"&merchant_id={CLICK_MERCHANT_ID}"
            f"&transaction_param={urllib.parse.quote(merchant_trans_id)}"
            f"&amount={amount}"
            f"&return_url={urllib.parse.quote('https://t.me/balansaibot')}"
        )

        logging.info(
            "TEST_PAYMENT: user_id=%s, package=%s, amount=%s, merchant_trans_id=%s",
            user_id,
            package_code,
            amount,
            merchant_trans_id,
        )
        return redirect(click_url)
    except Exception as e:
        logging.error(f"Test payment error: {e}")
        return jsonify({'error': str(e)}), 500


click_logger = logging.getLogger('click')
click_logger.setLevel(logging.INFO)
if not click_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    click_logger.addHandler(handler)


@app.route('/api/click/prepare', methods=['POST'])
def click_prepare():
    try:
        params = request.form.to_dict()
        click_logger.info(f"PREPARE_REQUEST: {params}")

        required_fields = ['click_trans_id', 'service_id', 'amount', 'action', 'sign_time', 'sign_string']
        for field in required_fields:
            if field not in params:
                return jsonify({'error': -8, 'error_note': f'Missing parameter: {field}'}), 400

        click_trans_id = params['click_trans_id']
        service_id = params['service_id']
        amount = params['amount']
        action = params['action']
        sign_time = params['sign_time']
        received_sign = params['sign_string']
        merchant_trans_id = params.get('merchant_trans_id') or params.get('transaction_param')

        if not merchant_trans_id:
            return jsonify({'error': -5, 'error_note': 'Merchant transaction not found'}), 400

        sign_string = f"{click_trans_id}{service_id}{CLICK_SECRET_KEY}{merchant_trans_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        if calculated_sign != received_sign:
            return jsonify({'error': -1, 'error_note': 'SIGN CHECK FAILED'}), 400

        try:
            if float(amount) <= 0:
                return jsonify({'error': -2, 'error_note': 'Incorrect parameter amount'}), 400
        except ValueError:
            return jsonify({'error': -2, 'error_note': 'Incorrect parameter amount'}), 400

        if action not in ['0', '1']:
            return jsonify({'error': -3, 'error_note': 'Action not found'}), 400

        try:
            db.update_payment_prepare(merchant_trans_id, click_trans_id)
        except Exception:
            pass

        response = {
            'error': 0,
            'error_note': 'Success',
            'click_trans_id': int(click_trans_id),
            'merchant_trans_id': merchant_trans_id,
            'merchant_prepare_id': int(datetime.now().timestamp()),
        }
        click_logger.info(f"PREPARE_RESPONSE: {response}")
        return jsonify(response)
    except Exception as e:
        logging.error(f"Click Prepare error: {e}")
        return jsonify({'error': -9, 'error_note': 'Transaction not found'}), 500


@app.route('/api/click/complete', methods=['GET', 'POST'])
def click_complete():
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'message': 'Complete endpoint ready'})

    try:
        params = request.form.to_dict()
        click_logger.info(f"COMPLETE_REQUEST: {params}")

        required_fields = ['click_trans_id', 'amount', 'action', 'sign_time', 'sign_string', 'error']
        for field in required_fields:
            if field not in params:
                return jsonify({'error': -8, 'error_note': f'Missing parameter: {field}'}), 400

        click_trans_id = params['click_trans_id']
        merchant_trans_id = params.get('merchant_trans_id') or params.get('transaction_param')
        amount = params['amount']
        action = params['action']
        sign_time = params['sign_time']
        received_sign = params['sign_string']
        service_id = params.get('service_id', CLICK_SERVICE_ID)
        merchant_prepare_id = params.get('merchant_prepare_id', '')

        sign_string = f"{click_trans_id}{service_id}{CLICK_SECRET_KEY}{merchant_trans_id}{merchant_prepare_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()

        if calculated_sign != received_sign:
            allow_debug = os.getenv('CLICK_ALLOW_DEBUG_SIGNATURE', 'false').lower() == 'true'
            if not allow_debug:
                return jsonify({'error': -1, 'error_note': 'SIGN CHECK FAILED'}), 400

        error_code = int(params.get('error', -1))

        if error_code != 0:
            db.update_payment_complete(merchant_trans_id, status='failed', error_code=error_code, error_note='Transaction cancelled')
            try:
                db.update_promo_redemption_status(merchant_trans_id, 'cancelled')
            except Exception as promo_err:
                logging.error(f"Promo redemption cancel error: {promo_err}")
            response = {
                'click_trans_id': int(click_trans_id),
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': int(datetime.now().timestamp()),
                'error': error_code,
                'error_note': 'Transaction cancelled',
            }
            click_logger.info(f"COMPLETE_RESPONSE_FAILED: {response}")
            return jsonify(response)

        # Synchronous confirmation to avoid Click side "pending"
        user_payload = None
        try:
            payment_rec = db.get_payment_by_merchant_trans_id(merchant_trans_id)
            user_id = None
            normalized_tariff = None
            package_code = None
            amount_value = float(amount) if amount else 0
            months = 1
            promo_code_value = None

            if payment_rec:
                user_id = int(payment_rec.get('user_id'))
                normalized_tariff = (payment_rec.get('tariff') or 'PLUS').upper()
                package_code = payment_rec.get('package_code')
                amount_value = float(payment_rec.get('amount') or 0)
                promo_code_value = (payment_rec.get('promo_code') or '').strip() or None
            else:
                parts = merchant_trans_id.split('_') if merchant_trans_id else []
                if len(parts) >= 2:
                    user_id = int(parts[0])
                    tariff_token = parts[1].upper()
                    normalized_tariff = 'PLUS' if tariff_token == 'PLUS' else tariff_token
                    if tariff_token == 'PLUS' and len(parts) >= 3:
                        third = parts[2]
                        if third.isdigit():
                            months = int(third)
                        else:
                            package_code = third.upper()
                    elif len(parts) >= 3 and parts[2].isdigit():
                        months = int(parts[2])

            if normalized_tariff and user_id:
                db.update_payment_complete(merchant_trans_id, status='confirmed', error_code=0, error_note='Success')
                db.activate_tariff(user_id, normalized_tariff, months)
                package_info = None
                if promo_code_value:
                    try:
                        db.update_promo_redemption_status(merchant_trans_id, 'completed')
                        db.increment_promo_code_usage(promo_code_value)
                    except Exception as promo_err:
                        logging.error(f"Promo redemption complete error: {promo_err}")
                if package_code:
                    package_info = PLUS_PACKAGES.get(package_code)
                    text_limit_val = int(package_info['text_limit']) if package_info and package_info.get('text_limit') is not None else 0
                    voice_limit_val = int(package_info['voice_limit']) if package_info and package_info.get('voice_limit') is not None else 0
                    if package_info:
                        db.assign_user_package(user_id, package_code, package_info['text_limit'], package_info['voice_limit'])
                    db.log_package_purchase(
                        user_id,
                        package_code,
                        amount_value,
                        merchant_trans_id,
                        text_limit=text_limit_val,
                        voice_limit=voice_limit_val,
                        status='completed',
                    )
                user_payload = {
                    'user_id': user_id,
                    'tariff': normalized_tariff,
                    'amount': amount_value,
                    'package': package_info,
                    'package_code': package_code,
                }
        except Exception as sync_err:
            logging.error(f"Immediate confirmation error: {sync_err}")

        response = {
            'click_trans_id': int(click_trans_id),
            'merchant_trans_id': merchant_trans_id,
            'merchant_confirm_id': int(datetime.now().timestamp()),
            'error': 0,
            'error_note': 'Success',
        }
        click_logger.info(f"COMPLETE_RESPONSE: {response}")

        def notify_telegram(payload):
            if not payload or not BOT_TOKEN:
                return
            try:
                display_tariff = 'Max' if payload['tariff'] == 'PRO' else payload['tariff']
                message = (
                    f"✅ To'lov {int(payload['amount']):,} so'm muvaffaqiyatli amalga oshirildi!\n\n"
                    f"Tarifingiz faollashtirildi: {display_tariff}"
                )
                package_info = payload.get('package')
                if package_info:
                    message += (
                        f"\nPaket: {package_info.get('title', payload.get('package_code'))} "
                        f"({package_info.get('text_limit', 0)} ta matn / {package_info.get('voice_limit', 0)} ta ovoz)"
                    )
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={'chat_id': payload['user_id'], 'text': message},
                    timeout=5,
                )
            except Exception as err:
                logging.error(f"Telegram notification error: {err}")

        if user_payload:
            threading.Thread(target=notify_telegram, args=(user_payload,), daemon=True).start()

        return jsonify(response)
    except Exception as e:
        logging.error(f"Click Complete error: {e}")
        return jsonify({'error': -9, 'error_note': 'Transaction not found'}), 500


@app.route('/api/user/tariff/<int:user_id>')
def get_user_tariff(user_id):
    try:
        tariff_info = db.get_user_tariff(user_id)
        tariff_code = tariff_info.get('tariff', 'Bepul')
        expires_at = tariff_info.get('expires_at')
        limits = TARIFF_LIMITS.get(tariff_code, TARIFF_LIMITS['Plus'])
        package_info = db.get_user_package_limits(user_id)
        payload = None
        if package_info:
            package_code = (package_info.get('package_code') or '').upper()
            package_meta = PLUS_PACKAGES.get(package_code)
            payload = {
                'code': package_code,
                'text_limit': package_info.get('text_limit'),
                'voice_limit': package_info.get('voice_limit'),
                'text_used': package_info.get('text_used'),
                'voice_used': package_info.get('voice_used'),
                'title': package_meta.get('title') if package_meta else None,
                'tagline': package_meta.get('tagline') if package_meta else None,
                'price': package_meta.get('price') if package_meta else None,
                'badge': package_meta.get('badge') if package_meta else None,
                'updated_at': package_info.get('updated_at').isoformat() if package_info.get('updated_at') else None,
            }
        last_payment = db.get_last_payment(user_id, tariff_code)
        last_payment_payload = None
        if last_payment:
            paid_at = last_payment.get('complete_time') or last_payment.get('created_at')
            last_payment_payload = {
                'amount': float(last_payment.get('amount') or 0),
                'paid_at': paid_at.isoformat() if paid_at else None,
            }
        return jsonify({
            'success': True,
            'data': {
                'tariff': tariff_code,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'limits': limits,
                'package': payload,
                'last_payment': last_payment_payload,
            },
        })
    except Exception as e:
        logging.error(f"Get user tariff error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/manual-complete', methods=['POST'])
def manual_complete_payment():
    merchant_trans_id = request.json.get('merchant_trans_id')
    if not merchant_trans_id:
        return jsonify({'success': False, 'message': 'merchant_trans_id required'}), 400

    try:
        parts = merchant_trans_id.split('_')
        if len(parts) < 2:
            return jsonify({'success': False, 'message': 'Invalid merchant_trans_id format'}), 400

        user_id = int(parts[0])
        tariff_token = parts[1].upper()
        months = 1
        package_code = None
        promo_code_value = None
        payment_rec = None

        try:
            payment_rec = db.get_payment_by_merchant_trans_id(merchant_trans_id)
            if payment_rec:
                promo_code_value = (payment_rec.get('promo_code') or '').strip() or None
        except Exception as err:
            logging.error(f"Manual complete fetch error: {err}")

        if tariff_token == 'PLUS' and len(parts) >= 3:
            third = parts[2]
            if third.isdigit():
                months = int(third)
            else:
                package_code = third.upper()
        elif len(parts) >= 3 and parts[2].isdigit():
            months = int(parts[2])

        normalized_tariff = 'PLUS' if tariff_token == 'PLUS' else tariff_token

        db.update_payment_complete(merchant_trans_id, status='confirmed', error_code=0, error_note='Manually completed')
        db.activate_tariff(user_id, normalized_tariff, months)

        if package_code and package_code in PLUS_PACKAGES:
            package = PLUS_PACKAGES[package_code]
            db.assign_user_package(user_id, package_code, package['text_limit'], package['voice_limit'])
            amount_value = float(payment_rec.get('amount')) if payment_rec and payment_rec.get('amount') else 0
            text_limit_val = int(package.get('text_limit')) if package.get('text_limit') is not None else 0
            voice_limit_val = int(package.get('voice_limit')) if package.get('voice_limit') is not None else 0
            db.log_package_purchase(
                user_id,
                package_code,
                amount_value,
                merchant_trans_id,
                text_limit=text_limit_val,
                voice_limit=voice_limit_val,
                status='completed',
            )

        if promo_code_value:
            try:
                db.update_promo_redemption_status(merchant_trans_id, 'completed')
                db.increment_promo_code_usage(promo_code_value)
            except Exception as promo_err:
                logging.error(f"Promo redemption manual complete error: {promo_err}")

        display_tariff = 'Max' if normalized_tariff == 'PRO' else normalized_tariff
        return jsonify({'success': True, 'message': f'Tariff activated: {display_tariff}', 'merchant_trans_id': merchant_trans_id})
    except Exception as e:
        logging.error(f"Manual complete error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    print(f"🚀 Payment service running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)