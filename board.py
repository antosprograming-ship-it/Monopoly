import json
from pathlib import Path

from models import Field

BASE_DIR = Path(__file__).parent


def load_board():
    with open(BASE_DIR / "board.json", encoding="utf-8") as file:
        raw_fields = json.load(file)
    return [Field(**data) for data in raw_fields]
