import random
from chance_cards import chance_cards
from community_chest_cards import community_chest_cards


# Rzut kostką
def roll_dice():
    dice_one = random.randint(1, 6)
    dice_two = random.randint(1, 6)
    return dice_one, dice_two


# Ruszanie graczy po planszy
def move_player(player, steps):
    BOARD_SIZE = 40
    old_position = player["position_index"]
    new_position = (old_position + steps) % BOARD_SIZE
    player["position_index"] = new_position

    # Jeśli nowa pozycja jest mniejsza niż stara, gracz przekroczył Start
    if new_position < old_position and steps > 0:
        player["budget"] += 200
        print(f"💰 {player['name']} passed START and collected $200!")

    return new_position


# Logika pól
# ==================================================
def handle_property(player, field):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner == player:
        print(f"{player['name']} stood on their own property: {field['name']}.")
    # WARUNEK 2: Nieruchomość przeciwnika (płacenie czynszu)
    elif owner is not None:
        rent = field.get("base_rent")
        print(
            f"{player['name']} landed on {owner['name']}'s property and paid ${rent} rent!"
        )

        player["budget"] -= rent
        owner["budget"] += rent
    # WARUNEK 3: Nieruchomość na sprzedaż
    else:
        print(f"{field['name']} is for sale for ${field['price']}!")
        should_buy = False

        # Obsułga decyzji (Człowiek vs Komputer)
        if player["name"] == "Computer":
            should_buy = (
                player["budget"] >= field["price"]
            )  # Wstępna logika komputer zawsze kupuje jak ma hajs, póżniej to zmienię
        else:
            while True:
                want_buy = (
                    input("\nType (buy) to purchase, (not) to pass: ").strip().lower()
                )
                if want_buy == "buy":
                    should_buy = True
                    break
                elif want_buy == "not":
                    should_buy = False
                    break
                else:
                    print("Invalid input! Choose 'buy' or 'not'.")

        if should_buy:
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player  # Przypisujemy obiekt gracza jako właściciela
                player["properties"].append(field)
                print(f"{player['name']} bought {field['name']} for ${field['price']}!")
            else:
                print(
                    f"{player['name']} does not have enough money to buy {field['name']}!"
                )


def handle_station(player, field):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner == player:
        print(f"{player['name']} stood on their own station: {field['name']}.")
    # WARUNEK 2: Stacja przeciwnika (płacenie czynszu)
    elif owner is not None:
        station_count = 0
        for p in owner["properties"]:
            if p["type"] == "station":
                station_count += 1

        rent_levels = field["rent_levels"]
        # Jeśli ma 1 dworzec -> station_count wynosi 1 -> pobieramy indeks 0 (25$)
        if station_count > 0:
            rent = rent_levels[station_count - 1]
        else:
            rent = 0

        print(f"{player['name']} landed on {owner['name']}'s station!")
        print(f"{owner['name']} owns {station_count} station(s). Rent is ${rent}!")

        player["budget"] -= rent
        owner["budget"] += rent
    # WARUNEK 3: Stacja na sprzedaż
    else:
        print(f"{field['name']} is for sale for ${field['price']}!")
        should_buy = False

        if player["name"] == "Computer":
            should_buy = (
                player["budget"] >= field["price"]
            )  # Wstępna logika komputer zawsze kupuje jak ma hajs, póżniej to zmienię
        else:
            while True:
                want_buy = (
                    input("Type (buy) to purchase, (not) to pass: ").strip().lower()
                )
                if want_buy == "buy":
                    should_buy = True
                    break
                elif want_buy == "not":
                    should_buy = False
                    break
                else:
                    print("Invalid input! Choose 'buy' or 'not'.")

        if should_buy:
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player
                player["properties"].append(field)
                print(f"{player['name']} bought {field['name']} for ${field['price']}!")
            else:
                print(f"{player['name']} does not have enough money!")


