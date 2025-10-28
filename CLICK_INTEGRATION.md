# 📝 Click.uz Integratsiya Hujjati

## 🎯 Maqsad
balansaibot servisini Click orqali to'lovni qabul qilish uchun to'liq integratsiya qilish.

---

## 📄 Kerakli Ma'lumotlar

```
SERVICE_ID: 85417
MERCHANT_ID: 49266
SECRET_KEY: 3DSnE96DKz7Nh
MERCHANT_USER_ID: 67944
```

---

## 🔐 Endpointlar

### 1. POST /api/click/prepare
**Maqsad:** Click to'lovni boshlashdan oldin tekshiruv

**Talablar:**
- `merchant_id` - MERCHANT_ID (49266) ga teng bo'lishi kerak
- `service_id` - SERVICE_ID (85417) ga teng bo'lishi kerak
- `sign_string` - SECRET_KEY orqali to'g'ri hosil qilingan bo'lishi kerak
- Barcha kerakli parametrlar mavjud bo'lishi kerak

**Signature Formula (MD5):**
```python
sign_string = MD5(
    click_trans_id + 
    service_id + 
    secret_key + 
    merchant_trans_id + 
    amount + 
    action + 
    sign_time
)
```

**Muvaffaqiyatli javob:**
```json
{
    "error": 0,
    "error_note": "Success",
    "click_trans_id": "12345",
    "merchant_trans_id": "123456_PLUS_1_1730034567",
    "merchant_prepare_id": 12345
}
```

**Xatolik javob:**
```json
{
    "error": -8,
    "error_note": "Missing parameter: field_name"
}
```

---

### 2. POST /api/click/complete
**Maqsad:** Click to'lovni tasdiqlaganda chaqiriladi

**Talablar:**
- `sign_string` - to'g'riligini tekshirish
- Oldingi prepare bosqichi bajarilganligini tekshirish
- `amount` mosligini tekshirish
- To'g'ri bo'lsa, to'lov holatini `confirmed` ga o'zgartirish

**Muvaffaqiyatli javob:**
```json
{
    "error": 0,
    "error_note": "Success",
    "click_trans_id": "12345",
    "merchant_trans_id": "123456_PLUS_1_1730034567",
    "merchant_confirm_id": 12345
}
```

**Xatolik javob:**
```json
{
    "error": -9,
    "error_note": "Transaction cancelled"
}
```

---

## 🔐 Security & Authentication

### Signature Verification
```python
def verify_click_signature(params, secret_key):
    """
    MD5 signature tekshiruvi
    """
    click_trans_id = str(params.get('click_trans_id', ''))
    service_id = str(params.get('service_id', ''))
    merchant_trans_id = str(params.get('merchant_trans_id', ''))
    amount = str(params.get('amount', ''))
    action = str(params.get('action', ''))
    sign_time = str(params.get('sign_time', ''))
    
    sign_string = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
    calculated_sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    return calculated_sign == params.get('sign_string', '')
```

---

## 📊 Logging

### Log Fayl: `/var/log/click.log`
**Format:** `datetime - message`

**Log Qismlari:**
1. `PREPARE_REQUEST` - Prepare so'rov ma'lumotlari
2. `PREPARE_RESPONSE` - Prepare javob ma'lumotlari
3. `COMPLETE_REQUEST` - Complete so'rov ma'lumotlari
4. `COMPLETE_RESPONSE_SUCCESS` - Muvaffaqiyatli complete
5. `COMPLETE_RESPONSE_FAILED` - Muvaffaqiyatsiz complete

**Misol:**
```
2025-10-27 12:34:56 - PREPARE_REQUEST: {'click_trans_id': '123', 'service_id': '85417', ...}
2025-10-27 12:34:56 - PREPARE_RESPONSE: {'error': 0, 'error_note': 'Success', ...}
```

---

## ⚙️ Xatolik Kodlari

| Kod | Tavsif |
|-----|--------|
| 0 | Muvaffaqiyatli |
| -1 | SIGN CHECK FAILED |
| -2 | Incorrect parameter amount |
| -3 | Action not found |
| -5 | Service ID not found |
| -6 | Merchant ID not found |
| -8 | Missing parameter |
| -9 | Transaction not found |

