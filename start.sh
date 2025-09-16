#!/bin/bash

echo "🚀 Balans AI Mini App ishga tushirilmoqda..."

# Virtual muhitni faollashtirish
if [ -d "venv" ]; then
    echo "📦 Virtual muhit faollashtirilmoqda..."
    source venv/bin/activate
else
    echo "⚠️  Virtual muhit topilmadi. Yaratilmoqda..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Bog'liqliklar o'rnatilmoqda..."
    pip install -r requirements.txt
fi

# Ma'lumotlar bazasi ulanishini tekshirish
echo "🔍 Ma'lumotlar bazasi ulanishi tekshirilmoqda..."
python3 -c "from database import db; print('✅ Ma\'lumotlar bazasiga ulanish muvaffaqiyatli' if db.connect() else '❌ Ma\'lumotlar bazasiga ulanishda xatolik')"

# .env faylini tekshirish
if [ ! -f ".env" ]; then
    echo "⚠️  .env fayli topilmadi. Yaratilmoqda..."
    cp env.example .env 2>/dev/null || echo "env.example fayli topilmadi"
    echo "📝 .env faylini tahrirlang va kerakli ma'lumotlarni kiriting"
fi

# Konfiguratsiyani tekshirish
echo "⚙️  Konfiguratsiya tekshirilmoqda..."
python3 -c "
from config import BOT_TOKEN, WEBHOOK_URL
print(f'🤖 Bot Token: {BOT_TOKEN[:10]}...' if BOT_TOKEN else '⚠️  BOT_TOKEN topilmadi')
if WEBHOOK_URL == 'YOUR_NGROK_URL_HERE':
    print('ℹ️  Development rejimi: WEBHOOK_URL o\'rnatilmagan')
else:
    print(f'✅ Webhook URL: {WEBHOOK_URL}')
print('✅ Konfiguratsiya .env faylidan yuklandi')
"

if [ $? -ne 0 ]; then
    echo "❌ Konfiguratsiya xatoligi. Iltimos config.py ni tekshiring."
    exit 1
fi

echo "🎯 Ilovani ishga tushirish..."
echo "📱 Mini App URL: http://localhost:8080/miniapp"
echo "🤖 Bot bilan /start buyrug'ini yuboring"
echo ""
echo "To'xtatish uchun Ctrl+C bosing"
echo "================================"

# Ilovani ishga tushirish
python3 main.py
