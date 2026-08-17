import random
from chance_cards import chance_cards
from community_chest_cards import community_chest_cards
from board import board

BOARD_SIZE = 40
GO_BONUS = 200


def reset_game(player1, player2, bank):
    # 1. Reset stanu graczy
    for p in [player1, player2]:
        p["position_index"] = 0
        p["budget"] = 1500
        p["properties"] = []
        p["jail_cards_count"] = 0
        p["jail_cards_held"] = []
        p["in_jail"] = False
        p["jail_turns"] = 0
        p["double_count"] = 0
        p["is_in_debt"] = False
        p["creditor"] = None

    # 2. Reset stanu Banku
    bank["houses"] = 32
    bank["hotels"] = 12

    for field in board:
        if "owner" in field:
            field["owner"] = None
        if "houses" in field:
            field["houses"] = 0
        if "is_mortgaged" in field:
            field["is_mortgaged"] = False

    # 4. Ponowne przetasowanie kart
    random.shuffle(chance_cards)
    random.shuffle(community_chest_cards)


# Rzut kostką
def roll_dice():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return d1, d2


def passed_start(old_position, new_position):
    return new_position < old_position


def award_go_bonus(player):
    player["budget"] += GO_BONUS
    # Bonus może spłacić wcześniejszy dług, więc odświeżamy flagę
    check_and_flag_debt(player, creditor=player.get("creditor"))


def check_and_flag_debt(player, creditor=None):
    if player["budget"] < 0:
        player["is_in_debt"] = True
        player["creditor"] = creditor

        debt_amount = abs(player["budget"])
        creditor_name = creditor["name"] if creditor else "Bank"
        print(
            f"⚠️ DEBT DETECTED! {player['name']} is in debt: -${debt_amount} | Owed to: {creditor_name}"
        )
        return True
    else:
        player["is_in_debt"] = False
        player["creditor"] = None
        return False


def get_player_liquidation_value(player):
    # 1. 50% wartości ze sprzedaży wszystkich domków i hoteli
    total_building_value = sum(
        (p.get("houses", 0) * p["house_cost"]) // 2
        for p in player["properties"]
        if p.get("houses", 0) > 0
    )

    # 2. 50% wartości zakupu z zastawienia niezastawionych działek
    total_properties_value = sum(
        p["price"] // 2
        for p in player["properties"]
        if not p.get("is_mortgaged", False)
    )

    # Zwraca łączny bilans (ujemny budżet + maksymalna gotówka z wyprzedaży)
    return player["budget"] + total_building_value + total_properties_value


# Ruszanie graczy po planszy
def move_player(player, steps):
    old_position = player["position_index"]
    new_position = (old_position + steps) % BOARD_SIZE
    player["position_index"] = new_position

    # Jeśli nowa pozycja jest mniejsza niż stara, gracz przekroczył Start
    if steps > 0 and passed_start(old_position, new_position):
        award_go_bonus(player)
        print(f"💰 {player['name']} passed START and collected $200!")

    return new_position


def send_to_jail(player):
    player["position_index"] = 10
    player["in_jail"] = True
    player["jail_turns"] = 0
    player["double_count"] = 0
    print(f"🚨 {player['name']} is sent directly to Jail!")


# Logika pól
# ==================================================
def decide_purchase(player, field):
    if player["name"] == "Computer":
        # Wstępna logika: komputer zawsze kupuje, jeśli ma wystarczająco pieniędzy.
        return player["budget"] >= field["price"]

    while True:
        want_buy = input("\nType (buy) to purchase, (not) to pass: ").strip().lower()
        if want_buy == "buy":
            return True
        elif want_buy == "not":
            return False
        else:
            print("Invalid input! Choose 'buy' or 'not'.")


