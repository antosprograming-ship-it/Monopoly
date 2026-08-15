import json
import random

with open("chance_cards.json", "r", encoding="utf-8") as file:
    chance_cards = json.load(file)

random.shuffle(chance_cards)
