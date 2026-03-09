import time
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from utils import (
    get_user, update_user, check_cooldown,
    RARITY_POINTS, RARITY_EMOJI, db_pool
)
from cards import (
    load_cards, get_random_card, get_card_by_id,
    open_epic_case, open_mythic_case, open_legendary_case,
    EPIC_CASE, MYTHIC_CASE, LEGENDARY_CASE
)

# ---------- Вспомогательные функции ----------
async def send_card_message(message, card, is_repeated, points_earned, new_balance):
    emoji = RARITY_EMOJI.get(card["rarity"], "⚪")
    repeat_text = "🔄 ПОВТОРНАЯ!" if is_repeated else "✅ НОВАЯ КАРТА!"
    caption = (
        f"🎴 <b>Карточка найдена!</b>\n\n"
        f"👤 Автор: @{card['author']}\n"
        f"{emoji} Редкость: <b>{card['rarity'].upper()}</b>\n"
        f"{repeat_text}\n\n"
        f"✨ +{points_earned} очков\n"
        f"💰 Новый баланс: <b>{new_balance}</b> очков"
    )
    with open(card['file_path'], 'rb') as photo:
        await message.reply_photo(photo=photo, caption=caption, parse_mode='HTML')

async def resolve_target(target: str):
    async with db_pool.acquire() as conn:
        if target.startswith('@'):
            username = target[1:].lower()
            row = await conn.fetchrow("SELECT user_id FROM users WHERE LOWER(username) = $1", username)
            if row:
                return row['user_id'], target
            return None, f"❌ Пользователь {target} не найден в базе."
        else:
            try:
                uid = int(target)
            except ValueError:
                return None, "❌ Неверный формат. Укажите @username или числовой ID."
            row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", uid)
            if row:
                return uid, target
            else:
                return None, f"❌ Пользователь с ID {uid} не найден в базе."

# ---------- Команды игроков ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_user(user.id, user.username)
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🎮 <b>Карточная игра (обновлённая версия)</b>\n\n"
        "📋 <b>Команды:</b>\n"
        "🎴 /cards - получить карту (раз в час)\n"
        "💰 /balance - проверить баланс\n"
        "📚 /collection - коллекция карт (с ID для передачи)\n"
        "🎁 /cases - открыть кейсы\n"
        "🔄 /transfer @user card_id - передать карту\n"
        "🏆 /top - топ игроков по очкам\n"
        "🎲 /bonus - бонусная карта (раз в 24 часа)\n"
        "💣 /roulette сумма - русская рулетка (50% удвоить/потерять)\n\n"
        "⭐ <b>Очки за редкость:</b>\n"
        "🟢 Необычная - 50\n🔵 Редкая - 100\n🟣 Эпическая - 200\n🟡 Мифическая - 500\n🔴 Ультра - 1000\n\n"
        "🔄 За повторную карту даётся 50% очков"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    can, remaining = await check_cooldown(user_data.get("last_card", 0), 1)
    if not can:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(
            f"⏳ <b>Кулдаун!</b>\nСледующая карта через: {hours}ч {minutes}мин",
            parse_mode='HTML'
        )
        return
    card = get_random_card()
    if not card:
        await update.message.reply_text("❌ В колоде пока нет карт!")
        return
    is_repeated = card['id'] in user_data.get("cards", [])
    base_points = RARITY_POINTS[card['rarity']]
    points_earned = base_points // 2 if is_repeated else base_points
    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])
    user_data["balance"] = user_data.get("balance", 0) + points_earned
    user_data["last_card"] = int(datetime.now().timestamp())
    await update_user(user.id, user_data)
    await send_card_message(update.message, card, is_repeated, points_earned, user_data["balance"])

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    cards_count = len(user_data.get("cards", []))
    text = f"💰 <b>Ваш баланс</b>\n\nОчки: <b>{user_data.get('balance', 0)}</b>\nКарт в коллекции: <b>{cards_count}</b>"
    await update.message.reply_text(text, parse_mode='HTML')

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    card_ids = user_data.get("cards", [])
    if not card_ids:
        await update.message.reply_text("📭 У вас пока нет карт в коллекции!")
        return
    all_cards = load_cards()
    rarity_author_cards = {rarity: {} for rarity in RARITY_POINTS.keys()}
    for card_id in card_ids:
        card = next((c for c in all_cards if c['id'] == card_id), None)
        if card:
            rarity_author_cards[card['rarity']].setdefault(card['author'], []).append(card)
    total_cards = len(card_ids)
    text = f"📚 <b>Ваша коллекция (ID для передачи):</b> всего карт: {total_cards}\n\n"
    for rarity, authors in rarity_author_cards.items():
        if authors:
            emoji = RARITY_EMOJI[rarity]
            rarity_total = sum(len(cards) for cards in authors.values())
            text += f"{emoji} <b>{rarity.upper()}</b> ({rarity_total} шт.)\n"
            for author, cards in authors.items():
                text += f"  • @{author} ({len(cards)} шт.):\n"
                for card in cards:
                    text += f"      <code>{card['id']}</code>\n"
            text += "\n"
    if len(text) > 4000:
        text = text[:4000] + "...\n(слишком много карт, показаны не все)"
    await update.message.reply_text(text, parse_mode='HTML')

