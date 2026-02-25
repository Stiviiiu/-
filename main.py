import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
from handlers import (
    start, cards, balance, collection, cases, case_callback, transfer,
    admin, add_points, remove_points, give_card, reset_cooldown, stats, reload_cards
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    """Запуск бота"""
    # Создаем приложение
    app = Application.builder().token(config.TOKEN).build()
    
    # Добавляем обработчики команд
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
    
    # Обработчик кнопок
    app.add_handler(CallbackQueryHandler(case_callback, pattern="^case_"))
    
    # Запускаем бота
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
