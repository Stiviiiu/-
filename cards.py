import os
import re
import random
from utils import RARITY_POINTS

CARDS_FOLDER = "cards"
_cards_cache = None

# ========== НАСТРОЙКА ШАНСОВ ==========
FREE_CARD_CHANCES = {
    "необычная": 0.40,
    "редкая": 0.30,
    "эпическая": 0.15,
    "мифическая": 0.10,
    "ультра": 0.05
}

MINI_CASE_CHANCES = {
    "необычная": 0.60,
    "редкая": 0.25,
    "эпическая": 0.10,
    "мифическая": 0.04,
    "ультра": 0.01
}

SECRET_CASE_CHANCES = {
    "необычная": 0.45,
    "редкая": 0.30,
    "эпическая": 0.15,
    "мифическая": 0.07,
    "ультра": 0.03
}

MEGA_CASE_CHANCES = {
    "необычная": 0.30,
    "редкая": 0.30,
    "эпическая": 0.25,
    "мифическая": 0.10,
    "ультра": 0.05
}
# =======================================

def load_cards():
    global _cards_cache
    if _cards_cache is not None:
        return _cards_cache
    cards = []
    if not os.path.exists(CARDS_FOLDER):
        os.makedirs(CARDS_FOLDER)
        return cards

    print(f"📂 Загрузка карт из папки: {CARDS_FOLDER}")
    for filename in os.listdir(CARDS_FOLDER):
        filepath = os.path.join(CARDS_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue

        # Поддержка ников с подчёркиваниями (например @on_dsgn)
        match = re.match(r"Работа_от_@(.+)_(необычная|редкая|эпическая|мифическая|ультра)\..+", filename)
        if not match:
            print(f"⚠️ Пропущен файл (неправильное имя): {filename}")
            continue

        author = match.group(1)
        rarity = match.group(2).lower()

        if rarity not in RARITY_POINTS:
            print(f"⚠️ Пропущен файл (неизвестная редкость '{rarity}'): {filename}")
            continue

        cards.append({
            "id": filename,
            "author": author,
            "rarity": rarity,
            "file_path": filepath
        })
        print(f"✅ Загружена карта: {author} - {rarity}")

    _cards_cache = cards
    print(f"📊 Всего загружено карт: {len(cards)}")
    return cards

def get_random_card():
    cards = load_cards()
    if not cards:
        return None

    cards_by_rarity = {}
    for card in cards:
        rarity = card["rarity"]
        if rarity not in cards_by_rarity:
            cards_by_rarity[rarity] = []
        cards_by_rarity[rarity].append(card)

    available_rarities = []
    weights = []
    for rarity, chance in FREE_CARD_CHANCES.items():
        if rarity in cards_by_rarity and cards_by_rarity[rarity]:
            available_rarities.append(rarity)
            weights.append(chance)

    if not available_rarities:
        return random.choice(cards)

    total_weight = sum(weights)
    normalized_weights = [w/total_weight for w in weights]
    chosen_rarity = random.choices(available_rarities, weights=normalized_weights)[0]
    return random.choice(cards_by_rarity[chosen_rarity])

def get_mini_case_card():
    return get_case_card_by_chances(MINI_CASE_CHANCES)

def get_secret_case_card():
    return get_case_card_by_chances(SECRET_CASE_CHANCES)

def get_mega_case_card():
    return get_case_card_by_chances(MEGA_CASE_CHANCES)

def get_case_card_by_chances(chances_dict):
    cards = load_cards()
    if not cards:
        return None

    cards_by_rarity = {}
    for card in cards:
        rarity = card["rarity"]
        if rarity not in cards_by_rarity:
            cards_by_rarity[rarity] = []
        cards_by_rarity[rarity].append(card)

    available_rarities = []
    weights = []
    for rarity, chance in chances_dict.items():
        if rarity in cards_by_rarity and cards_by_rarity[rarity]:
            available_rarities.append(rarity)
            weights.append(chance)

    if not available_rarities:
        return random.choice(cards)

    total_weight = sum(weights)
    normalized_weights = [w/total_weight for w in weights]
    chosen_rarity = random.choices(available_rarities, weights=normalized_weights)[0]
    return random.choice(cards_by_rarity[chosen_rarity])

def get_card_by_id(card_id):
    cards = load_cards()
    for card in cards:
        if card["id"] == card_id:
            return card
    return None