async def cases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📦 Эпический кейс (1000🌟)", callback_data="case_epic")],
        [InlineKeyboardButton("📦 Мифический кейс (2000🌟)", callback_data="case_mythic")],
        [InlineKeyboardButton("📦 Легендарный кейс (5000🌟)", callback_data="case_legendary")],
        [InlineKeyboardButton("❌ ОТМЕНА", callback_data="case_cancel")]
    ]
    epic_text = "\n".join([f"  {item.get('rarity', str(item.get('amount'))+'🌟')}: {item['weight']}%" for item in EPIC_CASE["items"]])
    mythic_text = "\n".join([f"  {item.get('rarity', str(item.get('amount'))+'🌟')}: {item['weight']}%" for item in MYTHIC_CASE["items"]])
    legend_text = "\n".join([f"  {item.get('rarity', str(item.get('amount'))+'🌟')}: {item['weight']}%" for item in LEGENDARY_CASE["items"]])
    text = (
        "🎁 <b>МАГАЗИН КЕЙСОВ</b>\n\n"
        f"📦 <b>Эпический кейс (1000🌟)</b>\n{epic_text}\n\n"
        f"📦 <b>Мифический кейс (2000🌟)</b>\n{mythic_text}\n\n"
        f"📦 <b>Легендарный кейс (5000🌟)</b>\n{legend_text}"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "case_cancel":
        await query.edit_message_text("❌ Покупка отменена")
        return
    user = query.from_user
    user_data = await get_user(user.id, user.username)
    if query.data == "case_epic":
        case = EPIC_CASE
        open_func = open_epic_case
    elif query.data == "case_mythic":
        case = MYTHIC_CASE
        open_func = open_mythic_case
    elif query.data == "case_legendary":
        case = LEGENDARY_CASE
        open_func = open_legendary_case
    else:
        return
    if user_data.get("balance", 0) < case["price"]:
        await query.edit_message_text("❌ Недостаточно очков!")
        return
    result = open_func()
    if result is None:
        await query.edit_message_text("❌ Ошибка при открытии кейса (нет карт нужной редкости).")
        return
    if result["type"] == "points":
        points_won = result["amount"]
        user_data["balance"] = user_data["balance"] - case["price"] + points_won
        await update_user(user.id, user_data)
        await query.edit_message_text(f"🎉 Вы открыли {case['name']} и получили {points_won}🌟!\n💰 Новый баланс: {user_data['balance']}🌟")
    else:
        card = result["card"]
        is_repeated = card['id'] in user_data.get("cards", [])
        base_points = RARITY_POINTS[card['rarity']]
        points_earned = base_points // 2 if is_repeated else base_points
        if not is_repeated:
            user_data.setdefault("cards", []).append(card['id'])
        user_data["balance"] = user_data["balance"] - case["price"] + points_earned
        await update_user(user.id, user_data)
        await query.message.delete()
        await send_card_message(query.message, card, is_repeated, points_earned, user_data["balance"])

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Использование: /transfer @username card_id\nПример: /transfer @user Работа_от_@RaffoGFX_необычная.jpg")
        return
    target_username = args[0].lstrip('@')
    card_id = args[1]
    from_user = update.effective_user
    from_data = await get_user(from_user.id, from_user.username)
    if card_id not in from_data.get("cards", []):
        await update.message.reply_text("❌ У вас нет такой карты!")
        return
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM users WHERE LOWER(username) = $1", target_username.lower())
        if not row:
            await update.message.reply_text(f"❌ Пользователь @{target_username} не найден в базе!")
            return
        to_id = row['user_id']
    if to_id == from_user.id:
        await update.message.reply_text("❌ Нельзя передать карту самому себе!")
        return
    from_data["cards"].remove(card_id)
    await update_user(from_user.id, from_data)
    to_data = await get_user(to_id)
    to_data.setdefault("cards", []).append(card_id)
    await update_user(to_id, to_data)
    await update.message.reply_text(f"✅ Карта передана пользователю @{target_username}!")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка базы данных: {e}")
        return

    if not rows:
        await update.message.reply_text("📊 Пока нет данных для топа.")
        return

    text = "🏆 <b>Топ игроков по очкам:</b>\n\n"
    for i, row in enumerate(rows, 1):
        username = row.get('username')
        display_name = f"@{username}" if username else "Аноним"
        balance = row['balance']
        text += f"{i}. {display_name} — {balance}🌟\n"

    await update.message.reply_text(text, parse_mode='HTML')

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    can, remaining = await check_cooldown(user_data.get("last_bonus", 0), 24)
    if not can:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(f"⏳ <b>Бонус будет доступен через:</b> {hours}ч {minutes}мин", parse_mode='HTML')
        return
    card = get_random_card()
    if not card:
        await update.message.reply_text("❌ В колоде пока нет карт!")
        return
    is_repeated = card['id'] in user_data.get("cards", [])
    base_points = RARITY_POINTS[card['rarity']]
    points_earned = base_points // 2 if is_repeated else base_points
    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])
    user_data["balance"] = user_data.get("balance", 0) + points_earned
    user_data["last_bonus"] = int(datetime.now().timestamp())
    await update_user(user.id, user_data)
    await send_card_message(update.message, card, is_repeated, points_earned, user_data["balance"])

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Использование: /roulette сумма")
        return
    try:
        bet = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Сумма должна быть числом!")
        return
    if bet <= 0:
        await update.message.reply_text("❌ Ставка должна быть положительной!")
        return
    user = update.effective_user
    user_data = await get_user(user.id, user.username)
    if user_data.get("balance", 0) < bet:
        await update.message.reply_text("❌ У вас недостаточно очков!")
        return
    if random.random() < 0.5:
        win = bet
        user_data["balance"] += win
        result_text = f"🎉 Вы выиграли {win}🌟! Новый баланс: {user_data['balance']}🌟"
    else:
        user_data["balance"] -= bet
        result_text = f"💥 Вы проиграли {bet}🌟. Новый баланс: {user_data['balance']}🌟"
    await update_user(user.id, user_data)
    await update.message.reply_text(result_text)

