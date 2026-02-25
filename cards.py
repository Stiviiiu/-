import os
import re
import random
from utils import RARITY_POINTS

CARDS_FOLDER = "cards"
_cards_cache = None

def load_cards():
    global _cards_cache
    if _cards_cache is not None:
        return _cards_cache
    cards = []
    if not os.path.exists(CARDS_FOLDER):
        os.makedirs(CARDS_FOLDER)
        return cards
    for filename in os.listdir(CARDS_FOLDER):
        filepath = os.path.join(CARDS_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue
        match = re.match(r"Работа_от_@(.+)_(.+)\..+", filename)
        if not match:
            continue
        author = match.group(1)
        rarity = match.group(2).lower()
        if rarity not in RARITY_POINTS:
            continue
        cards.append({
            "id": filename,
            "author": author,
            "rarity": rarity,
            "file_path": filepath
        })
    _cards_cache = cards
    return cards

def get_random_card():
    cards = load_cards()
    return random.choice(cards) if cards else None

def get_card_by_id(card_id):
    cards = load_cards()
    for card in cards:
        if card["id"] == card_id:
            return card
    return None

def get_random_card_by_rarity(rarity):
    cards = [c for c in load_cards() if c["rarity"] == rarity]
    return random.choice(cards) if cards else None
