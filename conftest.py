import pytest

from game_state import create_game


@pytest.fixture
def game():
    return create_game()


@pytest.fixture
def p1(game):
    return game.players[0]


@pytest.fixture
def p2(game):
    return game.players[1]


@pytest.fixture
def bank(game):
    return game.bank


@pytest.fixture
def find_field(game):
    def _find(field_id):
        return next(f for f in game.board if f.id == field_id)

    return _find
