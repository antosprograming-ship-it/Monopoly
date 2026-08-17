from dataclasses import dataclass
import random

from board import load_board
from chance_cards import load_chance_cards
from community_chest_cards import load_community_chest_cards
from models import Field, Player


@dataclass
class GameState:
    players: list[Player]
    board: list[Field]
    bank: dict
    chance_cards: list[dict]
    community_chest_cards: list[dict]

    def notify(self, message=""):
        print(message)

    def ask_buy_decision(self, player, field):
        while True:
            want_buy = input("\nType (buy) to purchase, (not) to pass: ").strip().lower()
            if want_buy == "buy":
                return True
            if want_buy == "not":
                return False
            self.notify("Invalid input! Choose 'buy' or 'not'.")


def create_game(player_name="You", bot_count=1):
    players = [Player(name=player_name)] + [
        Player(name=f"Computer {i}", is_ai=True) for i in range(1, bot_count + 1)
    ]

    chance_cards = load_chance_cards()
    community_chest_cards = load_community_chest_cards()
    random.shuffle(chance_cards)
    random.shuffle(community_chest_cards)

    return GameState(
        players=players,
        board=load_board(),
        bank={"houses": 32, "hotels": 12},
        chance_cards=chance_cards,
        community_chest_cards=community_chest_cards,
    )
