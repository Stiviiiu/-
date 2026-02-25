import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
from handlers import (
    start, cards, balance, collection, cases, buy_case, transfer,
    admin_panel, add_points, give_card, stats
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def main():
    app = Application.builder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cards", cards))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("collection", collection))
    app.add_handler(CommandHandler("cases", cases))
    app.add_handler(CommandHandler("transfer", transfer))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("add_points", add_points))
    app.add_handler(CommandHandler("give_card", give_card))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(buy_case, pattern="^buy_"))

    app.run_polling()

if __name__ == "__main__":
    main()
