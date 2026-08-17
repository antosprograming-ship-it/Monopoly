import engine
import main
from chance_cards import chance_cards


def test_play_eliminates_bankrupt_player_and_ends_two_player_game(p1, p2, bank, monkeypatch):
    p1["position_index"] = 2
    p1["budget"] = 100
    active_players = [p1, p2]
    monkeypatch.setattr(engine, "roll_dice", lambda: (1, 1))

    next_player = main.play(p1, active_players)

    assert active_players == [p2]
    assert next_player is p2
    assert p1["budget"] == 0
    assert p1["is_in_debt"] is False


def test_jail_bankruptcy_passes_active_players_to_debt_handler(
    p1, p2, monkeypatch
):
    p2.update(
        {
            "in_jail": True,
            "jail_turns": 2,
            "budget": 0,
            "position_index": 10,
        }
    )
    active_players = [p1, p2]
    monkeypatch.setattr(engine, "roll_dice", lambda: (1, 2))

    result = main.handle_jail_turn(p2, active_players)

    assert result == "BANKRUPT"
    assert active_players == [p1]


def test_restart_restores_a_get_out_of_jail_free_card_to_its_deck(p1, p2, bank):
    initial_ids = [card["id"] for card in chance_cards]
    jail_card_index = next(
        index
        for index, card in enumerate(chance_cards)
        if card["action_type"] == "keep_jail_card"
    )
    jail_card = chance_cards.pop(jail_card_index)
    engine.handle_card_keep_jail_card(p1, jail_card, chance_cards)

    engine.reset_game(p1, p2, bank)

    assert sorted(card["id"] for card in chance_cards) == sorted(initial_ids)
    assert p1["jail_cards_count"] == 0
    assert p1["jail_cards_held"] == []

