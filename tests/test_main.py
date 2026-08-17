import engine
import main
from game_state import create_game
from models import Player


def test_play_eliminates_bankrupt_player_and_ends_two_player_game(game, p1, p2, bank, monkeypatch):
    p1.position_index = 2
    p1.budget = 100
    active_players = [p1, p2]
    monkeypatch.setattr(engine, "roll_dice", lambda: (1, 1))

    next_player = main.play(game, p1, active_players)

    assert active_players == [p2]
    assert next_player is p2
    assert p1.budget == 0
    assert p1.is_in_debt is False


def test_jail_bankruptcy_passes_active_players_to_debt_handler(
    game, p1, p2, monkeypatch
):
    p2.in_jail = True
    p2.jail_turns = 2
    p2.budget = 0
    p2.position_index = 10
    active_players = [p1, p2]
    monkeypatch.setattr(engine, "roll_dice", lambda: (1, 2))

    result = main.handle_jail_turn(game, p2, active_players)

    assert result == "BANKRUPT"
    assert active_players == [p1]


def test_cascading_bankruptcy_eliminates_creditor_too(game, p1, p2, find_field):
    # Regresja: wierzyciel, który dziedziczy zastawioną nieruchomość, może
    # sam zbankrutować. declare_bankruptcy(p1) celowo nie przekazuje wyniku
    # zagnieżdżonego handle_debt_menu(p2) dalej — ta kaskada musi więc być
    # widoczna w samej liście active_players, nie w zwracanej wartości.
    p3 = Player(name="Third")
    game.players.append(p3)
    active_players = game.players

    konopacka = find_field("ulica_konopacka")  # price 60 -> mortgage 30, 10% tax = 3
    konopacka.owner = p1
    konopacka.is_mortgaged = True
    p1.properties = [konopacka]
    p1.budget = -10
    p1.is_in_debt = True
    p1.creditor = p2

    p2.is_ai = True  # unika promptu 'y/n' o natychmiastowe zdjęcie hipoteki
    p2.budget = 2  # po zapłaceniu 10% podatku ($3) schodzi na -1, bez majątku na pokrycie

    result = main.declare_bankruptcy(game, p1, active_players)

    assert result == "BANKRUPT"
    assert active_players == [p3]
    assert p2.budget == 0
    assert p2.is_in_debt is False
    assert p2.properties == []
    assert konopacka.owner is None
    assert konopacka.is_mortgaged is False


def test_prompt_for_nickname_rejects_blank_input(monkeypatch):
    inputs = iter(["", "   ", "Ala"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    assert main.prompt_for_nickname() == "Ala"


def test_prompt_for_bot_count_validates_range_and_digits(monkeypatch):
    inputs = iter(["0", "6", "abc", "3"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    assert main.prompt_for_bot_count() == 3


def test_find_player_by_name_is_case_insensitive(game, p1):
    p1.name = "Ala"

    assert main.find_player_by_name(game, "ala") is p1
    assert main.find_player_by_name(game, "ALA") is p1
    assert main.find_player_by_name(game, "nobody") is None


def test_restart_creates_a_fresh_complete_deck_with_no_held_cards():
    held_game = create_game()
    jail_card_index = next(
        index
        for index, card in enumerate(held_game.chance_cards)
        if card["action_type"] == "keep_jail_card"
    )
    jail_card = held_game.chance_cards.pop(jail_card_index)
    engine.handle_card_keep_jail_card(
        held_game, held_game.players[0], jail_card, held_game.chance_cards
    )

    restarted_game = create_game()

    assert sorted(card["id"] for card in restarted_game.chance_cards) == sorted(
        card["id"] for card in held_game.chance_cards + [jail_card]
    )
    assert restarted_game.players[0].jail_cards_count == 0
    assert restarted_game.players[0].jail_cards_held == []
