import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from utils import load_users, get_user, update_user, check_cooldown, RARITY_POINTS
from cards import load_cards, get_random_card, get_card_by_id, get_random_card_by_rarity

async def send_card_to_message(message, card, is_repeated, points_earned, new_balance):
    rarity_emoji = {
        "необычная": "🟢",
        "редкая": "🔵",
        "эпическая": "🟣",
        "мифическая": "🟡",
        "ультра": "🔴"
    }.get(card["rarity"], "⚪")
    repeat_text = "🔄 Повторная!" if is_repeated else "✅ Новая!"
    caption = (
        f"🖼 Работа от @{card['author']}\n"
        f"{rarity_emoji} Редкость: {card['rarity'].capitalize()}\n"
        f"{repeat_text}\n"
        f"✨ +{points_earned} очков\n"
        f"💰 Новый баланс: {new_balance} очков"
    )
    with open(card['file_path'], 'rb') as photo:
        await message.reply_photo(photo=photo, caption=caption)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(
        "👋 Добро пожаловать в карточного бота!\n\n"
        "Команды:\n"
        "/cards - получить случайную карту (раз в час)\n"
        "/balance - проверить баланс\n"
        "/collection - ваша коллекция\n"
        "/cases - открыть кейсы\n"
        "/transfer @user card_id - передать карту\n"
        "/admin - админ панель"
    )

async def cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    can, remaining = check_cooldown(user_data.get("last_card", 0))
    if not can:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(f"⏳ Подождите еще {hours}ч {minutes}мин до следующей бесплатной карты.")
        return

    card = get_random_card()
    if not card:
        await update.message.reply_text("😕 В колоде пока нет карт.")
        return

    is_repeated = card['id'] in user_data.get("cards", [])
    base = RARITY_POINTS[card['rarity']]
    points = base // 2 if is_repeated else base

    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])

    user_data["balance"] = user_data.get("balance", 0) + points
    user_data["last_card"] = time.time()
    update_user(user_id, user_data)

    await send_card_to_message(update.message, card, is_repeated, points, user_data["balance"])

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    await update.message.reply_text(f"💰 Ваш баланс: {user_data.get('balance', 0)} очков")

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    card_ids = user_data.get("cards", [])
    if not card_ids:
        await update.message.reply_text("📭 У вас пока нет карт.")
        return

    all_cards = load_cards()
    lines = []
    for cid in card_ids:
        card = next((c for c in all_cards if c['id'] == cid), None)
        if card:
            lines.append(f"• {card['author']} ({card['rarity'].capitalize()})")
    await update.message.reply_text("📚 Ваша коллекция:\n" + "\n".join(lines))

async def cases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔹 Мини-кейс (2000 очков)", callback_data="buy_mini")],
        [InlineKeyboardButton("🔸 Тайно-кейс (5000 очков)", callback_data="buy_secret")],
        [InlineKeyboardButton("🔺 Мега-кейс (10000 очков)", callback_data="buy_mega")],
    ]
    await update.message.reply_text("Выберите кейс:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user(user_id)
    case = query.data.split("_")[1]  # mini, secret, mega

    prices = {"mini": 2000, "secret": 5000, "mega": 10000}
    price = prices.get(case)
    if price is None:
        await query.edit_message_text("Неверный кейс.")
        return

    if user_data.get("balance", 0) < price:
        await query.edit_message_text("❌ Недостаточно очков!")
        return

    # Вероятности для каждого кейса
    chances = {
        "mini":  {"необычная":0.7, "редкая":0.2, "эпическая":0.07, "мифическая":0.02, "ультра":0.01},
        "secret":{"необычная":0.5, "редкая":0.3, "эпическая":0.15, "мифическая":0.04, "ультра":0.01},
        "mega":  {"необычная":0.3, "редкая":0.3, "эпическая":0.25, "мифическая":0.1,  "ультра":0.05}
    }
    ch = chances[case]
    rarity = random.choices(list(ch.keys()), weights=list(ch.values()))[0]

    card = get_random_card_by_rarity(rarity)
    if not card:
        await query.edit_message_text("😕 Карт этой редкости пока нет.")
        return

    is_repeated = card['id'] in user_data.get("cards", [])
    base = RARITY_POINTS[rarity]
    points = base // 2 if is_repeated else base

    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])

    user_data["balance"] = user_data["balance"] - price + points
    update_user(user_id, user_data)

    await query.message.delete()
    await send_card_to_message(query.message, card, is_repeated, points, user_data["balance"])

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Использование: /transfer @username card_id")
        return

    target_name = args[0].lstrip('@')
    card_id = args[1]
    from_id = update.effective_user.id
    from_data = get_user(from_id)

    if card_id not in from_data.get("cards", []):
        await update.message.reply_text("❌ У вас нет такой карты.")
        return

    # Поиск получателя по username
    users = load_users()
    to_id = None
    for uid, data in users.items():
        if data.get("username", "").lower() == target_name.lower():
            to_id = int(uid)
            break

    if not to_id:
        await update.message.reply_text("❌ Пользователь с таким username не найден в базе.")
        return

    if to_id == from_id:
        await update.message.reply_text("❌ Нельзя передать карту самому себе.")
        return

    # Передача
    from_data["cards"].remove(card_id)
    update_user(from_id, from_data)

    to_data = get_user(to_id)
    to_data.setdefault("cards", []).append(card_id)
    update_user(to_id, to_data)

    await update.message.reply_text(f"✅ Карта передана пользователю @{target_name}.")

# ---------- Админка ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await update.message.reply_text(
        "Админ команды:\n"
        "/add_points user_id сумма\n"
        "/give_card user_id card_id\n"
        "/stats"
    )

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except:
        await update.message.reply_text("Использование: /add_points user_id сумма")
        return
    data = get_user(uid)
    data["balance"] = data.get("balance", 0) + amount
    update_user(uid, data)
    await update.message.reply_text(f"✅ Начислено {amount} очков пользователю {uid}.")

async def give_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    try:
        uid = int(context.args[0])
        card_id = context.args[1]
    except:
        await update.message.reply_text("Использование: /give_card user_id card_id")
        return
    card = get_card_by_id(card_id)
    if not card:
        await update.message.reply_text("❌ Карта не найдена.")
        return
    data = get_user(uid)
    if card_id in data.get("cards", []):
        await update.message.reply_text("❌ У пользователя уже есть эта карта.")
        return
    data.setdefault("cards", []).append(card_id)
    update_user(uid, data)
    await update.message.reply_text(f"✅ Карта {card_id} выдана пользователю {uid}.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    users = load_users()
    total = len(users)
    cards_count = sum(len(u.get("cards", [])) for u in users.values())
    balance_sum = sum(u.get("balance", 0) for u in users.values())
    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"Пользователей: {total}\n"
        f"Всего карт: {cards_count}\n"
        f"Общий баланс: {balance_sum} очков"
    )
