import pytest

import engine
import models
from board import board


def find_field_by_id(field_id):
    return next(f for f in board if f.get("id") == field_id)


@pytest.fixture(autouse=True)
def reset_state():
    """Every test starts from a clean board/player state and leaves one behind."""
    engine.reset_game(models.player1, models.player2, models.bank)
    yield
    engine.reset_game(models.player1, models.player2, models.bank)


@pytest.fixture
def p1():
    return models.player1


@pytest.fixture
def p2():
    return models.player2


@pytest.fixture
def bank():
    return models.bank


@pytest.fixture
def find_field():
    return find_field_by_id