def attempt_purchase(player, field):
    if decide_purchase(player, field):
        if player["budget"] >= field["price"]:
            player["budget"] -= field["price"]
            field["owner"] = player  # Przypisujemy obiekt gracza jako właściciela
            field["is_mortgaged"] = False
            player["properties"].append(field)
            print(f"✅ {player['name']} bought {field['name']} for ${field['price']}!")
        else:
            print(
                f"{player['name']} does not have enough money to buy {field['name']}!"
            )


def has_monopoly(player, group_name):
    # 1. Liczymy, ile w sumie jest ulic w tym kolorze na całej planszy
    total_in_group = 0
    for field in board:
        if field.get("type") == "property" and field.get("group") == group_name:
            total_in_group += 1

    # 2. Liczymy, ile z tych ulic ma w ekwipunku gracz
    player_in_group = sum(
        1 for p in player["properties"] if p.get("group") == group_name
    )

    # 3. Zwracamy True tylko wtedy, gdy gracz ma wszystkie ulice z danego koloru
    return total_in_group == player_in_group and total_in_group > 0


def get_group_properties(group_name):
    return [
        f for f in board if f.get("type") == "property" and f.get("group") == group_name
    ]


def group_has_mortgaged_property(group_name):
    return any(f.get("is_mortgaged", False) for f in get_group_properties(group_name))


def group_has_houses(group_name):
    return any(f.get("houses", 0) > 0 for f in get_group_properties(group_name))


def rent_blocked_by_mortgage(player, field):
    if field.get("is_mortgaged", False):
        print(
            f"  {field['name']} is mortgaged! {player['name']} does not pay any rent."
        )
        return True
    return False


