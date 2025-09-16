@echo off
chcp 65001 > nul
echo 🚀 Balans AI Mini App ishga tushirilmoqda...

REM Virtual muhitni tekshirish va yaratish
if exist "venv" (
    echo 📦 Virtual muhit faollashtirilmoqda...
    call venv\Scripts\activate
) else (
    echo ⚠️  Virtual muhit topilmadi. Yaratilmoqda...
    python -m venv venv
    call venv\Scripts\activate
    echo 📥 Bog'liqliklar o'rnatilmoqda...
    pip install -r requirements.txt
)

REM Ma'lumotlar bazasi ulanishini tekshirish
echo 🔍 Ma'lumotlar bazasi ulanishi tekshirilmoqda...
python -c "from database import db; print('✅ Ma\'lumotlar bazasiga ulanish muvaffaqiyatli' if db.connect() else '❌ Ma\'lumotlar bazasiga ulanishda xatolik')"

REM Konfiguratsiyani tekshirish
echo ⚙️  Konfiguratsiya tekshirilmoqda...
python -c "from config import BOT_TOKEN, WEBHOOK_URL; import sys; sys.exit(1) if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE' else (print('ℹ️  Development rejimi: WEBHOOK_URL o\'rnatilmagan') if WEBHOOK_URL == 'YOUR_NGROK_URL_HERE' else print(f'✅ Webhook URL: {WEBHOOK_URL}')); print('✅ Konfiguratsiya tayyor')"

if %errorlevel% neq 0 (
    echo ❌ Konfiguratsiya xatoligi. Iltimos config.py ni tekshiring.
    pause
    exit /b 1
)

echo 🎯 Ilovani ishga tushirish...
echo 📱 Mini App URL: http://localhost:8080/miniapp
echo 🤖 Bot bilan /start buyrug'ini yuboring
echo.
echo To'xtatish uchun Ctrl+C bosing
echo ================================

REM Ilovani ishga tushirish
python main.py

pause
