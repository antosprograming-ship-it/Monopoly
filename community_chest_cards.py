import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "community_chest_cards.json", "r", encoding="utf-8") as file:
    community_chest_cards = json.load(file)

random.shuffle(community_chest_cards)
