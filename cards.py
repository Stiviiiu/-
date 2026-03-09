import os
import re
import random
from typing import List, Dict, Optional

CARDS_FOLDER = "cards"
_cards_cache = None

# Веса для бесплатной карты
FREE_CARD_WEIGHTS = {
    "необычная": 50,
    "редкая": 40,
    "эпическая": 25,
    "мифическая": 16,
    "ультра": 6
}

# Кейсы
EPIC_CASE = {
    "name": "Эпический кейс",
    "price": 1000,
    "items": [
        {"type": "card", "rarity": "необычная", "weight": 50},
        {"type": "card", "rarity": "редкая", "weight": 40},
        {"type": "card", "rarity": "эпическая", "weight": 25},
        {"type": "card", "rarity": "мифическая", "weight": 18},
        {"type": "card", "rarity": "ультра", "weight": 5},
        {"type": "points", "amount": 1000, "weight": 15},
        {"type": "points", "amount": 7000, "weight": 10},
        {"type": "points", "amount": 15000, "weight": 3},
    ]
}

MYTHIC_CASE = {
    "name": "Мифический кейс",
    "price": 2000,
    "items": [
        {"type": "card", "rarity": "эпическая", "weight": 30},
        {"type": "card", "rarity": "мифическая", "weight": 20},
        {"type": "card", "rarity": "ультра", "weight": 7},
        {"type": "points", "amount": 3000, "weight": 15},
    ]
}

LEGENDARY_CASE = {
    "name": "Легендарный кейс",
    "price": 5000,
    "items": [
        {"type": "card", "rarity": "мифическая", "weight": 30},
        {"type": "card", "rarity": "ультра", "weight": 9},
        {"type": "points", "amount": 25000, "weight": 2},
        {"type": "points", "amount": 5000, "weight": 10},
        {"type": "points", "amount": 1000, "weight": 25},
    ]
}

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
        match = re.match(r"Работа_от_@(.+)_(необычная|редкая|эпическая|мифическая|ультра)\..+", filename)
        if not match:
            print(f"⚠️ Пропущен файл (неправильное имя): {filename}")
            continue
        author = match.group(1)
        rarity = match.group(2).lower()
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
        cards_by_rarity.setdefault(card["rarity"], []).append(card)

    available = []
    weights = []
    for rarity, w in FREE_CARD_WEIGHTS.items():
        if rarity in cards_by_rarity and cards_by_rarity[rarity]:
            available.append(rarity)
            weights.append(w)
    if not available:
        return random.choice(cards)

    total = sum(weights)
    probs = [w/total for w in weights]
    chosen_rarity = random.choices(available, weights=probs)[0]
    return random.choice(cards_by_rarity[chosen_rarity])

def get_case_result(case_config: dict) -> dict:
    items = case_config["items"]
    weights = [item["weight"] for item in items]
    total = sum(weights)
    probs = [w/total for w in weights]
    chosen = random.choices(items, weights=probs)[0]
    if chosen["type"] == "card":
        cards = load_cards()
        cards_of_rarity = [c for c in cards if c["rarity"] == chosen["rarity"]]
        if not cards_of_rarity:
            return None
        return {"type": "card", "card": random.choice(cards_of_rarity)}
    else:
        return {"type": "points", "amount": chosen["amount"]}

def open_epic_case():
    return get_case_result(EPIC_CASE)

def open_mythic_case():
    return get_case_result(MYTHIC_CASE)

def open_legendary_case():
    return get_case_result(LEGENDARY_CASE)

def get_card_by_id(card_id):
    cards = load_cards()
    for card in cards:
        if card["id"] == card_id:
            return card
    return None
