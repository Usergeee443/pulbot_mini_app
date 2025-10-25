#!/usr/bin/env python3
"""Main application entry point"""
import os

if __name__ == "__main__":
    print("🚀 Balans AI Mini App ishga tushirilmoqda...")
    print("📱 Telegram Mini App: http://localhost:8081/miniapp")
    print("=" * 60)
    
    # Flask app ni ishga tushirish
    from app import app
    
    port = int(os.environ.get('PORT', 8081))
    print(f"✅ Server ishga tushdi: http://localhost:{port}")
    print("✅ Mini App ochib sinab ko'ring!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)
