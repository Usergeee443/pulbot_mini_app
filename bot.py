import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import BOT_TOKEN, MINI_APP_URL
from database import db

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot va dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Start buyrug'i"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Foydalanuvchi"
    
    # Foydalanuvchini ma'lumotlar bazasiga qo'shish
    try:
        if not db.user_exists(user_id):
            db.add_user(user_id, first_name)
            logger.info(f"Yangi foydalanuvchi qo'shildi: {user_id}")
    except Exception as e:
        logger.error(f"Foydalanuvchi qo'shishda xatolik: {e}")
    
    # Mini app URL ga user ID qo'shish
    mini_app_url = f"{MINI_APP_URL}?user_id={user_id}"
    
    # Mini app tugmasi
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📱 Mini App ochish",
                web_app=WebAppInfo(url=mini_app_url)
            )],
            [InlineKeyboardButton(
                text="📊 Hisobotlar",
                web_app=WebAppInfo(url=mini_app_url)
            )]
        ]
    )
    
    await message.answer(
        f"Salom {first_name}! 👋\n\n"
        "💰 Balans AI - sizning moliyaviy yordamchingiz!\n\n"
        "📱 Mini App orqali:\n"
        "• Balansingizni kuzating\n"
        "• Tranzaksiyalarni boshqaring\n"
        "• Tahlillar va grafiklarni ko'ring\n"
        "• AI yordamchisidan foydalaning\n\n"
        "Quyidagi tugmalardan birini bosing:",
        reply_markup=keyboard
    )

@dp.message()
async def message_handler(message: types.Message):
    """Boshqa xabarlar uchun"""
    user_id = message.from_user.id
    mini_app_url = f"{MINI_APP_URL}?user_id={user_id}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📱 Mini App ochish",
                web_app=WebAppInfo(url=mini_app_url)
            )]
        ]
    )
    
    await message.answer(
        "Mini App orqali barcha funksiyalardan foydalaning!",
        reply_markup=keyboard
    )

async def main():
    """Botni ishga tushirish"""
    try:
        logger.info("Bot ishga tushirilmoqda...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot ishga tushirishda xatolik: {e}")

if __name__ == "__main__":
    asyncio.run(main())
