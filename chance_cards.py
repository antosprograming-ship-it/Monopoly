import json
from pathlib import Path

BASE_DIR = Path(__file__).parent


def load_chance_cards():
    with open(BASE_DIR / "chance_cards.json", "r", encoding="utf-8") as file:
        return json.load(file)