# ---------- Админ-команды ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    text = (
        "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "📌 <b>Команды (можно указывать @username или числовой ID):</b>\n"
        "/add_points пользователь сумма\n"
        "/remove_points пользователь сумма\n"
        "/give_card пользователь card_id\n"
        "/reset_cooldown пользователь\n"
        "/reset_bonus пользователь\n"
        "/stats - статистика бота\n"
        "/reload_cards - перезагрузить карты"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Использование: /add_points @username или user_id сумма")
        return
    target = args[0]
    try:
        points = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Сумма должна быть числом!")
        return
    target_id, display = await resolve_target(target)
    if target_id is None:
        await update.message.reply_text(display)
        return
    user_data = await get_user(target_id)
    user_data["balance"] = user_data.get("balance", 0) + points
    await update_user(target_id, user_data)
    await update.message.reply_text(f"✅ Начислено {points} очков пользователю {display} (ID: {target_id})")

async def remove_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Использование: /remove_points @username или user_id сумма")
        return
    target = args[0]
    try:
        points = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Сумма должна быть числом!")
        return
    target_id, display = await resolve_target(target)
    if target_id is None:
        await update.message.reply_text(display)
        return
    user_data = await get_user(target_id)
    current = user_data.get("balance", 0)
    user_data["balance"] = max(0, current - points)
    await update_user(target_id, user_data)
    await update.message.reply_text(f"✅ Снято {points} очков у пользователя {display} (ID: {target_id})")

