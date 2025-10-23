import asyncio
import threading
import time
from bot import main as bot_main
from app import app
from config import FLASK_PORT

def run_flask():
    """Flask app ni ishga tushirish"""
    app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)

def run_bot():
    """Bot ni ishga tushirish"""
    asyncio.run(bot_main())

if __name__ == "__main__":
    print("🚀 Balans AI Mini App ishga tushirilmoqda...")
    print(f"📱 Mini App URL: http://localhost:{FLASK_PORT}/miniapp")
    print("🤖 Bot va Flask app bir vaqtda ishga tushirilmoqda...")
    print("To'xtatish uchun Ctrl+C bosing")
    print("=" * 50)
    
    # Flask ni alohida thread da ishga tushirish
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Kichik kutish
    time.sleep(2)
    
    # Bot ni ishga tushirish
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n👋 Ilova to'xtatildi")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