def calculate_unmortgage_value(field):
    return round((field["price"] // 2) * 1.1)


def get_player_monopolies(player):
    # 1. Zbieramy unikalne grupy kolorów z posiadłości gracza (używamy set, żeby uniknąć duplikatów)
    player_groups = set()
    for prop in player["properties"]:
        group = prop.get("group")
        if group:
            player_groups.add(group)

    # 2. Sprawdzamy, na które z tych grup gracz ma pełny monopol
    monopolies = []
    for group in player_groups:
        if has_monopoly(player, group):
            monopolies.append(group)

    # jeżeli gracz nie ma monopola zwraca [] czyli wartość Fals'ową, jeżeli gracz ma monopol
    # zwraca jego kolor np. ["red"] albo pare ["red", "green", "pink"]
    return monopolies


def build_house(player, field, bank):
    group_name = field["group"]

    # 1. Sprawdzenie monopolu
    if not has_monopoly(player, group_name):
        print(f"❌ {player['name']} does not have a monopoly on {group_name.upper()}!")
        return

    # 2. Pobieramy wszystkie ulice z tej grupy
    group_props = get_group_properties(group_name)

    # 🚨 BLOKADA BUDOWANIA DLA HIPOTEKI
    # Jeśli którakolwiek ulica w grupie jest zastawiona, blokujemy rozbudowę
    if group_has_mortgaged_property(group_name):
        print(
            f"❌ Cannot build on {group_name.upper()}! One or more properties in this group are mortgaged."
        )
        return

    current_houses = field.get("houses", 0)
    house_cost = field["house_cost"]

    # 3. Sprawdzenie maksymalnego rozbudowania (Hotel = 5)
    if current_houses >= 5:
        print(f"❌ {field['name']} already has a Hotel!")
        return

    # 4. Zasada równomiernego budowania
    min_houses = min(f.get("houses", 0) for f in group_props)
    if current_houses > min_houses:
        print(
            f"❌ You must build evenly! Build on other properties in {group_name.upper()} first."
        )
        return

    # 5. Sprawdzenie budżetu gracza
    if player["budget"] < house_cost:
        print(f"❌ {player['name']} cannot afford a building (${house_cost})!")
        return

    # 6A. Budowa DOMKU (poziomy 1-4)
    if current_houses < 4:
        if bank["houses"] <= 0:
            print("❌ Bank has no more houses available!")
            return

        player["budget"] -= house_cost
        field["houses"] = current_houses + 1
        bank["houses"] -= 1
        print(
            f"🏠 {player['name']} built a house on {field['name']} for ${house_cost}!"
        )

    # 6B. Transakcja na HOTEL (poziom 5)
    elif current_houses == 4:
        if bank["hotels"] <= 0:
            print("❌ Bank has no more hotels available!")
            return

        player["budget"] -= house_cost
        field["houses"] = 5
        bank["hotels"] -= 1
        bank["houses"] += 4  # 4 domki wracają do Banku
        print(
            f"🏨 {player['name']} built a HOTEL on {field['name']} for ${house_cost}!"
        )


def can_sell_house(field):
    # Zasada równomiernego sprzedawania (Even Selling Rule): sprzedawać można
    # wyłącznie z ulic posiadających najwięcej budynków w danej grupie kolorystycznej
    houses = field.get("houses", 0)
    if houses <= 0:
        return False
    group_props = get_group_properties(field["group"])
    max_houses = max(f.get("houses", 0) for f in group_props)
    return houses == max_houses


def sell_house(player, field, bank):
    group_name = field["group"]
    current_houses = field.get("houses", 0)

    # 1. Sprawdzenie, czy na tej konkretnej ulicy w ogóle stoją budynki
    if current_houses <= 0:
        print(f"❌ {field['name']} has no buildings to sell!")
        return

    # 2. Zasada równomiernego sprzedawania (Even Selling Rule)
    if not can_sell_house(field):
        max_houses = max(
            f.get("houses", 0) for f in get_group_properties(group_name)
        )
        print(
            f"❌ You must sell evenly! Sell from properties with {max_houses} building(s) in {group_name.upper()} first."
        )
        return

    refund = field["house_cost"] // 2

    # 3A. Sprzedaż HOTELU (Zejście z poziomu 5 na 4 domki)
    if current_houses == 5:
        # Bank musi posiadać co najmniej 4 wolne domki, aby zamienić hotel z powrotem na 4 domki
        if bank["houses"] < 4:
            print(
                "❌ Bank does not have enough houses (4 required) to downgrade the Hotel!"
            )
            return

        field["houses"] = 4
        bank["hotels"] += 1
        bank["houses"] -= 4
        player["budget"] += refund
        print(
            f"🏨 {player['name']} sold a HOTEL on {field['name']} for ${refund}! (Replaced with 4 houses)"
        )

    # 3B. Sprzedaż zwykłego DOMKU (Poziomy 1–4)
    else:
        field["houses"] = current_houses - 1
        bank["houses"] += 1
        player["budget"] += refund
        print(f"🏠 {player['name']} sold a house on {field['name']} for ${refund}!")


def mortgage_property(player, field):
    # 1. Zabezpieczenie przed zastawieniem nieruchomości należącej do innego gracza
    if field.get("owner") is not player:
        print(f"❌ {player['name']} does not own {field['name']}!")
        return

    # 2. Zabezpieczenie przed ponownym zastawieniem
    if field.get("is_mortgaged", False):
        print(f"❌ {field['name']} is already mortgaged.")
        return

    # 3. Zabezpieczenie przed zastawieniem nieruchomości z domkami w dzielnicy
    group_name = field.get("group")
    if group_name and group_has_houses(group_name):
        print(
            f"❌ Cannot mortgage {field['name']}! You must sell all houses in {group_name.upper()} first."
        )
        return

    # 4. Wyliczenie kwoty zastawu (50% ceny zakupu)
    mortgage_value = field["price"] // 2

    # 5. Aktualizacja stanu gry
    field["is_mortgaged"] = True
    player["budget"] += mortgage_value

    # 6. Komunikat dla gracza
    print(f"🏦 {player['name']} mortgaged {field['name']} for ${mortgage_value}!")
    print(f"   Current budget: ${player['budget']}")


def unmortgage_property(player, field):
    # 1. Zabezpieczenie przed wykupem nieruchomości należącej do innego gracza
    if field.get("owner") is not player:
        print(f"❌ {player['name']} does not own {field['name']}!")
        return

    # 2. Weryfikacja statusu hipoteki (Guard Clause)
    if not field.get("is_mortgaged", False):
        print(f"❌ {field['name']} is not mortgaged.")
        return

    # 3. Kalkulacja kosztu wykupu
    unmortgage_value = calculate_unmortgage_value(field)

    # 4. Sprawdzenie budżetu gracza (Guard Clause)
    if player["budget"] < unmortgage_value:
        print(
            f"❌ {player['name']} cannot pay ${unmortgage_value} to unmortgage {field['name']}!"
        )
        return

    # 5. Realizacja transakcji w pamięci
    player["budget"] -= unmortgage_value
    field["is_mortgaged"] = False

    # 6. Powiadomienie gracza
    print(f"🏦 {player['name']} unmortgaged {field['name']} for ${unmortgage_value}!")
    print(f"   Current budget: ${player['budget']}")


def handle_property(player, field):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"🏠 {player['name']} stood on their own property: {field['name']}.")

    # WARUNEK 2: Nieruchomość przeciwnika (płacenie czynszu)
    elif owner is not None:
        # 🚨 BLOKADA CZYNSZU DLA HIPOTEKI
        if rent_blocked_by_mortgage(player, field):
            return

        houses = field.get("houses", 0)

        # 3. Jeśli na ulicy stoją budynki (1-4 domki lub 5 = hotel)
        if houses > 0:
            rent = field["house_rents"][houses - 1]
            print(
                f"🏠 {player['name']} landed on {owner['name']}'s property with {houses} building(s)!"
            )

        # 4. Jeśli nie ma budynków, ale właściciel ma MONOPOL -> Podwójny czynsz
        # (mortgage nie odbiera własności, więc nie przerywa monopolu na potrzeby tej reguły)
        elif has_monopoly(owner, field["group"]):
            rent = field.get("base_rent") * 2
            print(
                f"👑 {owner['name']} has a MONOPOLY on {field['group']}! Rent is doubled."
            )

        # 5. Zwykły czynsz bazowy
        else:
            rent = field.get("base_rent")

        print(
            f"💸 {player['name']} landed on {owner['name']}'s property and paid ${rent} rent!"
        )
        player["budget"] -= rent
        owner["budget"] += rent

        # 🚨 DETEKCJA DŁUGU (wierzycielem jest owner)
        check_and_flag_debt(player, creditor=owner)
        # Czynsz mógł spłacić wcześniejszy dług właściciela, więc odświeżamy jego flagę
        check_and_flag_debt(owner, creditor=owner.get("creditor"))

    # WARUNEK 6: Nieruchomość na sprzedaż
    else:
        print(f"🏷️ {field['name']} is for sale for ${field['price']}!")
        attempt_purchase(player, field)


def handle_station(player, field, multiplier=1):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"🚆 {player['name']} stood on their own station: {field['name']}.")

    # WARUNEK 2: Stacja przeciwnika (płacenie czynszu)
    elif owner is not None:
        # 🚨 BLOKADA CZYNSZU DLA HIPOTEKI
        if rent_blocked_by_mortgage(player, field):
            return

        # Liczba dworców to WSZYSTKIE posiadane, także zastawione — mortgage nie zmienia
        # własności, tylko blokuje czynsz z tej konkretnej nieruchomości.
        station_count = sum(
            1 for p in owner["properties"] if p.get("type") == "station"
        )
        rent_levels = field["rent_levels"]

        # Obliczamy czynsz i MNOŻYMY przez multiplier!
        if station_count > 0:
            rent = rent_levels[station_count - 1] * multiplier
        else:
            rent = 0

        print(f"💸 {player['name']} landed on {owner['name']}'s station!")

        if multiplier > 1:
            print(
                f"   {owner['name']} owns {station_count} station(s). Rent is ${rent} (Multiplier x{multiplier})!"
            )
        else:
            print(
                f"   {owner['name']} owns {station_count} station(s). Rent is ${rent}!"
            )

        player["budget"] -= rent
        owner["budget"] += rent

        # 🚨 DETEKCJA DŁUGU (wierzycielem jest owner)
        check_and_flag_debt(player, creditor=owner)
        # Czynsz mógł spłacić wcześniejszy dług właściciela, więc odświeżamy jego flagę
        check_and_flag_debt(owner, creditor=owner.get("creditor"))
    # WARUNEK 3: Stacja na sprzedaż
    else:
        print(f"🏷️ {field['name']} is for sale for ${field['price']}!")
        attempt_purchase(player, field)


