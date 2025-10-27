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

## 🔄 Keyingi Qadamlar

1. ✅ Endpointlar yaratildi va test qilindi
2. ⏳ Database'ga to'lov ma'lumotlarini saqlash
3. ⏳ Frontend'da to'lov tugmasini faollashtirish
4. ⏳ Foydalanuvchi tarifini avtomatik yangilash
5. ⏳ To'lov tarixini ko'rsatish

---

## 📞 Yordam

Savollar bo'lsa:
- Click.uz: https://docs.click.uz/
- Telegram: @support_balansai