---

## 💾 Database Schema

### Payments Jadvali
```sql
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
```

**Status Flow:**
```
pending → prepared → confirmed
                  ↘ failed
```

---

## 🔌 Database Funksiyalari

```python
# To'lov yozuvi yaratish
db.create_payment_record(user_id, merchant_trans_id, amount, tariff, payment_method)

# Prepare holatini yangilash
db.update_payment_prepare(merchant_trans_id, click_trans_id)

# Complete holatini yangilash
db.update_payment_complete(merchant_trans_id, status, error_code, error_note)

# Tarifni faollashtirish
db.activate_tariff(user_id, tariff, months)

# To'lovlar tarixini olish
db.get_user_payments(user_id, limit)
```

---

## 🚀 Frontend Integratsiya

### 1. To'lov Yaratish
```javascript
POST /api/create-payment

Body:
{
  "user_id": 123456,
  "tariff": "PLUS",
  "amount": 15000,
  "months": 1,
  "payment_method": "click"
}

Response:
{
  "success": true,
  "merchant_trans_id": "123456_PLUS_1_1730034567"
}
```

### 2. Click.uz'ga Yo'naltirish
```javascript
const clickUrl = `https://my.click.uz/services/pay?service_id=85417&merchant_trans_id=${merchant_trans_id}&amount=${amount}`;
window.location.href = clickUrl;
```

---

## 📋 Merchant Trans ID Format

**Format:** `user_id_tariff_months_timestamp`

**Misol:**
- `123456_PLUS_1_1730034567` - User 123456, PLUS tarifi, 1 oy
- `789012_MAX_3_1730034568` - User 789012, MAX tarifi, 3 oy

**Parsing:**
```python
parts = merchant_trans_id.split('_')
user_id = int(parts[0])      # 123456
tariff = parts[1].upper()     # PLUS
months = int(parts[2])        # 1
timestamp = int(parts[3])     # 1730034567
```

---

## 🔄 To'lov Jarayoni

```
1. Frontend → POST /api/create-payment
   ↓ merchant_trans_id yaratiladi
   ↓ Database: status = 'pending'

2. Frontend → Click.uz'ga yo'naltirish
   ↓ Click.uz to'lov sahifasi

3. Click.uz → POST /api/click/prepare
   ↓ Signature tekshiruvi
   ↓ Database: status = 'prepared'

4. Foydalanuvchi → To'lovni tasdiqlaydi

5. Click.uz → POST /api/click/complete
   ↓ Signature tekshiruvi
   ↓ Database: status = 'confirmed'
   ↓ db.activate_tariff() - Tarif faollashtiriladi
```

---

## 🧪 Test

### Test Rejimi
Click.uz test rejimida to'lov yuborganda:
- JSON javoblarda `error: 0` bo'lishi kerak
- Log faylga yozilishi kerak
- Database'da saqlanishi kerak

### Test Endpointlari
```
Prepare: https://balansai.onrender.com/api/click/prepare
Complete: https://balansai.onrender.com/api/click/complete
```

---

## ✅ Kamchiliklar va Cheklovlar

1. **Login** - Faqat `application/x-www-form-urlencoded` formatda so'rovlar qabul qilinadi
2. **Signature** - MD5 hash tekshiruvi barcha so'rovlarda talab qilinadi
3. **Merchant Trans ID** - Mavjud formatdan foydalanish shart (`user_id_tariff_months_timestamp`)
4. **Logging** - Production'da `/var/log/click.log` ga yozadi, agar ruxsat yo'q bo'lsa `click_logs.txt` ga yozadi

---

## 📞 Yordam

Click.uz o'z saytida to'liq integratsiya bo'yicha yordam beradi:
- [Click.uz Integratsiya Bo'limi](https://docs.click.uz/)
- Farangez Raximovaga murojaat: "URL joylandi, testga tayyor"

---

## 🎉 Status

✅ Endpointlar yaratildi  
✅ Database integratsiyasi  
✅ Signature verification (MD5)  
✅ Logging tizimi  
✅ Tariff faollashtirish  
✅ To'lovlar tarixi API  

**Ready for Testing!** 🚀