async def give_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ Использование: /give_card @username или user_id card_id")
        return
    target = args[0]
    card_id = args[1]
    target_id, display = await resolve_target(target)
    if target_id is None:
        await update.message.reply_text(display)
        return
    card = get_card_by_id(card_id)
    if not card:
        await update.message.reply_text("❌ Карта не найдена!")
        return
    user_data = await get_user(target_id)
    if card_id in user_data.get("cards", []):
        await update.message.reply_text("❌ У пользователя уже есть эта карта!")
        return
    user_data.setdefault("cards", []).append(card_id)
    await update_user(target_id, user_data)
    await update.message.reply_text(f"✅ Карта выдана пользователю {display} (ID: {target_id})")

async def reset_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Использование: /reset_cooldown @username или user_id")
        return
    target = args[0]
    target_id, display = await resolve_target(target)
    if target_id is None:
        await update.message.reply_text(display)
        return
    user_data = await get_user(target_id)
    user_data["last_card"] = 0
    await update_user(target_id, user_data)
    await update.message.reply_text(f"✅ Кулдаун сброшен для пользователя {display} (ID: {target_id})")

async def reset_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❌ Использование: /reset_bonus @username или user_id")
        return
    target = args[0]
    target_id, display = await resolve_target(target)
    if target_id is None:
        await update.message.reply_text(display)
        return
    user_data = await get_user(target_id)
    user_data["last_bonus"] = 0
    await update_user(target_id, user_data)
    await update.message.reply_text(f"✅ Бонус сброшен для пользователя {display} (ID: {target_id})")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    async with db_pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_balance = await conn.fetchval("SELECT COALESCE(SUM(balance), 0) FROM users")
    all_cards = load_cards()
    cards_in_game = len(all_cards)
    rarity_stats = {rarity: 0 for rarity in RARITY_POINTS.keys()}
    for card in all_cards:
        rarity_stats[card['rarity']] += 1
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance}🌟\n"
        f"📦 Карт в игре: {cards_in_game}\n\n"
        "<b>Распределение карт:</b>\n"
    )
    for rarity, count in rarity_stats.items():
        emoji = RARITY_EMOJI[rarity]
        percentage = (count / cards_in_game * 100) if cards_in_game else 0
        text += f"{emoji} {rarity}: {count} ({percentage:.1f}%)\n"
    await update.message.reply_text(text, parse_mode='HTML')

async def reload_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    await get_user(update.effective_user.id, update.effective_user.username)
    from cards import _cards_cache
    _cards_cache = None
    cards = load_cards()
    await update.message.reply_text(f"✅ Карты перезагружены! Загружено: {len(cards)} карт")
