import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "board.json", "r", encoding="utf-8") as file:
    board = json.load(file)