def handle_company(player, field, dice_total, custom_multiplier=None):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"⚡ {player['name']} stood on their own company: {field['name']}.")

    # WARUNEK 2: Firma przeciwnika (płacenie czynszu)
    elif owner is not None:
        # 🚨 BLOKADA CZYNSZU DLA HIPOTEKI
        if rent_blocked_by_mortgage(player, field):
            return

        # Liczba firm to WSZYSTKIE posiadane, także zastawione — jak przy dworcach.
        company_count = sum(
            1 for p in owner["properties"] if p.get("type") == "company"
        )

        if custom_multiplier is not None:
            rent = dice_total * custom_multiplier
        elif company_count == 1:
            rent = dice_total * 4
        else:
            rent = dice_total * 10

        print(f"💸 {player['name']} landed on {owner['name']}'s company!")
        if custom_multiplier is not None:
            print(
                f"   {owner['name']} owns {company_count} company(s). Rent is ${rent} (Dice: {dice_total} x {custom_multiplier})!"
            )
        else:
            print(
                f"   {owner['name']} owns {company_count} company(s). Rent is ${rent} (Dice: {dice_total})!"
            )

        player["budget"] -= rent
        owner["budget"] += rent

        # 🚨 DETEKCJA DŁUGU (wierzycielem jest owner)
        check_and_flag_debt(player, creditor=owner)
        # Czynsz mógł spłacić wcześniejszy dług właściciela, więc odświeżamy jego flagę
        check_and_flag_debt(owner, creditor=owner.get("creditor"))
    # WARUNEK 3: Firma na sprzedaż
    else:
        print(f"💡 {field['name']} is for sale for ${field['price']}!")
        attempt_purchase(player, field)


