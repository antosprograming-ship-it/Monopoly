import json
from pathlib import Path

BASE_DIR = Path(__file__).parent


def load_community_chest_cards():
    with open(BASE_DIR / "community_chest_cards.json", "r", encoding="utf-8") as file:
        return json.load(file)
