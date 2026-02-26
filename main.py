import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
from handlers import (
    start, cards, balance, collection, cases, case_callback, transfer,
    admin, add_points, remove_points, give_card, reset_cooldown, stats, reload_cards
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ===== HEALTH CHECK SERVER для Render =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        return  # отключаем логи health-запросов

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server listening on port {port}")
    server.serve_forever()

def main():
    # Запускаем health-сервер в фоновом потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("🤖 Бот запускается...")

    app = Application.builder().token(config.TOKEN).build()

    # Команды игроков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cards", cards))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("collection", collection))
    app.add_handler(CommandHandler("cases", cases))
    app.add_handler(CommandHandler("transfer", transfer))

    # Админ-команды
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("add_points", add_points))
    app.add_handler(CommandHandler("remove_points", remove_points))
    app.add_handler(CommandHandler("give_card", give_card))
    app.add_handler(CommandHandler("reset_cooldown", reset_cooldown))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reload_cards", reload_cards))

    # Callback для кейсов
    app.add_handler(CallbackQueryHandler(case_callback, pattern="^case_"))

    app.run_polling()

if __name__ == "__main__":
    main()