def handle_tax(player, field):
    tax_amount = field.get("tax")
    player["budget"] -= tax_amount

    # 🚨 DETEKCJA DŁUGU (wierzycielem jest Bank)
    check_and_flag_debt(player, creditor=None)

    print(
        f"{player['name']} paid tax ({field['name']}): - ${tax_amount}. Remaining budget: ${player['budget']}"
    )


# ==================================================

# Logika kart szansy i kasa społeczna
# ==================================================


def handle_card_bank_money(player, card):
    amount = card["amount"]
    player["budget"] += amount

    if amount < 0:
        # Nowa opłata na rzecz Banku - to on jest wierzycielem ewentualnego długu
        check_and_flag_debt(player, creditor=None)
    else:
        # Wpływ mógł spłacić wcześniejszy dług - zachowujemy dotychczasowego wierzyciela
        check_and_flag_debt(player, creditor=player.get("creditor"))

    if amount > 0:
        print(
            f"💰 {player['name']} receives ${amount}. Current budget: ${player['budget']}."
        )
    else:
        print(
            f"💸 {player['name']} pays ${abs(amount)}. Current budget: ${player['budget']}."
        )


def handle_chance_move_relative(player, card, dice_total, all_players):
    steps = card["steps"]
    old_position = player["position_index"]

    new_position = (old_position + steps) % BOARD_SIZE
    player["position_index"] = new_position

    new_field = board[new_position]

    direction = "forward" if steps > 0 else "backward"
    print(f"🚶 {player['name']} moves {direction} by {abs(steps)} spaces.")
    print(f"Landed on: {new_field['name']} (Field: #{new_position})")

    handle_field_action(player, new_field, dice_total, all_players)


