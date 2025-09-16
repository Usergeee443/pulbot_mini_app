# 💰 Balans AI - Telegram Mini App

Balans AI bot uchun mukammal moliyaviy hisobotlar Telegram Mini App.

## 🚀 Xususiyatlar

- 💰 **Dashboard**: Asosiy sahifada barcha statistikalar
- 📊 **Interaktiv grafiklar**: Chart.js bilan oylik va kategoriya tahlillari
- 💸 **Tranzaksiyalar**: Daromad, xarajat qo'shish va boshqarish
- 🏦 **Qarzlar**: Alohida qarzlar bo'limi
- 📈 **Tahlil**: Batafsil hisobotlar va statistikalar
- 📱 **Full Screen**: To'liq ekran rejimi
- 🎨 **Premium UI**: Mukammal zamonaviy dizayn

## 🛠 Texnologiyalar

- **Backend**: Python, Flask, Aiogram 3.x
- **Frontend**: HTML, CSS, JavaScript + Chart.js
- **Ma'lumotlar bazasi**: MySQL/PyMySQL
- **Deployment**: Render.com, Gunicorn

## 📋 O'rnatish (Local)

### 1. Loyihani yuklab olish
```bash
git clone https://github.com/Usergeee443/pulbot_mini_app.git
cd pulbot_mini_app
```

### 2. Virtual muhit yaratish
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows
```

### 3. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Environment sozlash
```bash
cp env.example .env
```

`.env` faylini tahrirlang:
```env
# Bot sozlamalari
BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=your_webhook_url

# Ma'lumotlar bazasi
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

# Flask
FLASK_HOST=127.0.0.1
FLASK_PORT=8080
SECRET_KEY=your_secret_key
```

### 5. Ishga tushirish
```bash
./start.sh  # Linux/Mac
# yoki
python main.py
```

## 🌐 Render.com ga Deploy

### 1. GitHub repository yaratish
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin your-repo-url
git push -u origin main
```

### 2. Render.com sozlash
1. [Render.com](https://render.com) ga kiring
2. "New" → "Web Service"
3. GitHub repository ni tanlang
4. Sozlamalar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT main:app`
   - **Environment**: `Python 3`

### 3. Environment Variables
Render.com da quyidagi environment variables ni qo'shing:
```
BOT_TOKEN=your_bot_token
DB_HOST=your_db_host
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
FLASK_HOST=0.0.0.0
FLASK_PORT=10000
SECRET_KEY=your_secret_key
WEBHOOK_URL=https://your-app.onrender.com
```

## 🤖 Bot sozlash

1. [@BotFather](https://t.me/BotFather) ga boring
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting
4. Bot username kiriting
5. Token ni `.env` fayliga qo'ying

### Webhook sozlash
Deploy qilingandan keyin:
```bash
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-app.onrender.com/webhook"}'
```

## 📱 Foydalanish

1. Botingizga `/start` buyrug'ini yuboring
2. "📊 Hisobotlarni ochish" tugmasini bosing
3. Mini App to'liq ekranda ochiladi:
   - 📊 **Dashboard**: Asosiy statistikalar va grafiklar
   - 💰 **Tranzaksiyalar**: Daromad, xarajat qo'shish va boshqarish
   - 🏦 **Qarzlar**: Qarzlarni alohida kuzatish
   - 📈 **Tahlil**: Batafsil grafiklar va hisobotlar

## 🔧 API Endpoints

### Tranzaksiyalar
- `GET /api/transactions/<user_id>` - Tranzaksiyalarni olish
- `POST /api/transactions` - Tranzaksiya qo'shish
- `PUT /api/transactions/<id>` - Tranzaksiyani yangilash
- `DELETE /api/transactions/<id>` - Tranzaksiyani o'chirish

### Statistikalar
- `GET /api/statistics/<user_id>` - Batafsil statistikalarni olish
- `GET /api/debts/<user_id>` - Qarzlar ro'yxatini olish

## 📁 Fayl tuzilmasi

```
pulbot_mini_app/
├── main.py              # Asosiy fayl
├── app.py               # Flask web ilova
├── bot.py               # Telegram bot
├── database.py          # PyMySQL database
├── config.py            # Konfiguratsiya
├── requirements.txt     # Bog'liqliklar
├── runtime.txt          # Python versiyasi
├── Procfile            # Gunicorn konfiguratsiyasi
├── .env                # Environment variables
├── .gitignore          # Git ignore
├── env.example         # Environment namunasi
├── templates/
│   └── index.html       # Mini App HTML
├── static/
│   ├── css/
│   │   └── style.css    # Premium CSS
│   └── js/
│       └── app.js       # JavaScript + Chart.js
└── README.md            # Qo'llanma
```

## 🎨 UI Xususiyatlari

- 📱 **Full Screen**: To'liq ekran rejimi
- 🎨 **Premium Design**: Mukammal zamonaviy dizayn
- 📊 **Interactive Charts**: Chart.js bilan grafiklar
- 🌙 **Dark/Light Theme**: Telegram temasiga moslashadi
- ⚡ **Fast Loading**: Tez yuklanish va smooth animatsiyalar
- 🔄 **Real-time Updates**: Real vaqt yangilanishlar
- 📱 **Mobile First**: Mobil qurilmalar uchun optimallashtirilgan

## 🐛 Muammolarni hal qilish

### Deploy muammolari
1. Environment variables to'g'riligini tekshiring
2. Database ulanish ma'lumotlarini tekshiring
3. Render.com loglarini ko'ring

### Bot javob bermayapti
1. Bot token to'g'riligini tekshiring
2. Webhook URL ni tekshiring
3. `/setWebhook` qilganingizni tekshiring

### Ma'lumotlar saqlanmayapti
1. Database credentials ni tekshiring
2. Server loglarini tekshiring
3. API so'rovlar to'g'riligini tekshiring

## 📄 Litsenziya

MIT License

## 👨‍💻 Muallif

Telegram: @your_username
GitHub: @Usergeee443
