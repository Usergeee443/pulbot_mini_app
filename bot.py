import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, WEBHOOK_URL, MINI_APP_URL
from database import db

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot va dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    """Start komandasi handler"""
    user = message.from_user
    
    # Foydalanuvchini bazaga qo'shish/yangilash
    try:
        # Foydalanuvchi mavjudligini tekshirish
        existing_user = db.get_user_data(user.id)
        
        if not existing_user:
            # Yangi foydalanuvchi qo'shish (default PREMIUM tarif bilan)
            db.add_user(user.id, user.username, user.first_name, user.last_name)
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user.id}")
        else:
            # Mavjud foydalanuvchi ma'lumotlarini yangilash
            db.update_user_info(user.id, user.username, user.first_name, user.last_name)
            logger.info(f"Foydalanuvchi ma'lumotlari yangilandi: {user.id}")
    
    except Exception as e:
        logger.error(f"Foydalanuvchi ma'lumotlarini saqlashda xatolik: {e}")

    # Mini App tugmasini yaratish
    webapp_button = InlineKeyboardButton(
        text="💰 Balans AI ni ochish",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
    
    # Foydalanuvchi tarifini olish
    tariff = db.get_user_tariff(user.id)
    tariff_emoji = "⭐" if tariff == "PREMIUM" else "🆓"
    
    welcome_text = f"""
🎉 Assalomu alaykum, {user.first_name}!

💰 **Balans AI** ga xush kelibsiz!

{tariff_emoji} **Sizning tarifingiz:** {tariff}

Bu yerda siz:
💰 Moliyaviy hisobotlaringizni boshqarishingiz
📊 AI tahlillar va maslahatlar olishingiz
📈 Batafsil statistikalarni ko'rishingiz
🏦 Qarzlaringizni kuzatishingiz mumkin

Ilovani ochish uchun pastdagi tugmani bosing 👇
"""
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Yordam komandasi"""
    help_text = """
🔧 **Yordam**

📊 **Balans AI** - bu sizning moliyaviy hisobotlaringiz, vazifalaringiz va maqsadlaringizni boshqarish uchun mo'ljallangan mini ilova.

**Mavjud imkoniyatlar:**
💰 Tranzaksiyalarni qo'shish, tahrirlash va o'chirish
✅ Vazifalarni yaratish va kuzatish
🎯 Maqsadlarni belgilash va nazorat qilish

**Foydalanish:**
1. /start - Mini appni ochish
2. /help - Yordam olish
3. /stats - Tezkor statistika

Mini appni ochish uchun /start buyrug'ini yuboring.
"""
    
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def stats_handler(message: types.Message):
    """Tezkor moliyaviy statistika"""
    user_id = message.from_user.id
    
    try:
        # Tranzaksiyalar statistikasi
        transactions = db.get_transactions(user_id, 1000)
        
        if not transactions:
            stats_text = """
📊 **Sizning moliyaviy statistikangiz**

💰 **Moliyaviy holat:**
📈 Daromad: 0 so'm
📉 Xarajat: 0 so'm
🏦 Qarzlar: 0 so'm
💳 Balans: 0 so'm

📱 Tranzaksiyalar qo'shish uchun mini appni oching 👇
"""
        else:
            # Moliyaviy statistika
            total_income = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'income')
            total_expense = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'expense')
            total_debt = sum(float(t['amount']) for t in transactions if t['transaction_type'] == 'debt')
            balance = total_income - total_expense - total_debt
            
            # Bu oydagi statistika
            from datetime import datetime, timedelta
            current_month = datetime.now().replace(day=1)
            this_month_transactions = [t for t in transactions 
                                     if datetime.strptime(str(t['created_at']), '%Y-%m-%d %H:%M:%S') >= current_month]
            
            this_month_income = sum(float(t['amount']) for t in this_month_transactions if t['transaction_type'] == 'income')
            this_month_expense = sum(float(t['amount']) for t in this_month_transactions if t['transaction_type'] == 'expense')
            
            # Eng ko'p ishlatiladigan kategoriya
            from collections import Counter
            categories = [t['category'] for t in transactions]
            top_category = Counter(categories).most_common(1)[0] if categories else ('', 0)
            
            stats_text = f"""
📊 **Sizning moliyaviy statistikangiz**

💰 **Umumiy moliyaviy holat:**
📈 Daromad: {total_income:,.0f} so'm
📉 Xarajat: {total_expense:,.0f} so'm
🏦 Qarzlar: {total_debt:,.0f} so'm
💳 Balans: {balance:,.0f} so'm

📅 **Bu oyda:**
📈 Daromad: {this_month_income:,.0f} so'm
📉 Xarajat: {this_month_expense:,.0f} so'm

📊 **Eng ko'p kategoriya:**
{top_category[0]} ({top_category[1]} marta)

📱 Batafsil tahlil uchun mini appni oching 👇
"""
        
        # Mini App tugmasi
        webapp_button = InlineKeyboardButton(
            text="💰 Balans AI ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await message.answer(stats_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Statistika olishda xatolik: {e}")
        await message.answer(
            "❌ Statistika olishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )

@dp.message()
async def echo_handler(message: types.Message):
    """Boshqa xabarlar uchun javob"""
    webapp_button = InlineKeyboardButton(
        text="💰 Balans AI ochish",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
    
    await message.answer(
        "💰 Moliyaviy hisobotlaringizni ko'rish uchun pastdagi tugmani bosing:",
        reply_markup=keyboard
    )

async def on_startup():
    """Bot ishga tushganda"""
    logger.info("Bot ishga tushdi")
    # Ma'lumotlar bazasiga ulanish
    if not db.connect():
        logger.error("Ma'lumotlar bazasiga ulanib bo'lmadi!")
        return False
    
    # Webhook o'rnatish
    if WEBHOOK_URL != 'YOUR_NGROK_URL_HERE':
        webhook_url = f"{WEBHOOK_URL}/webhook"
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook o'rnatildi: {webhook_url}")
    
    return True

async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("Bot to'xtayapti")
    await bot.session.close()
    db.disconnect()

def create_app():
    """Web ilova yaratish"""
    app = web.Application()
    
    # Webhook handler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path="/webhook")
    
    # Startup va shutdown handlerlar
    app.on_startup.append(lambda app: asyncio.create_task(on_startup()))
    app.on_shutdown.append(lambda app: asyncio.create_task(on_shutdown()))
    
    return app

async def main():
    """Asosiy funksiya"""
    # Ma'lumotlar bazasiga ulanish
    if not await on_startup():
        return
    
    if WEBHOOK_URL == 'YOUR_NGROK_URL_HERE':
        # Polling rejimi (development uchun)
        logger.info("Polling rejimida ishga tushirilmoqda...")
        await dp.start_polling(bot)
    else:
        # Webhook rejimi (production uchun)
        logger.info("Webhook rejimi uchun tayyor")
        # Bu yerda web server Flask tomonidan boshqariladi

if __name__ == "__main__":
    asyncio.run(main())
