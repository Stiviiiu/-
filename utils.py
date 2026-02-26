import json
import os
import time

DATA_FILE = "data/users.json"

def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def get_user(user_id, username=None):
    """
    Получить данные пользователя по user_id.
    Если передан username, обновляет его в базе (при изменении).
    """
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        # Новый пользователь
        users[uid] = {
            "username": username or "",
            "balance": 0,
            "last_card": 0,
            "cards": []
        }
        save_users(users)
    else:
        # Обновляем username, если он изменился
        if username is not None and users[uid].get("username") != username:
            users[uid]["username"] = username
            save_users(users)
    return users[uid]

def update_user(user_id, data):
    users = load_users()
    uid = str(user_id)
    users[uid] = data
    save_users(users)

def check_cooldown(last_time, cooldown_hours=1):
    if last_time == 0:
        return True, 0
    elapsed = time.time() - last_time
    cooldown_sec = cooldown_hours * 3600
    if elapsed >= cooldown_sec:
        return True, 0
    remaining = cooldown_sec - elapsed
    return False, int(remaining)

# Очки за редкость
RARITY_POINTS = {
    "необычная": 50,
    "редкая": 100,
    "эпическая": 200,
    "мифическая": 500,
    "ультра": 1000
}

# Эмодзи для редкостей
RARITY_EMOJI = {
    "необычная": "🟢",
    "редкая": "🔵",
    "эпическая": "🟣",
    "мифическая": "🟡",
    "ультра": "🔴"
}
