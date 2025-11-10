from flask import Flask, render_template, jsonify, request, redirect, abort
import os
import requests
import hashlib
import logging
import threading
from datetime import datetime
from database import Database
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
except Exception as bootstrap_err:
    logging.warning(f"⚠️ Database bootstrap warning: {bootstrap_err}")


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

        if not package_code or package_code not in PLUS_PACKAGES:
            return jsonify({'error': 'Invalid package selection'}), 400

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            logging.error(f"Invalid user_id provided: {user_id_raw}")
            return jsonify({'error': 'Invalid user identifier'}), 400

        package = PLUS_PACKAGES[package_code]
        amount = package['price']

        timestamp = int(datetime.now().timestamp())
        merchant_trans_id = f"{user_id}_PLUS_{package_code}_{timestamp}"

        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, 'PLUS', 'click', package_code=package_code)
        except Exception as e:
            logging.error(f"Error creating payment record: {e}")

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


@app.route('/payment-pro', methods=['GET', 'POST'])
def payment_pro():
    if request.method == 'GET':
        return render_template('payment-pro.html')

    try:
        user_id = int(request.form.get('user_id', CLICK_MERCHANT_USER_ID))
        months_raw = request.form.get('months')

        if months_raw not in ['1', '12']:
            return jsonify({'error': 'Invalid months selection'}), 400

        months = int(months_raw)
        prices = {1: 49990, 12: int(49990 * 12 * 0.9)}
        amount = prices.get(months, 49990)

        timestamp = int(datetime.now().timestamp())
        merchant_trans_id = f"{user_id}_PRO_{months}_{timestamp}"

        try:
            db.create_payment_record(user_id, merchant_trans_id, amount, 'PRO', 'click')
        except Exception as e:
            logging.error(f"Error creating payment record (MAX): {e}")

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
            response = {
                'click_trans_id': int(click_trans_id),
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': int(datetime.now().timestamp()),
                'error': error_code,
                'error_note': 'Transaction cancelled',
            }
            click_logger.info(f"COMPLETE_RESPONSE_FAILED: {response}")
            return jsonify(response)

        response = {
            'click_trans_id': int(click_trans_id),
            'merchant_trans_id': merchant_trans_id,
            'merchant_confirm_id': int(datetime.now().timestamp()),
            'error': 0,
            'error_note': 'Success',
        }
        click_logger.info(f"COMPLETE_RESPONSE: {response}")

        def background_update():
            try:
                local_merchant_trans_id = merchant_trans_id
                local_click_trans_id = click_trans_id
                local_amount = float(amount) if amount else 0

                if not local_merchant_trans_id:
                    payment = db.get_payment_by_click_trans_id(local_click_trans_id)
                    if payment:
                        local_merchant_trans_id = payment.get('merchant_trans_id')
                        if local_amount == 0 and payment.get('amount'):
                            local_amount = float(payment['amount'])

                if not local_merchant_trans_id:
                    return

                parts = local_merchant_trans_id.split('_')
                if len(parts) < 2:
                    return

                user_id = int(parts[0])
                tariff_token = parts[1].upper()
                months = 1
                package_code = None
                package_info = None

                if tariff_token == 'PLUS' and len(parts) >= 3:
                    third = parts[2]
                    if third.isdigit():
                        months = int(third)
                    else:
                        package_code = third.upper()
                elif len(parts) >= 3 and parts[2].isdigit():
                    months = int(parts[2])

                normalized_tariff = 'PLUS' if tariff_token == 'PLUS' else tariff_token

                db.update_payment_complete(local_merchant_trans_id, status='confirmed', error_code=0, error_note='Success')
                db.activate_tariff(user_id, normalized_tariff, months)

                if package_code and package_code in PLUS_PACKAGES:
                    package = PLUS_PACKAGES[package_code]
                    db.assign_user_package(user_id, package_code, package['text_limit'], package['voice_limit'])

                if BOT_TOKEN:
                    display_tariff = 'Max' if normalized_tariff == 'PRO' else normalized_tariff
                    message = (
                        f"✅ To'lov {int(local_amount):,} so'm muvaffaqiyatli amalga oshirildi!\n\n"
                        f"Tarifingiz faollashtirildi: {display_tariff}"
                    )
                    if package_info:
                        message += (
                            f"\nPaket: {package_info.get('title', package_code)} "
                            f"({package_info.get('text_limit', 0)} ta matn / {package_info.get('voice_limit', 0)} ta ovoz)"
                        )
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={'chat_id': user_id, 'text': message},
                        timeout=5,
                    )
            except Exception as err:
                logging.error(f"Background update error: {err}")

        threading.Thread(target=background_update, daemon=True).start()
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

        display_tariff = 'Max' if normalized_tariff == 'PRO' else normalized_tariff
        return jsonify({'success': True, 'message': f'Tariff activated: {display_tariff}', 'merchant_trans_id': merchant_trans_id})
    except Exception as e:
        logging.error(f"Manual complete error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    print(f"🚀 Payment service running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)