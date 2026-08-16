import pytest

import engine


# ============================================================
# Zakup nieruchomości
# ============================================================
class TestPurchase:
    def test_computer_buys_and_clears_stale_mortgage_flag(self, p2, find_field):
        field = find_field("ulica_konopacka")
        field["is_mortgaged"] = True  # symulacja "wiszącej" flagi sprzed restartu

        engine.attempt_purchase(p2, field)

        assert field["owner"] is p2
        assert field["is_mortgaged"] is False
        assert field in p2["properties"]
        assert p2["budget"] == 1500 - field["price"]

    def test_computer_skips_purchase_without_enough_budget(self, p2, find_field):
        field = find_field("ulica_konopacka")
        p2["budget"] = 10  # < price (60)

        engine.attempt_purchase(p2, field)

        assert field["owner"] is None
        assert p2["budget"] == 10


# ============================================================
# Czynsz za ulice
# ============================================================
class TestPropertyRent:
    def test_own_field_no_charge(self, p1, find_field):
        field = find_field("ulica_konopacka")
        field["owner"] = p1

        engine.handle_property(p1, field)

        assert p1["budget"] == 1500

    def test_base_rent_without_monopoly(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        p1["properties"] = [konopacka]  # brak Stalowej -> brak monopolu

        engine.handle_property(p2, konopacka)

        assert p2["budget"] == 1500 - konopacka["base_rent"]
        assert p1["budget"] == 1500 + konopacka["base_rent"]

    def test_rent_doubled_with_full_monopoly(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        stalowa = find_field("ulica_stalowa")
        konopacka["owner"] = p1
        stalowa["owner"] = p1
        p1["properties"] = [konopacka, stalowa]

        engine.handle_property(p2, stalowa)

        assert p2["budget"] == 1500 - stalowa["base_rent"] * 2
        assert p1["budget"] == 1500 + stalowa["base_rent"] * 2

    def test_rent_still_doubled_when_sibling_is_mortgaged(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        stalowa = find_field("ulica_stalowa")
        konopacka["owner"] = p1
        stalowa["owner"] = p1
        p1["properties"] = [konopacka, stalowa]
        konopacka["is_mortgaged"] = True  # mortgage nie odbiera własności

        engine.handle_property(p2, stalowa)

        assert p2["budget"] == 1500 - stalowa["base_rent"] * 2

    def test_rent_uses_house_rents_table(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["houses"] = 2
        p1["properties"] = [konopacka]

        engine.handle_property(p2, konopacka)

        expected = konopacka["house_rents"][1]
        assert p2["budget"] == 1500 - expected

    def test_no_rent_when_property_is_mortgaged(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True
        p1["properties"] = [konopacka]

        engine.handle_property(p2, konopacka)

        assert p2["budget"] == 1500
        assert p1["budget"] == 1500


# ============================================================
# Czynsz za dworce
# ============================================================
class TestStationRent:
    def test_own_station_no_charge(self, p1, find_field):
        station = find_field("dworzec_zachodni")
        station["owner"] = p1

        engine.handle_station(p1, station)

        assert p1["budget"] == 1500

    @pytest.mark.parametrize("count", [1, 2, 3, 4])
    def test_rent_scales_with_owned_count(self, p1, p2, find_field, count):
        all_stations = [
            find_field("dworzec_zachodni"),
            find_field("dworzec_gdanski"),
            find_field("dworzec_wschodni"),
            find_field("dworzec_centralny"),
        ]
        owned = all_stations[:count]
        for s in owned:
            s["owner"] = p1
        p1["properties"] = owned

        engine.handle_station(p2, owned[-1])

        expected = owned[-1]["rent_levels"][count - 1]
        assert p2["budget"] == 1500 - expected
        assert p1["budget"] == 1500 + expected

    def test_mortgaged_station_still_counts_toward_rent(self, p1, p2, find_field):
        all_stations = [
            find_field("dworzec_zachodni"),
            find_field("dworzec_gdanski"),
            find_field("dworzec_wschodni"),
            find_field("dworzec_centralny"),
        ]
        for s in all_stations:
            s["owner"] = p1
        p1["properties"] = all_stations
        all_stations[0]["is_mortgaged"] = True  # zastawiamy jeden z czterech

        engine.handle_station(p2, all_stations[1])  # ląduje na niezastawionym

        assert p2["budget"] == 1500 - 200  # nadal stawka za 4 dworce

    def test_no_rent_when_station_is_mortgaged(self, p1, p2, find_field):
        station = find_field("dworzec_zachodni")
        station["owner"] = p1
        station["is_mortgaged"] = True
        p1["properties"] = [station]

        engine.handle_station(p2, station)

        assert p2["budget"] == 1500

    def test_card_multiplier_is_applied(self, p1, p2, find_field):
        station = find_field("dworzec_zachodni")
        station["owner"] = p1
        p1["properties"] = [station]

        engine.handle_station(p2, station, multiplier=3)

        assert p2["budget"] == 1500 - station["rent_levels"][0] * 3


# ============================================================
# Czynsz za firmy
# ============================================================
class TestCompanyRent:
    def test_own_company_no_charge(self, p1, find_field):
        company = find_field("elektrownia")
        company["owner"] = p1

        engine.handle_company(p1, company, dice_total=6)

        assert p1["budget"] == 1500

    @pytest.mark.parametrize("count,rate", [(1, 4), (2, 10)])
    def test_rent_scales_with_owned_count(self, p1, p2, find_field, count, rate):
        companies = [find_field("elektrownia"), find_field("wodociagi")]
        owned = companies[:count]
        for c in owned:
            c["owner"] = p1
        p1["properties"] = owned

        engine.handle_company(p2, owned[-1], dice_total=6)

        assert p2["budget"] == 1500 - 6 * rate

    def test_mortgaged_company_still_counts_toward_rent(self, p1, p2, find_field):
        companies = [find_field("elektrownia"), find_field("wodociagi")]
        for c in companies:
            c["owner"] = p1
        p1["properties"] = companies
        companies[0]["is_mortgaged"] = True

        engine.handle_company(p2, companies[1], dice_total=6)

        assert p2["budget"] == 1500 - 6 * 10  # nadal stawka za 2 firmy

    def test_no_rent_when_company_is_mortgaged(self, p1, p2, find_field):
        company = find_field("elektrownia")
        company["owner"] = p1
        company["is_mortgaged"] = True
        p1["properties"] = [company]

        engine.handle_company(p2, company, dice_total=6)

        assert p2["budget"] == 1500

    def test_custom_multiplier_overrides_owned_count(self, p1, p2, find_field):
        company = find_field("elektrownia")
        company["owner"] = p1
        p1["properties"] = [company]

        engine.handle_company(p2, company, dice_total=5, custom_multiplier=7)

        assert p2["budget"] == 1500 - 5 * 7


# ============================================================
# Pomocnicze funkcje monopolu / grupy
# ============================================================
class TestMonopolyHelpers:
    def test_has_monopoly_true_with_full_group(self, p1, find_field):
        p1["properties"] = [find_field("ulica_konopacka"), find_field("ulica_stalowa")]
        assert engine.has_monopoly(p1, "brown") is True

    def test_has_monopoly_false_with_partial_group(self, p1, find_field):
        p1["properties"] = [find_field("ulica_konopacka")]
        assert engine.has_monopoly(p1, "brown") is False

    def test_has_monopoly_false_for_unknown_group(self, p1):
        assert engine.has_monopoly(p1, "not_a_real_group") is False

    def test_get_player_monopolies_returns_only_complete_groups(self, p1, find_field):
        p1["properties"] = [
            find_field("ulica_konopacka"),
            find_field("ulica_stalowa"),
            find_field("ulica_radzyminska"),  # tylko 1 z 3 light_blue
        ]
        assert engine.get_player_monopolies(p1) == ["brown"]

    def test_get_group_properties_returns_all_group_members(self):
        names = {f["name"] for f in engine.get_group_properties("brown")}
        assert names == {"Ulica Konopacka", "Ulica Stalowa"}

    def test_group_has_houses(self, find_field):
        find_field("ulica_stalowa")["houses"] = 2
        assert engine.group_has_houses("brown") is True
        assert engine.group_has_houses("light_blue") is False

    def test_group_has_mortgaged_property(self, find_field):
        find_field("ulica_konopacka")["is_mortgaged"] = True
        assert engine.group_has_mortgaged_property("brown") is True
        assert engine.group_has_mortgaged_property("light_blue") is False


# ============================================================
# Budowa domków / hoteli
# ============================================================
class TestBuildHouse:
    def _own_full_brown(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        stalowa = find_field("ulica_stalowa")
        konopacka["owner"] = p1
        stalowa["owner"] = p1
        p1["properties"] = [konopacka, stalowa]
        return konopacka, stalowa

    def test_requires_monopoly(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        p1["properties"] = [konopacka]  # brak Stalowej

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 0
        assert p1["budget"] == 1500

    def test_blocked_when_group_has_mortgaged_property(self, p1, bank, find_field):
        konopacka, stalowa = self._own_full_brown(p1, find_field)
        konopacka["is_mortgaged"] = True

        engine.build_house(p1, stalowa, bank)

        assert stalowa["houses"] == 0
        assert p1["budget"] == 1500

    def test_first_house_is_built(self, p1, bank, find_field):
        konopacka, _ = self._own_full_brown(p1, find_field)

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 1
        assert p1["budget"] == 1500 - konopacka["house_cost"]
        assert bank["houses"] == 32 - 1

    def test_even_building_rule_blocks_ahead_of_group(self, p1, bank, find_field):
        konopacka, stalowa = self._own_full_brown(p1, find_field)
        konopacka["houses"] = 1  # Stalowa wciąż na 0

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 1  # zablokowane, bez zmian
        assert p1["budget"] == 1500

    def test_hotel_conversion_uses_bank_stock(self, p1, bank, find_field):
        konopacka, stalowa = self._own_full_brown(p1, find_field)
        konopacka["houses"] = 4
        stalowa["houses"] = 4

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 5
        assert p1["budget"] == 1500 - konopacka["house_cost"]
        assert bank["hotels"] == 12 - 1
        assert bank["houses"] == 32 + 4  # 4 domki wracają do banku

    def test_blocked_when_bank_out_of_houses(self, p1, bank, find_field):
        konopacka, _ = self._own_full_brown(p1, find_field)
        bank["houses"] = 0

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 0
        assert p1["budget"] == 1500

    def test_blocked_when_bank_out_of_hotels(self, p1, bank, find_field):
        konopacka, stalowa = self._own_full_brown(p1, find_field)
        konopacka["houses"] = 4
        stalowa["houses"] = 4
        bank["hotels"] = 0

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 4
        assert bank["houses"] == 32

    def test_blocked_when_budget_too_low(self, p1, bank, find_field):
        konopacka, _ = self._own_full_brown(p1, find_field)
        p1["budget"] = 10

        engine.build_house(p1, konopacka, bank)

        assert konopacka["houses"] == 0
        assert p1["budget"] == 10


# ============================================================
# Sprzedaż domków / hoteli
# ============================================================
class TestSellHouse:
    def test_nothing_to_sell(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")

        engine.sell_house(p1, konopacka, bank)

        assert p1["budget"] == 1500

    def test_even_selling_rule_blocks_below_group_max(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        stalowa = find_field("ulica_stalowa")
        konopacka["houses"] = 2
        stalowa["houses"] = 1

        engine.sell_house(p1, stalowa, bank)

        assert stalowa["houses"] == 1  # zablokowane
        assert p1["budget"] == 1500

    def test_sells_from_max_house_property(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        find_field("ulica_stalowa")["houses"] = 1
        konopacka["houses"] = 2

        engine.sell_house(p1, konopacka, bank)

        assert konopacka["houses"] == 1
        assert p1["budget"] == 1500 + konopacka["house_cost"] // 2
        assert bank["houses"] == 32 + 1

    def test_hotel_downgrade_requires_four_bank_houses(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["houses"] = 5
        bank["houses"] = 3  # < 4

        engine.sell_house(p1, konopacka, bank)

        assert konopacka["houses"] == 5
        assert p1["budget"] == 1500

    def test_hotel_downgrade_success(self, p1, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["houses"] = 5

        engine.sell_house(p1, konopacka, bank)

        assert konopacka["houses"] == 4
        assert bank["hotels"] == 12 + 1
        assert bank["houses"] == 32 - 4
        assert p1["budget"] == 1500 + konopacka["house_cost"] // 2


# ============================================================
# Zastaw (mortgage)
# ============================================================
class TestMortgageProperty:
    def test_success_pays_half_price(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1

        engine.mortgage_property(p1, konopacka)

        assert konopacka["is_mortgaged"] is True
        assert p1["budget"] == 1500 + konopacka["price"] // 2

    def test_blocks_non_owner(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1

        engine.mortgage_property(p2, konopacka)

        assert konopacka["is_mortgaged"] is False
        assert p2["budget"] == 1500

    def test_blocks_already_mortgaged(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True

        engine.mortgage_property(p1, konopacka)

        assert p1["budget"] == 1500  # brak podwójnej wypłaty

    def test_blocks_when_group_has_houses(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        stalowa = find_field("ulica_stalowa")
        konopacka["owner"] = p1
        stalowa["owner"] = p1
        stalowa["houses"] = 1

        engine.mortgage_property(p1, konopacka)

        assert konopacka["is_mortgaged"] is False
        assert p1["budget"] == 1500


class TestUnmortgageProperty:
    def test_calculate_unmortgage_value_rounds_up_from_half_cent(self, find_field):
        belwederska = find_field("ulica_belwederska")  # price 350
        assert engine.calculate_unmortgage_value(belwederska) == 193

    def test_calculate_unmortgage_value_exact_case(self, find_field):
        konopacka = find_field("ulica_konopacka")  # price 60 -> 30 * 1.1 = 33.0
        assert engine.calculate_unmortgage_value(konopacka) == 33

    def test_success_charges_110_percent(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True

        engine.unmortgage_property(p1, konopacka)

        assert konopacka["is_mortgaged"] is False
        assert p1["budget"] == 1500 - 33

    def test_blocks_non_owner(self, p1, p2, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True

        engine.unmortgage_property(p2, konopacka)

        assert konopacka["is_mortgaged"] is True
        assert p2["budget"] == 1500

    def test_blocks_when_not_mortgaged(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1

        engine.unmortgage_property(p1, konopacka)

        assert p1["budget"] == 1500

    def test_blocks_insufficient_funds(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True
        p1["budget"] = 10  # < 33

        engine.unmortgage_property(p1, konopacka)

        assert konopacka["is_mortgaged"] is True
        assert p1["budget"] == 10


# ============================================================
# reset_game
# ============================================================
class TestResetGame:
    def test_clears_ownership_houses_and_mortgage(self, p1, p2, bank, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["owner"] = p1
        konopacka["is_mortgaged"] = True
        konopacka["houses"] = 3
        p1["properties"] = [konopacka]
        p1["budget"] = 42
        bank["houses"] = 5

        engine.reset_game(p1, p2, bank)

        assert konopacka["owner"] is None
        assert konopacka["is_mortgaged"] is False
        assert konopacka["houses"] == 0
        assert p1["budget"] == 1500
        assert p1["properties"] == []
        assert bank["houses"] == 32
        assert bank["hotels"] == 12


# ============================================================
# Ruch po planszy i więzienie
# ============================================================
class TestMovement:
    def test_move_player_awards_go_bonus_on_wrap(self, p1):
        p1["position_index"] = 38

        new_position = engine.move_player(p1, 5)

        assert new_position == 3
        assert p1["budget"] == 1500 + 200

    def test_move_player_no_bonus_without_wrap(self, p1):
        p1["position_index"] = 2

        new_position = engine.move_player(p1, 5)

        assert new_position == 7
        assert p1["budget"] == 1500

    def test_send_to_jail_resets_state(self, p1):
        p1["position_index"] = 20
        p1["double_count"] = 2

        engine.send_to_jail(p1)

        assert p1["position_index"] == 10
        assert p1["in_jail"] is True
        assert p1["jail_turns"] == 0
        assert p1["double_count"] == 0


# ============================================================
# Karty Szansy / Kasy Społecznej
# ============================================================
class TestCards:
    def test_bank_money_positive(self, p1):
        engine.handle_card_bank_money(p1, {"amount": 150})
        assert p1["budget"] == 1650

    def test_bank_money_negative(self, p1):
        engine.handle_card_bank_money(p1, {"amount": -15})
        assert p1["budget"] == 1485

    def test_pay_players_pays_every_opponent(self, p1, p2):
        engine.handle_chance_pay_players(p1, {"amount": 50}, [p1, p2])
        assert p1["budget"] == 1450
        assert p2["budget"] == 1550

    def test_collect_from_players_collects_from_every_opponent(self, p1, p2):
        engine.handle_community_chest_collect_from_players(p1, {"amount": 10}, [p1, p2])
        assert p1["budget"] == 1510
        assert p2["budget"] == 1490

    def test_property_repairs_charges_per_house_and_hotel(self, p1, find_field):
        konopacka = find_field("ulica_konopacka")
        konopacka["houses"] = 2
        plowiecka = find_field("ulica_plowiecka")
        plowiecka["houses"] = 5  # hotel
        p1["properties"] = [konopacka, plowiecka]

        engine.handle_card_property_repairs(p1, {"house_cost": 25, "hotel_cost": 100})

        assert p1["budget"] == 1500 - (2 * 25 + 1 * 100)

    def test_property_repairs_free_without_buildings(self, p1):
        p1["properties"] = []
        engine.handle_card_property_repairs(p1, {"house_cost": 25, "hotel_cost": 100})
        assert p1["budget"] == 1500

    def test_move_to_field_awards_go_bonus_on_wrap(self, p1, p2, find_field):
        plowiecka = find_field("ulica_plowiecka")  # index 11
        plowiecka["owner"] = p1  # unikamy promptu o zakup
        p1["position_index"] = 15

        engine.handle_card_move_to_field(
            p1, {"target_id": "ulica_plowiecka", "collect_start": True}, 7, [p1, p2]
        )

        assert p1["position_index"] == 11
        assert p1["budget"] == 1500 + 200

    def test_move_to_field_no_bonus_without_wrap(self, p1, p2, find_field):
        plowiecka = find_field("ulica_plowiecka")  # index 11
        plowiecka["owner"] = p1
        p1["position_index"] = 5

        engine.handle_card_move_to_field(
            p1, {"target_id": "ulica_plowiecka", "collect_start": True}, 7, [p1, p2]
        )

        assert p1["position_index"] == 11
        assert p1["budget"] == 1500

    def test_nearest_station_uses_default_double_rent(self, p1, p2, find_field):
        p1["position_index"] = 0
        station = find_field("dworzec_zachodni")  # najbliższy dworzec od pola 0
        station["owner"] = p2
        p2["properties"] = [station]

        engine.handle_chance_nearest_station(p1, {"rent_multiplier": 2})

        assert p1["position_index"] == 5
        assert p1["budget"] == 1500 - station["rent_levels"][0] * 2
        assert p2["budget"] == 1500 + station["rent_levels"][0] * 2

    def test_nearest_utility_uses_flat_dice_multiplier(self, p1, p2, find_field, monkeypatch):
        p1["position_index"] = 0
        company = find_field("elektrownia")  # najbliższa firma od pola 0
        company["owner"] = p2
        p2["properties"] = [company]
        monkeypatch.setattr(engine, "roll_dice", lambda: (3, 4))

        engine.handle_chance_nearest_utility(p1, {"dice_multiplier": 10})

        assert p1["position_index"] == 12
        assert p1["budget"] == 1500 - 7 * 10
        assert p2["budget"] == 1500 + 7 * 10

    def test_keep_jail_card_roundtrip(self, p1):
        deck = [{"id": "chest_get_out_of_jail", "action_type": "keep_jail_card"}]
        card = deck.pop(0)

        engine.handle_card_keep_jail_card(p1, card, deck)

        assert p1["jail_cards_count"] == 1
        assert deck == []  # karta u gracza, jeszcze nie wróciła do talii

        held = p1["jail_cards_held"].pop(0)
        held["deck"].append(held["card"])

        assert deck == [card]  # wraca na spód właściwej talii po użyciu


# ============================================================
# Podatek i dispatch pól
# ============================================================
class TestTaxAndDispatch:
    def test_handle_tax_deducts_amount(self, p1, find_field):
        tax_field = find_field("tax_1")
        engine.handle_tax(p1, tax_field)
        assert p1["budget"] == 1500 - tax_field["tax"]

    def test_go_to_jail_field_sends_player_to_jail(self, p1, p2, find_field):
        go_to_jail_field = find_field("go_to_jail")
        engine.handle_field_action(p1, go_to_jail_field, 7, [p1, p2])
        assert p1["in_jail"] is True
        assert p1["position_index"] == 10

    @pytest.mark.parametrize("field_id", ["start", "jail", "parking"])
    def test_noop_fields_do_not_change_budget(self, p1, p2, find_field, field_id):
        target = find_field(field_id)
        engine.handle_field_action(p1, target, 7, [p1, p2])
        assert p1["budget"] == 1500
