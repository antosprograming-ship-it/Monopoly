import json
import random

with open("community_chest_cards.json", "r", encoding="utf-8") as file:
    community_chest_cards = json.load(file)

random.shuffle(community_chest_cards)
