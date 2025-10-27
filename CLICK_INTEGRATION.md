# Click.uz To'lov Integratsiyasi

## 📋 Umumiy Ma'lumot

Balans AI mini ilovasiga Click.uz to'lov tizimi integratsiya qilindi.

### Endpointlar:
- **Prepare URL**: `https://balansai.onrender.com/click/prepare`
- **Complete URL**: `https://balansai.onrender.com/click/complete`

---

## 🔐 Sozlash

### 1. Environment Variables

`.env` faylga quyidagilarni qo'shing:

```env
CLICK_SECRET_KEY=your_click_secret_key_here
CLICK_SERVICE_ID=your_service_id_here
CLICK_MERCHANT_ID=your_merchant_id_here
```

### 2. Click.uz Kabinetida Sozlash

1. Click.uz kabinetingizga kiring
2. Service yarating yoki mavjud serviceni sozlang
3. Quyidagi URLlarni kiriting:
   - **Prepare URL**: `https://balansai.onrender.com/click/prepare`
   - **Complete URL**: `https://balansai.onrender.com/click/complete`
4. Secret Key va Service ID ni oling va `.env` ga kiriting

---

## 📡 API Hujjatlari

### 1. `/click/prepare` - Prepare Endpoint

**Metod**: `POST`  
**Content-Type**: `application/x-www-form-urlencoded`

**So'rov parametrlari**:
```
click_trans_id: Click tranzaksiya ID
service_id: Xizmat ID
merchant_trans_id: Merchant tranzaksiya ID (format: "user_id_tariff_timestamp")
amount: Summa (so'm)
action: Harakat (0 yoki 1)
sign_time: Vaqt timestamp
sign_string: SHA1 imzo
```

**Muvaffaqiyatli javob** (200):
```json
{
  "click_trans_id": 123456,
  "merchant_trans_id": "789_PLUS_1234567890",
  "merchant_prepare_id": 1234567890,
  "error": 0,
  "error_note": "Success"
}
```

**Xato javoblari**:
- `-1`: Sign check failed (imzo xato)
- `-2`: Incorrect amount (summa xato)
- `-3`: Action not found (harakat topilmadi)
- `-5`: Service ID not found (xizmat topilmadi)
- `-8`: Missing parameter (parametr yo'q)
- `-9`: Transaction not found (tranzaksiya topilmadi)

---

### 2. `/click/complete` - Complete Endpoint

**Metod**: `POST`  
**Content-Type**: `application/x-www-form-urlencoded`

**So'rov parametrlari**:
```
click_trans_id: Click tranzaksiya ID
merchant_trans_id: Merchant tranzaksiya ID
amount: Summa
action: Harakat
sign_time: Vaqt
sign_string: SHA1 imzo
error: Click xato kodi (0 = muvaffaqiyatli)
```

**Muvaffaqiyatli javob** (200):
```json
{
  "click_trans_id": 123456,
  "merchant_trans_id": "789_PLUS_1234567890",
  "merchant_confirm_id": 1234567890,
  "error": 0,
  "error_note": "Success"
}
```

---

## 🔒 Xavfsizlik

### SHA1 Imzo Algoritmi

Imzo yaratish formulasi:
```
SHA1(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
```

**Python misol**:
```python
import hashlib

def create_signature(click_trans_id, service_id, secret_key, merchant_trans_id, amount, action, sign_time):
    sign_string = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
    return hashlib.sha1(sign_string.encode('utf-8')).hexdigest()
```

---

## 📝 Loglar

Barcha to'lov so'rovlari `click_logs.txt` faylga yoziladi:

```
2025-10-27 12:34:56 - INFO - Click Prepare request: {...}
2025-10-27 12:34:57 - INFO - Prepare success: merchant_trans_id=789_PLUS_1234567890
2025-10-27 12:35:00 - INFO - Payment confirmed: merchant_trans_id=789_PLUS_1234567890
```

---

## 🧪 Test Qilish

### Test So'rov (cURL):

```bash
curl -X POST https://balansai.onrender.com/click/prepare \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "click_trans_id=123456" \
  -d "service_id=YOUR_SERVICE_ID" \
  -d "merchant_trans_id=789_PLUS_1234567890" \
  -d "amount=15000" \
  -d "action=0" \
  -d "sign_time=1234567890" \
  -d "sign_string=CALCULATED_SHA1_HASH"
```

### Merchant Trans ID Formati:

```
{user_id}_{tariff}_{timestamp}

Misol:
- 123456_PLUS_1730034567
- 789012_PRO_1730034568
```

---

## 💾 Database Integratsiyasi

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

### Database Funksiyalari

```python
# To'lov yozuvi yaratish
db.create_payment_record(user_id, merchant_trans_id, amount, tariff, payment_method)

# Prepare holatini yangilash
db.update_payment_prepare(merchant_trans_id, click_trans_id)

# Complete holatini yangilash
db.update_payment_complete(merchant_trans_id, status='confirmed', error_code=0, error_note='Success')

# Tarifni faollashtirish
db.activate_tariff(user_id, tariff, months)

# To'lovlar tarixini olish
db.get_user_payments(user_id, limit=10)
```

---

## 🔌 Frontend API Endpointlari

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
  "merchant_trans_id": "123456_PLUS_1_1730034567",
  "message": "To'lov yozuvi yaratildi"
}
```

### 2. To'lovlar Tarixi

```javascript
GET /api/payment-history/{user_id}?limit=10

Response:
{
  "success": true,
  "payments": [
    {
      "id": 1,
      "user_id": 123456,
      "click_trans_id": "123456789",
      "merchant_trans_id": "123456_PLUS_1_1730034567",
      "amount": 15000,
      "tariff": "PLUS",
      "status": "confirmed",
      "created_at": "2025-10-27 12:34:56"
    }
  ]
}
```

---

## 🔄 To'lov Jarayoni

### 1. Frontend → Backend

```javascript
// 1. To'lov yozuvini yaratish
const response = await fetch('/api/create-payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: userId,
        tariff: 'PLUS',
        amount: 15000,
        months: 1,
        payment_method: 'click'
    })
});

const { merchant_trans_id } = await response.json();

// 2. Click.uz'ga yo'naltirish
window.location.href = `https://my.click.uz/services/pay?service_id=${SERVICE_ID}&merchant_trans_id=${merchant_trans_id}&amount=${amount}`;
```

### 2. Click.uz → Backend

```
1. Click.uz /click/prepare ga POST yuboradi
   → Database: status = 'prepared'

2. Foydalanuvchi to'lovni tasdiqlaydi

3. Click.uz /click/complete ga POST yuboradi
   → Database: status = 'confirmed'
   → User tariff yangilanadi
```

---

## 🔄 Keyingi Qadamlar

1. ✅ Endpointlar yaratildi va test qilindi
2. ✅ Database'ga to'lov ma'lumotlarini saqlash
3. ✅ Foydalanuvchi tarifini avtomatik yangilash
4. ✅ To'lov tarixini ko'rsatish
5. ⏳ Frontend'da to'lov tugmasini faollashtirish
6. ⏳ Click.uz test rejimida test qilish

---

## 📞 Yordam

Savollar bo'lsa:
- Click.uz: https://docs.click.uz/
- Telegram: @support_balansai

