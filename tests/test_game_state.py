from game_state import create_game


def test_create_game_defaults_to_one_bot():
    game = create_game()

    assert len(game.players) == 2
    assert game.players[0].name == "You"
    assert game.players[0].is_ai is False
    assert game.players[1].is_ai is True


def test_create_game_uses_given_nickname_and_bot_count():
    game = create_game(player_name="Ala", bot_count=3)

    assert len(game.players) == 4
    assert game.players[0].name == "Ala"
    assert game.players[0].is_ai is False

    bots = game.players[1:]
    assert len(bots) == 3
    assert all(bot.is_ai for bot in bots)
    assert len({bot.name for bot in bots}) == 3  # unikalne nazwy botów
