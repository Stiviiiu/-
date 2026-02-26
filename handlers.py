import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from utils import get_user, update_user, check_cooldown, RARITY_POINTS, RARITY_EMOJI
from cards import load_cards, get_random_card, get_card_by_id, get_mini_case_card, get_secret_case_card, get_mega_case_card

async def send_card_message(message, card, is_repeated, points_earned, new_balance):
    """Отправить карточку с красивым оформлением"""
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    get_user(user.id)
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🎮 <b>Карточная игра</b>\n\n"
        "📋 <b>Команды:</b>\n"
        "🎴 /cards - получить карту (раз в час)\n"
        "💰 /balance - проверить баланс\n"
        "📚 /collection - коллекция карт\n"
        "🎁 /cases - открыть кейсы\n"
        "🔄 /transfer @user card_id - передать карту\n\n"
        "⭐ <b>Очки за редкость:</b>\n"
        "🟢 Необычная - 50 очков\n"
        "🔵 Редкая - 100 очков\n"
        "🟣 Эпическая - 200 очков\n"
        "🟡 Мифическая - 500 очков\n"
        "🔴 Ультра - 1000 очков\n\n"
        "🔄 За повторную карту даётся 50% очков"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cards"""
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Проверка кулдауна
    can, remaining = check_cooldown(user_data.get("last_card", 0))
    if not can:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(
            f"⏳ <b>Кулдаун!</b>\n"
            f"Следующая карта через: {hours}ч {minutes}мин",
            parse_mode='HTML'
        )
        return
    
    # Получаем карту с учетом шансов
    card = get_random_card()
    if not card:
        await update.message.reply_text("❌ В колоде пока нет карт!")
        return
    
    # Проверка на повтор
    is_repeated = card['id'] in user_data.get("cards", [])
    base_points = RARITY_POINTS[card['rarity']]
    points_earned = base_points // 2 if is_repeated else base_points
    
    # Обновляем данные пользователя
    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])
    
    user_data["balance"] = user_data.get("balance", 0) + points_earned
    user_data["last_card"] = time.time()
    update_user(user_id, user_data)
    
    # Отправляем карту
    await send_card_message(update.message, card, is_repeated, points_earned, user_data["balance"])

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /balance"""
    user_data = get_user(update.effective_user.id)
    cards_count = len(user_data.get("cards", []))
    
    text = (
        f"💰 <b>Ваш баланс</b>\n\n"
        f"Очки: <b>{user_data.get('balance', 0)}</b>\n"
        f"Карт в коллекции: <b>{cards_count}</b>"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает коллекцию с группировкой по авторам и ID карт для передачи"""
    user_data = get_user(update.effective_user.id)
    card_ids = user_data.get("cards", [])
    
    if not card_ids:
        await update.message.reply_text("📭 У вас пока нет карт в коллекции!")
        return
    
    from cards import load_cards
    all_cards = load_cards()
    
    # Группируем карты по редкости, затем по автору
    rarity_author_cards = {rarity: {} for rarity in RARITY_POINTS.keys()}
    
    for card_id in card_ids:
        card = next((c for c in all_cards if c['id'] == card_id), None)
        if card:
            rarity = card['rarity']
            author = card['author']
            if author not in rarity_author_cards[rarity]:
                rarity_author_cards[rarity][author] = []
            rarity_author_cards[rarity][author].append(card)
    
    total_cards = len(card_ids)
    text = f"📚 <b>Ваша коллекция (ID для передачи):</b> всего карт: {total_cards}\n\n"
    
    for rarity, authors in rarity_author_cards.items():
        if authors:
            emoji = RARITY_EMOJI[rarity]
            # Считаем общее количество карт этой редкости
            rarity_total = sum(len(cards) for cards in authors.values())
            text += f"{emoji} <b>{rarity.upper()}</b> ({rarity_total} шт.)\n"
            
            for author, cards in authors.items():
                count = len(cards)
                # Склонение слова "карт" (можно упростить до "шт.")
                text += f"  • @{author} ({count} шт.):\n"
                for card in cards:
                    text += f"      <code>{card['id']}</code>\n"
            text += "\n"
    
    # Ограничение длины сообщения Telegram (4096 символов)
    if len(text) > 4000:
        text = text[:4000] + "...\n(слишком много карт, показаны не все)"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def cases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cases"""
    keyboard = [
        [InlineKeyboardButton("📦 МИНИ-КЕЙС (2000🌟)", callback_data="case_mini")],
        [InlineKeyboardButton("📦 ТАЙНО-КЕЙС (5000🌟)", callback_data="case_secret")],
        [InlineKeyboardButton("📦 МЕГА-КЕЙС (10000🌟)", callback_data="case_mega")],
        [InlineKeyboardButton("❌ ОТМЕНА", callback_data="case_cancel")]
    ]
    
    text = (
        "🎁 <b>МАГАЗИН КЕЙСОВ</b>\n\n"
        "📦 <b>Мини-кейс (2000🌟)</b>\n"
        "🟢 Необычная: 60%\n"
        "🔵 Редкая: 25%\n"
        "🟣 Эпическая: 10%\n"
        "🟡 Мифическая: 4%\n"
        "🔴 Ультра: 1%\n\n"
        "📦 <b>Тайно-кейс (5000🌟)</b>\n"
        "🟢 Необычная: 45%\n"
        "🔵 Редкая: 30%\n"
        "🟣 Эпическая: 15%\n"
        "🟡 Мифическая: 7%\n"
        "🔴 Ультра: 3%\n\n"
        "📦 <b>Мега-кейс (10000🌟)</b>\n"
        "🟢 Необычная: 30%\n"
        "🔵 Редкая: 30%\n"
        "🟣 Эпическая: 25%\n"
        "🟡 Мифическая: 10%\n"
        "🔴 Ультра: 5%"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки кейсов"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "case_cancel":
        await query.edit_message_text("❌ Покупка отменена")
        return
    
    user_id = query.from_user.id
    user_data = get_user(user_id)
    
    # Цены кейсов
    case_prices = {
        "case_mini": 2000,
        "case_secret": 5000,
        "case_mega": 10000
    }
    
    price = case_prices.get(query.data, 0)
    if user_data.get("balance", 0) < price:
        await query.edit_message_text("❌ Недостаточно очков!")
        return
    
    # Получаем карту из кейса
    if query.data == "case_mini":
        card = get_mini_case_card()
        case_name = "Мини-кейс"
    elif query.data == "case_secret":
        card = get_secret_case_card()
        case_name = "Тайно-кейс"
    else:
        card = get_mega_case_card()
        case_name = "Мега-кейс"
    
    if not card:
        await query.edit_message_text("❌ В кейсе пока нет карт!")
        return
    
    # Проверка на повтор
    is_repeated = card['id'] in user_data.get("cards", [])
    base_points = RARITY_POINTS[card['rarity']]
    points_earned = base_points // 2 if is_repeated else base_points
    
    # Обновляем данные
    if not is_repeated:
        user_data.setdefault("cards", []).append(card['id'])
    
    user_data["balance"] = user_data["balance"] - price + points_earned
    update_user(user_id, user_data)
    
    # Удаляем сообщение с кнопками
    await query.message.delete()
    
    # Отправляем карту
    await send_card_message(query.message, card, is_repeated, points_earned, user_data["balance"])

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /transfer"""
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ Использование: /transfer @username card_id\n"
            "Пример: /transfer @user Работа_от_@RaffoGFX_необычная.jpg"
        )
        return
    
    target_username = args[0].lstrip('@')
    card_id = args[1]
    from_id = update.effective_user.id
    from_data = get_user(from_id)
    
    # Проверяем наличие карты
    if card_id not in from_data.get("cards", []):
        await update.message.reply_text("❌ У вас нет такой карты!")
        return
    
    # Ищем получателя
    from utils import load_users
    users = load_users()
    to_id = None
    
    for uid, data in users.items():
        if data.get("username", "").lower() == target_username.lower():
            to_id = int(uid)
            break
    
    if not to_id:
        await update.message.reply_text(f"❌ Пользователь @{target_username} не найден!")
        return
    
    if to_id == from_id:
        await update.message.reply_text("❌ Нельзя передать карту самому себе!")
        return
    
    # Передаем карту
    from_data["cards"].remove(card_id)
    update_user(from_id, from_data)
    
    to_data = get_user(to_id)
    to_data.setdefault("cards", []).append(card_id)
    update_user(to_id, to_data)
    
    await update.message.reply_text(f"✅ Карта передана пользователю @{target_username}!")

# ========== АДМИН-ПАНЕЛЬ ==========

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    text = (
        "👑 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "📌 <b>Команды:</b>\n"
        "/add_points user_id сумма - начислить очки\n"
        "/remove_points user_id сумма - снять очки\n"
        "/give_card user_id card_id - выдать карту\n"
        "/reset_cooldown user_id - сбросить кулдаун\n"
        "/stats - статистика бота\n"
        "/reload_cards - перезагрузить карты"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начислить очки"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
    except:
        await update.message.reply_text("❌ Использование: /add_points user_id сумма")
        return
    
    user_data = get_user(user_id)
    user_data["balance"] = user_data.get("balance", 0) + points
    update_user(user_id, user_data)
    
    await update.message.reply_text(f"✅ Начислено {points} очков пользователю {user_id}")

async def remove_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снять очки"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
    except:
        await update.message.reply_text("❌ Использование: /remove_points user_id сумма")
        return
    
    user_data = get_user(user_id)
    current = user_data.get("balance", 0)
    user_data["balance"] = max(0, current - points)
    update_user(user_id, user_data)
    
    await update.message.reply_text(f"✅ Снято {points} очков у пользователя {user_id}")

async def give_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдать карту"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    try:
        user_id = int(context.args[0])
        card_id = context.args[1]
    except:
        await update.message.reply_text("❌ Использование: /give_card user_id card_id")
        return
    
    card = get_card_by_id(card_id)
    if not card:
        await update.message.reply_text("❌ Карта не найдена!")
        return
    
    user_data = get_user(user_id)
    if card_id in user_data.get("cards", []):
        await update.message.reply_text("❌ У пользователя уже есть эта карта!")
        return
    
    user_data.setdefault("cards", []).append(card_id)
    update_user(user_id, user_data)
    
    await update.message.reply_text(f"✅ Карта выдана пользователю {user_id}")

async def reset_cooldown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить кулдаун"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    try:
        user_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Использование: /reset_cooldown user_id")
        return
    
    user_data = get_user(user_id)
    user_data["last_card"] = 0
    update_user(user_id, user_data)
    
    await update.message.reply_text(f"✅ Кулдаун сброшен для пользователя {user_id}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика бота"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    from utils import load_users
    users = load_users()
    all_cards = load_cards()
    
    total_users = len(users)
    total_balance = sum(u.get("balance", 0) for u in users.values())
    total_cards = sum(len(u.get("cards", [])) for u in users.values())
    cards_in_game = len(all_cards)
    
    # Статистика по редкостям
    rarity_stats = {rarity: 0 for rarity in RARITY_POINTS.keys()}
    for card in all_cards:
        rarity_stats[card['rarity']] += 1
    
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance}🌟\n"
        f"🃏 Всего карт у игроков: {total_cards}\n"
        f"📦 Карт в игре: {cards_in_game}\n\n"
        "<b>Распределение карт:</b>\n"
    )
    
    for rarity, count in rarity_stats.items():
        emoji = RARITY_EMOJI[rarity]
        percentage = (count / cards_in_game * 100) if cards_in_game else 0
        text += f"{emoji} {rarity}: {count} ({percentage:.1f}%)\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def reload_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезагрузить карты"""
    if update.effective_user.id not in config.ADMIN_IDS:
        return
    
    from cards import _cards_cache
    _cards_cache = None
    cards = load_cards()
    
    await update.message.reply_text(f"✅ Карты перезагружены! Загружено: {len(cards)} карт")
