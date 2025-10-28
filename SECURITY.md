# 🔐 Xavfsizlik Ko'rsatmalari

## ⚠️ MUHIM: Sensitive Ma'lumotlarni Yashirish

Bu loyihada barcha sensitive (yashirin) ma'lumotlar `.env` fayl orqali boshqariladi.

---

## 📝 .env Fayl Yaratish

### 1. Development uchun
```bash
cp env.example .env
```

### 2. .env faylni oching va ma'lumotlarni kiriting

```env
# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sizning_parolingiz
DB_NAME=pulbot_mini_app
DB_PORT=3306

# OpenAI Configuration
OPENAI_API_KEY=sizning_openai_key

# Telegram Bot Configuration
BOT_TOKEN=sizning_bot_token
WEBHOOK_URL=https://sizning-url.uz

# App Configuration
FLASK_ENV=development
SECRET_KEY=sizning_secret_key

# Click.uz Payment Configuration (MUHIM!)
CLICK_SECRET_KEY=3DSnE96DKz7Nh
CLICK_SERVICE_ID=85417
CLICK_MERCHANT_ID=49266
CLICK_MERCHANT_USER_ID=67944
```

---

## 🚫 HECH QANDAY HOLATDA:

1. ❌ `.env` faylni Git'ga commit qilmang
2. ❌ `config.py` da API key yoki secret key'larni hardcode qilmang
3. ❌ Production secret'larini development'da ishlatmang
4. ❌ Public repository'da sensitive ma'lumotlarni unutmang

---

## ✅ TO'G'RI AMALIYOTLAR:

1. ✅ `.env` fayl allaqachon `.gitignore` da
2. ✅ `config.py` faqat environment variable'larni o'qiydi
3. ✅ `env.example` faqat struktura ko'rsatadi
4. ✅ Render.com'da environment variable'lar alohida sozlanadi

---

## 🌐 Render.com'da Sozlash

Render.com dashboard'ga kirib:

1. **Environment** tab'ga o'ting
2. Quyidagi variable'larni qo'shing:

```env
CLICK_SECRET_KEY=3DSnE96DKz7Nh
CLICK_SERVICE_ID=85417
CLICK_MERCHANT_ID=49266
CLICK_MERCHANT_USER_ID=67944
DB_HOST=sizning_host
DB_USER=sizning_user
DB_PASSWORD=sizning_password
DB_NAME=sizning_database
OPENAI_API_KEY=sizning_key
```

---

## 🔍 Tekshirish

Ma'lumotlar to'g'ri yuklanayaptimi tekshirish:

```python
# app.py'da
from config import CLICK_SECRET_KEY, CLICK_SERVICE_ID

if not CLICK_SECRET_KEY:
    print("⚠️ CLICK_SECRET_KEY topilmadi! .env faylni tekshiring")
    
if not CLICK_SERVICE_ID:
    print("⚠️ CLICK_SERVICE_ID topilmadi! .env faylni tekshiring")
```

---

## 📞 Yordam

Agar sensitive ma'lumotlar commit qilingan bo'lsa:

```bash
# Git tarixdan to'liq o'chirish
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# GitHub'ga push
git push origin --force --all
```

---

## ✨ Xulosa

- ✅ `.env` - Local development uchun
- ✅ `env.example` - Struktura uchun
- ✅ Render.com Environment Variables - Production uchun
- ❌ `config.py` da hardcode - HECH QACHAY

**Xavfsizlik har bir bosqichda muhim!** 🔒
