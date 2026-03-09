import logging
import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
from handlers import (
    start, cards, balance, collection, cases, case_callback, transfer,
    admin, add_points, remove_points, give_card, reset_cooldown, reset_bonus,
    stats, reload_cards, top, bonus, roulette
)
from utils import init_db_pool, close_db_pool, db_pool

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server listening on port {port}")
    server.serve_forever()

async def init_db():
    """Инициализация пула соединений с БД"""
    try:
        await init_db_pool(config.DATABASE_URL)
        print("✅ Database pool created successfully")
    except Exception as e:
        print(f"❌ Failed to create database pool: {e}")
        # Можно завершить приложение, если база критична
        # exit(1)

async def shutdown_db():
    await close_db_pool()
    print("✅ Database pool closed")

def main():
    # Запускаем health-сервер
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("🤖 Бот запускается...")

    # Инициализируем базу данных синхронно
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
        if db_pool is None:
            print("❌ Database pool is None after init. Exiting.")
            return
    except Exception as e:
        print(f"❌ Unhandled exception during DB init: {e}")
        return

    app = Application.builder().token(config.TOKEN).build()

    # Команды игроков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cards", cards))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("collection", collection))
    app.add_handler(CommandHandler("cases", cases))
    app.add_handler(CommandHandler("transfer", transfer))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("leaders", top))  # синоним
    app.add_handler(CommandHandler("bonus", bonus))
    app.add_handler(CommandHandler("roulette", roulette))

    # Админ-команды
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("add_points", add_points))
    app.add_handler(CommandHandler("remove_points", remove_points))
    app.add_handler(CommandHandler("give_card", give_card))
    app.add_handler(CommandHandler("reset_cooldown", reset_cooldown))
    app.add_handler(CommandHandler("reset_bonus", reset_bonus))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reload_cards", reload_cards))

    # Callback для кейсов
    app.add_handler(CallbackQueryHandler(case_callback, pattern="^case_"))

    try:
        app.run_polling()
    finally:
        # Закрываем пул при завершении
        loop.run_until_complete(shutdown_db())
        loop.close()

if __name__ == "__main__":
    main()