def handle_card_move_to_field(player, card, dice_total, all_players):
    target_id = card["target_id"]
    old_position = player["position_index"]

    new_field = None
    for field in board:
        if field["id"] == target_id:
            new_field = field
            break

    if new_field is None:
        raise ValueError(f"Unknown target_id in card: {target_id}")

    new_position = new_field["index"]

    if card.get("collect_start", False) and (
        passed_start(old_position, new_position) or target_id == "start"
    ):
        award_go_bonus(player)
        print(
            f"💰 {player['name']} passes START and collects $200! Current budget: ${player['budget']}."
        )

    player["position_index"] = new_position
    print(
        f"✈️  {player['name']} goes directly to: {new_field['name']} (Field: #{new_position})."
    )

    handle_field_action(player, new_field, dice_total, all_players)


def handle_chance_pay_players(player, card, all_players):
    amount = card["amount"]

    for opponent in all_players:
        if opponent is not player:
            player["budget"] -= amount
            opponent["budget"] += amount
            print(f"💸 {player['name']} pays to {opponent['name']} ${amount}!")
            check_and_flag_debt(player, creditor=opponent)
            # Otrzymana kwota mogła spłacić wcześniejszy dług przeciwnika
            check_and_flag_debt(opponent, creditor=opponent.get("creditor"))


def handle_card_keep_jail_card(player, card, deck):
    player["jail_cards_count"] += 1
    player["jail_cards_held"].append({"card": card, "deck": deck})

    print(f"🎟️ {player['name']} got a 'Get out of jail free' Card!")
    print(f"   (Cards in inventory: {player['jail_cards_count']})")


def find_nearest_field(position, field_type):
    steps = 1
    while True:
        check_index = (position + steps) % BOARD_SIZE
        if board[check_index]["type"] == field_type:
            return board[check_index]
        steps += 1


def handle_chance_nearest_station(player, card):
    old_position = player["position_index"]
    new_field = find_nearest_field(old_position, "station")
    new_position = new_field["index"]

    if passed_start(old_position, new_position):
        award_go_bonus(player)
        print(f"💰 {player['name']} passes START and collects $200!")

    player["position_index"] = new_position
    print(
        f"🚂 {player['name']} advances to nearest station: {new_field['name']} (Field: #{new_position})."
    )

    multiplier = card.get("rent_multiplier", 2)
    handle_station(player, new_field, multiplier)


def handle_chance_nearest_utility(player, card):
    old_position = player["position_index"]
    new_field = find_nearest_field(old_position, "company")
    new_position = new_field["index"]

    if passed_start(old_position, new_position):
        award_go_bonus(player)
        print(f"💰 {player['name']} passes START and collects $200!")

    player["position_index"] = new_position
    print(
        f"💡 {player['name']} advances to nearest company: {new_field['name']} (Field: #{new_position})."
    )

    d1, d2 = roll_dice()
    dice_total = d1 + d2
    print(
        f"🎲 {player['name']} rolls the dice for utility rent: {d1} and {d2} (Total: {dice_total})"
    )

    multiplier = card.get("dice_multiplier", 10)

    handle_company(player, new_field, dice_total, custom_multiplier=multiplier)


