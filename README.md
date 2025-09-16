# 📊 Balans AI - Telegram Mini App

Balans AI bot uchun hisobotlarni ko'rsatish, tahrirlash, o'chirish va qo'shish imkoniyatlari bo'lgan Telegram Mini App.

## 🚀 Xususiyatlar

- 💰 **Tranzaksiyalar**: Daromad, xarajat va qarzlarni boshqarish
- 📊 **Dashboard**: Asosiy sahifada barcha statistikalar
- 📈 **Grafiklar**: Oylik va kategoriya bo'yicha tahlil
- 🏦 **Qarzlar**: Alohida qarzlar bo'limi
- 📱 **Full Screen**: To'liq ekran rejimi
- 🎨 **Premium UI**: Mukammal zamonaviy dizayn

## 🛠 Texnologiyalar

- **Backend**: Python, Flask, Aiogram 3.x
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Ma'lumotlar bazasi**: MySQL
- **Deployment**: ngrok (development uchun)

## 📋 O'rnatish

### 1. Loyihani yuklab olish
```bash
git clone <repository_url>
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

### 4. Konfiguratsiya
`.env` faylini yarating va kerakli ma'lumotlarni kiriting:

```bash
# .env fayli yaratish
cp env.example .env
```

`.env` faylida quyidagi ma'lumotlarni o'zgartiring:

```env
# Bot token (BotFather dan olingan)
BOT_TOKEN=your_actual_bot_token_here

# ngrok URL (development uchun)
WEBHOOK_URL=your_ngrok_url_here

# Ma'lumotlar bazasi (agar kerak bo'lsa)
DB_HOST=195.200.29.240
DB_PORT=3306
DB_USER=db
DB_PASSWORD=your_db_password
DB_NAME=MaqsadAiBot
```

### 5. Ma'lumotlar bazasi
Ma'lumotlar bazasi allaqachon sozlangan:
- Host: 195.200.29.240
- Port: 3306
- User: db
- Password: 33608540414
- Database: MaqsadAiBot

## 🚀 Ishga tushirish

### Development rejimi (ngrok bilan)

1. **ngrok o'rnatish va ishga tushirish:**
```bash
# ngrok yuklab oling: https://ngrok.com/download
ngrok http 5000
```

2. **ngrok URL ni config.py ga qo'shish:**
```python
WEBHOOK_URL = "https://your-ngrok-url.ngrok.io"
```

3. **Bot token olish:**
- [@BotFather](https://t.me/BotFather) ga boring
- Yangi bot yarating yoki mavjud bot tokenini oling
- Token ni `config.py` ga qo'shing

4. **Ilovani ishga tushirish:**
```bash
python main.py
```

### Production rejimi

1. **Server sozlash:**
```bash
# WEBHOOK_URL ni production server URL ga o'zgartiring
WEBHOOK_URL = "https://your-domain.com"
```

2. **Ishga tushirish:**
```bash
python main.py
```

## 📱 Foydalanish

1. Telegram botingizga `/start` buyrug'ini yuboring
2. "📊 Hisobotlarni ochish" tugmasini bosing
3. Mini App to'liq ekranda ochiladi va siz quyidagilarni qila olasiz:
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
├── database.py          # Ma'lumotlar bazasi
├── config.py            # Konfiguratsiya
├── requirements.txt     # Bog'liqliklar
├── templates/
│   └── index.html       # Mini App HTML
├── static/
│   ├── css/
│   │   └── style.css    # Stillar
│   └── js/
│       └── app.js       # JavaScript
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

### Bot javob bermayapti
1. Bot token to'g'riligini tekshiring
2. Webhook URL ni tekshiring
3. Ma'lumotlar bazasi ulanishini tekshiring

### Mini App ochilmayapti
1. ngrok ishlab turganini tekshiring
2. Flask server ishlab turganini tekshiring
3. Browser consoleda xatolarni tekshiring

### Ma'lumotlar saqlanmayapti
1. Ma'lumotlar bazasi ulanishini tekshiring
2. Server loglarini tekshiring
3. API so'rovlar to'g'riligini tekshiring

## 📞 Yordam

Savollar bo'lsa, quyidagi ma'lumotlar orqali murojaat qiling:
- GitHub Issues
- Telegram: @your_username

## 📄 Litsenziya

MIT License