def handle_company(player, field, total_steps):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner == player:
        print(f"⚡ {player['name']} stood on their own company: {field['name']}.")

    # WARUNEK 2: Firma przeciwnika (płacenie czynszu)
    elif owner is not None:
        company_count = 0
        for c in owner["properties"]:
            if c["type"] == "company":
                company_count += 1
        rent = 0
        if company_count == 1:
            rent = total_steps * 4
        elif company_count == 2:
            rent = total_steps * 10

        print(f"💸 {player['name']} landed on {owner['name']}'s company!")
        print(f"{owner['name']} owns {company_count} company(s). Rent is ${rent}!")

        player["budget"] -= rent
        owner["budget"] += rent
    # WARUNEK 3: Firma na sprzedaż
    else:
        print(f"💡{field['name']} is for sale for ${field['price']}!")
        should_buy = False

        if player["name"] == "Computer":
            should_buy = (
                player["budget"] >= field["price"]
            )  # Wstępna logika komputer zawsze kupuje jak ma hajs, póżniej to zmienię
        else:
            while True:
                want_buy = (
                    input("Type (buy) to purchase, (not) to pass: ").strip().lower()
                )
                if want_buy == "buy":
                    should_buy = True
                    break
                elif want_buy == "not":
                    should_buy = False
                    break
                else:
                    print("Invalid input! Choose 'buy' or 'not'.")

        if should_buy:
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player
                player["properties"].append(field)
                print(
                    f"✅ {player['name']} bought {field['name']} for ${field['price']}!"
                )
            else:
                print(f"❌ {player['name']} does not have enough money!")


def handle_tax(player, field):
    tax_amount = field.get("tax")

    player["budget"] -= tax_amount
    print(
        f"{player['name']} paid tax ({field['name']}): - ${tax_amount}. Remaining budget: ${player['budget']}\n"
    )


# ==================================================

# Logika kart szansy i kasa społeczna
# ==================================================


def handle_go_to_jail(player):
    print("Mechanics of 'handle_go_to_jail' is not supported yet.\n")


def handle_card_bank_money(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_chance_move_relative(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_chance_pay_players(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_cart_move_to_field(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_card_go_to_jail(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_card_keep_jail_card(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_chance_nearest_station(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_chance_nearest_utility(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_card_property_repairs(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_community_chest_collect_from_players(player, card):
    print(f"Action type '{card['action_type']}' is not supported yet.\n")


def handle_chance(player, field):
    # 1. Pobieranie karty z góry talii i odłożenie na spód
    card = chance_cards.pop(0)
    chance_cards.append(card)

    print(f"\n {player['name']} draws a Chance card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    # 2. Dyspozytor akcji
    match card["action_type"]:
        case "bank_money":  #
            handle_card_bank_money(player, card)

        case "move_relative":  #
            handle_chance_move_relative(player, card)

        case "pay_players":  #
            handle_chance_pay_players(player, card)

        case "move_to_field":  #
            handle_cart_move_to_field(player, card)

        case "keep_jail_card":  #
            handle_card_keep_jail_card(player, card)

        case "go_to_jail":  #
            handle_card_go_to_jail(player, card)

        case "nearest_station":  #
            handle_chance_nearest_station(player, card)

        case "nearest_utility":  #
            handle_chance_nearest_utility(player, card)

        case "property_repairs":
            handle_card_property_repairs(player, card)


def handle_community_chest(player, field):
    card = community_chest_cards.pop(0)
    community_chest_cards.append(card)

    print(f"\n {player['name']} draws a community chest card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    match card["action_type"]:
        case "bank_money":
            handle_card_bank_money(player, card)  #

        case "go_to_jail":
            handle_card_go_to_jail(player, card)(player, card)  #

        case "keep_jail_card":
            handle_card_keep_jail_card(player, card)

        case "property_repairs":
            handle_card_property_repairs(player, card)

        case "move_to_field":
            handle_cart_move_to_field(player, card)

        case "collect_from_players":
            handle_community_chest_collect_from_players(player, card)


# ==================================================


def handle_field_action(player, field, total_steps):
    field_type = field["type"]

    match field_type:
        case "property":
            handle_property(player, field)
        case "tax":
            handle_tax(player, field)
        case "go_to_jail":
            handle_go_to_jail(player)
        case "chance":
            handle_chance(player, field)
        case "community_chest":
            handle_community_chest(player, field)
        case "station":
            handle_station(player, field)
        case "company":
            handle_company(player, field, total_steps)
        case "start" | "jail" | "parking":
            print(
                f"{player['name']} stood on {field['name']}, there is no action on this field"
            )