def handle_card_property_repairs(player, card):
    house_cost = card["house_cost"]
    hotel_cost = card["hotel_cost"]

    total_houses = 0
    total_hotels = 0

    # 1. Liczymy wszystkie domki i hotele gracza
    for prop in player["properties"]:
        houses = prop.get("houses", 0)
        if houses == 5:
            total_hotels += 1
        elif houses > 0:
            total_houses += houses

    # 2. Jeśli gracz nic nie ma, to ma farta!
    if total_houses == 0 and total_hotels == 0:
        print(f"😊 {player['name']} owns no buildings. Repair cost is $0!")
        return

    # 3. Obliczamy całkowity koszt
    total_cost = (total_houses * house_cost) + (total_hotels * hotel_cost)

    player["budget"] -= total_cost
    print(
        f"🛠️ {player['name']} paid ${total_cost} for property repairs ({total_houses} houses, {total_hotels} hotels)."
    )

    check_and_flag_debt(player, creditor=None)


def handle_community_chest_collect_from_players(player, card, all_players):
    amount = card["amount"]

    for opponent in all_players:
        if opponent is not player:
            player["budget"] += amount
            opponent["budget"] -= amount
            print(f"🎁 {player['name']} collects ${amount} from {opponent['name']}!")

            check_and_flag_debt(opponent, creditor=player)
            # Otrzymana kwota mogła spłacić wcześniejszy dług gracza
            check_and_flag_debt(player, creditor=player.get("creditor"))

    print(f"💰 {player['name']}'s current budget: ${player['budget']}.")


# ======================================================================== #


def handle_chance(player, field, dice_total, all_players):
    # 1. Pobieranie karty z góry talii i odłożenie na spód
    card = chance_cards.pop(0)

    # Karta "Wyjdź z więzienia za darmo" zostaje u gracza i wraca do talii
    # dopiero, gdy zostanie wykorzystana.
    if card["action_type"] != "keep_jail_card":
        chance_cards.append(card)

    print(f"\n {player['name']} draws a Chance card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    # 2. Dyspozytor akcji
    match card["action_type"]:
        case "bank_money":
            handle_card_bank_money(player, card)

        case "move_relative":
            handle_chance_move_relative(player, card, dice_total, all_players)

        case "pay_players":
            handle_chance_pay_players(player, card, all_players)

        case "move_to_field":
            handle_card_move_to_field(player, card, dice_total, all_players)

        case "keep_jail_card":
            handle_card_keep_jail_card(player, card, chance_cards)

        case "go_to_jail":
            send_to_jail(player)

        case "nearest_station":
            handle_chance_nearest_station(player, card)

        case "nearest_utility":
            handle_chance_nearest_utility(player, card)

        case "property_repairs":
            handle_card_property_repairs(player, card)


def handle_community_chest(player, field, dice_total, all_players):
    card = community_chest_cards.pop(0)

    # Karta "Wyjdź z więzienia za darmo" zostaje u gracza i wraca do talii
    # dopiero, gdy zostanie wykorzystana.
    if card["action_type"] != "keep_jail_card":
        community_chest_cards.append(card)

    print(f"\n {player['name']} draws a community chest card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    match card["action_type"]:
        case "bank_money":
            handle_card_bank_money(player, card)

        case "go_to_jail":
            send_to_jail(player)

        case "keep_jail_card":
            handle_card_keep_jail_card(player, card, community_chest_cards)

        case "property_repairs":
            handle_card_property_repairs(player, card)

        case "move_to_field":
            handle_card_move_to_field(player, card, dice_total, all_players)

        case "collect_from_players":
            handle_community_chest_collect_from_players(player, card, all_players)


# ==================================================


def handle_field_action(player, field, dice_total, all_players):
    field_type = field["type"]

    match field_type:
        case "property":
            handle_property(player, field)
        case "tax":
            handle_tax(player, field)
        case "go_to_jail":
            send_to_jail(player)
        case "chance":
            handle_chance(player, field, dice_total, all_players)
        case "community_chest":
            handle_community_chest(player, field, dice_total, all_players)
        case "station":
            handle_station(player, field)
        case "company":
            handle_company(player, field, dice_total)
        case "start" | "jail" | "parking":
            print(
                f"{player['name']} stood on: {field['name']}, there is no action on this field"
            )
