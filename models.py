from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(eq=False)
class Field:
    index: int
    id: str
    type: str
    name: str
    price: int | None = None
    group: str | None = None
    base_rent: int | None = None
    house_cost: int | None = None
    house_rents: list[int] | None = None
    rent_levels: list[int] | None = None
    tax: int | None = None
    houses: int = 0
    is_mortgaged: bool = False
    owner: Player | None = None


@dataclass(eq=False)
class Player:
    name: str
    is_ai: bool = False
    position_index: int = 0
    budget: int = 1500
    properties: list[Field] = field(default_factory=list)
    jail_cards_count: int = 0
    jail_cards_held: list[dict] = field(default_factory=list)
    in_jail: bool = False
    jail_turns: int = 0
    double_count: int = 0
    is_in_debt: bool = False
    creditor: Player | None = None

    def pay(self, game, amount, creditor):
        self.budget -= amount
        self.flag_debt(game, creditor)

    def receive(self, game, amount):
        self.budget += amount
        self.flag_debt(game, self.creditor)

    def flag_debt(self, game, creditor):
        # Odświeża is_in_debt/creditor na podstawie aktualnego budżetu.
        # Wspólne dla pay()/receive() i engine.check_and_flag_debt(), więc
        # żadne miejsce poruszające budżetem nie musi pamiętać o wywołaniu
        # tego osobno.
        if self.budget < 0:
            self.is_in_debt = True
            self.creditor = creditor
            debt_amount = abs(self.budget)
            creditor_name = creditor.name if creditor else "Bank"
            game.notify(
                f"⚠️ DEBT DETECTED! {self.name} is in debt: -${debt_amount} | Owed to: {creditor_name}"
            )
        else:
            self.is_in_debt = False
            self.creditor = None
