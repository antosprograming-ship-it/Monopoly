import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "chance_cards.json", "r", encoding="utf-8") as file:
    chance_cards = json.load(file)

random.shuffle(chance_cards)
