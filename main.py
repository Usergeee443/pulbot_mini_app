#!/usr/bin/env python3
"""
Balans AI Mini App
Telegram bot va Flask web ilovasini birlashtiruvchi asosiy fayl
"""

import asyncio
import logging
import threading
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from app import app as flask_app
from bot import bot, dp, on_startup, on_shutdown
from config import FLASK_HOST, FLASK_PORT, WEBHOOK_URL

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBotWebhookHandler:
    """Telegram bot webhook handler"""
    
    def __init__(self):
        self.bot = bot
        self.dp = dp
    
    async def setup_webhook(self, app: web.Application):
        """Webhook sozlash"""
        # Webhook handler ro'yxatdan o'tkazish
        SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot
        ).register(app, path="/webhook")
        
        # Bot ishga tushirish
        await on_startup()
        
        logger.info("Telegram bot webhook sozlandi")
    
    async def cleanup_webhook(self, app: web.Application):
        """Webhook tozalash"""
        await on_shutdown()

def run_flask_app():
    """Flask ilovasini alohida threadda ishga tushirish"""
    logger.info(f"Flask ilova ishga tushirilmoqda: http://{FLASK_HOST}:{FLASK_PORT}")
    flask_app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )

async def create_aiohttp_app():
    """aiohttp ilovasini yaratish"""
    app = web.Application()
    
    # Telegram webhook handler
    webhook_handler = TelegramBotWebhookHandler()
    
    # Startup va cleanup handlerlar
    app.on_startup.append(webhook_handler.setup_webhook)
    app.on_cleanup.append(webhook_handler.cleanup_webhook)
    
    # Static fayllar uchun handler (agar kerak bo'lsa)
    app.router.add_get('/health', lambda request: web.Response(text='OK'))
    
    return app

async def run_webhook_server():
    """Webhook server ishga tushirish"""
    app = await create_aiohttp_app()
    
    # aiohttp serverni ishga tushirish
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Webhook uchun alohida port (Flask dan farqli)
    webhook_port = FLASK_PORT + 1
    site = web.TCPSite(runner, FLASK_HOST, webhook_port)
    await site.start()
    
    logger.info(f"Webhook server ishga tushdi: http://{FLASK_HOST}:{webhook_port}")
    
    # Server to'xtagunicha kutish
    try:
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        logger.info("Server to'xtatilmoqda...")
    finally:
        await runner.cleanup()

def main():
    """Asosiy funksiya"""
    logger.info("🚀 Balans AI Mini App ishga tushirilmoqda...")
    
    try:
        if WEBHOOK_URL == 'YOUR_NGROK_URL_HERE':
            # Development rejimi - faqat Flask
            logger.info("Development rejimi: faqat Flask server")
            run_flask_app()
        else:
            # Production rejimi - Flask + Webhook
            logger.info("Production rejimi: Flask + Telegram Webhook")
            
            # Flask ni alohida threadda ishga tushirish
            flask_thread = threading.Thread(target=run_flask_app, daemon=True)
            flask_thread.start()
            
            # Webhook serverni asosiy threadda ishga tushirish
            asyncio.run(run_webhook_server())
    
    except KeyboardInterrupt:
        logger.info("Dastur to'xtatildi")
    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    main()
