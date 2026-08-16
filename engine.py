import random
from chance_cards import chance_cards
from community_chest_cards import community_chest_cards
from board import board

BOARD_SIZE = 40
GO_BONUS = 200


# Rzut kostką
def roll_dice():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return d1, d2


def passed_start(old_position, new_position):
    return new_position < old_position


def award_go_bonus(player):
    player["budget"] += GO_BONUS


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


def handle_property(player, field):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"🏠 {player['name']} stood on their own property: {field['name']}.")
    # WARUNEK 2: Nieruchomość przeciwnika (płacenie czynszu)
    elif owner is not None:
        rent = field.get("base_rent")
        print(
            f"💸 {player['name']} landed on {owner['name']}'s property and paid ${rent} rent!"
        )

        player["budget"] -= rent
        owner["budget"] += rent
    # WARUNEK 3: Nieruchomość na sprzedaż
    else:
        print(f"🏷️ {field['name']} is for sale for ${field['price']}!")

        if decide_purchase(player, field):
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player  # Przypisujemy obiekt gracza jako właściciela
                player["properties"].append(field)
                print(
                    f"✅ {player['name']} bought {field['name']} for ${field['price']}!"
                )
            else:
                print(
                    f"{player['name']} does not have enough money to buy {field['name']}!"
                )


def handle_station(player, field, multiplier=1):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"🚆 {player['name']} stood on their own station: {field['name']}.")

    # WARUNEK 2: Stacja przeciwnika (płacenie czynszu)
    elif owner is not None:
        station_count = 0
        for p in owner["properties"]:
            if p["type"] == "station":
                station_count += 1

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
    # WARUNEK 3: Stacja na sprzedaż
    else:
        print(f"🏷️ {field['name']} is for sale for ${field['price']}!")

        if decide_purchase(player, field):
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player
                player["properties"].append(field)
                print(
                    f"✅ {player['name']} bought {field['name']} for ${field['price']}!"
                )
            else:
                print(
                    f"{player['name']} does not have enough money to buy {field['name']}!"
                )


def handle_company(player, field, dice_total, custom_multiplier=None):
    owner = field.get("owner")

    # WARUNEK 1: Twoja własność
    if owner is player:
        print(f"⚡ {player['name']} stood on their own company: {field['name']}.")

    # WARUNEK 2: Firma przeciwnika (płacenie czynszu)
    elif owner is not None:
        company_count = 0
        for c in owner["properties"]:
            if c["type"] == "company":
                company_count += 1

        if custom_multiplier is not None:
            rent = dice_total * custom_multiplier
        else:
            if company_count == 1:
                rent = dice_total * 4
            elif company_count == 2:
                rent = dice_total * 10
            else:
                rent = 0

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
    # WARUNEK 3: Firma na sprzedaż
    else:
        print(f"💡 {field['name']} is for sale for ${field['price']}!")

        if decide_purchase(player, field):
            if player["budget"] >= field["price"]:
                player["budget"] -= field["price"]
                field["owner"] = player
                player["properties"].append(field)
                print(
                    f"✅ {player['name']} bought {field['name']} for ${field['price']}!"
                )
            else:
                print(
                    f"{player['name']} does not have enough money to buy {field['name']}!"
                )


def handle_tax(player, field):
    tax_amount = field.get("tax")

    player["budget"] -= tax_amount
    print(
        f"{player['name']} paid tax ({field['name']}): - ${tax_amount}. Remaining budget: ${player['budget']}\n"
    )


def handle_go_to_jail(player):
    print("Not supported yet.")  # Do zrobienia


# ==================================================

# Logika kart szansy i kasa społeczna
# ==================================================


def handle_card_bank_money(player, card):
    amount = card["amount"]
    player["budget"] += amount

    if amount > 0:
        print(
            f"💰 {player['name']} receives ${amount}. Current budget: ${player['budget']}."
        )
    else:
        print(
            f"💸 {player['name']} pays ${abs(amount)}. Current budget: ${player['budget']}."
        )


def handle_chance_move_relative(player, card, all_players):
    steps = card["steps"]
    old_position = player["position_index"]

    new_position = (old_position + steps) % BOARD_SIZE
    player["position_index"] = new_position

    new_field = board[new_position]

    direction = "forward" if steps > 0 else "backward"
    print(f"🚶 {player['name']} moves {direction} by {abs(steps)} spaces.")
    print(f"Landed on: {new_field['name']} (Field: #{new_position})")

    handle_field_action(player, new_field, 0, all_players)


def handle_card_move_to_field(player, card, all_players):
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

    handle_field_action(player, new_field, 0, all_players)


def handle_chance_pay_players(player, card, all_players):
    amount = card["amount"]

    for opponent in all_players:
        if opponent != player:
            player["budget"] -= amount
            opponent["budget"] += amount

            print(f"💸 {player['name']} pays to {opponent['name']} ${amount}!")


def handle_card_keep_jail_card(player, card):
    player["jail_cards_count"] += 1

    print(f"🎟️ {player['name']} got a 'Get out of jail free' Card!")
    print(f"   (Cards in inventory: {player['jail_cards_count']})")


def handle_card_go_to_jail(player, card):
    print(
        f"Action type '{card['action_type']}' is not supported yet.\n"
    )  # Do zrobienia


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
    print(
        f"Action type '{card['action_type']}' is not supported yet.\n"
    )  # Do zrobienia


def handle_community_chest_collect_from_players(player, card, all_players):
    amount = card["amount"]

    for opponent in all_players:
        if opponent != player:
            player["budget"] += amount
            opponent["budget"] -= amount

            print(f"🎁 {player['name']} collects ${amount} from {opponent['name']}!")

    print(f"💰 {player['name']}'s current budget: ${player['budget']}.")


# ======================================================================== #


def handle_chance(player, field, all_players):
    # 1. Pobieranie karty z góry talii i odłożenie na spód
    card = chance_cards.pop(0)
    chance_cards.append(card)

    print(f"\n {player['name']} draws a Chance card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    # 2. Dyspozytor akcji
    match card["action_type"]:
        case "bank_money":
            handle_card_bank_money(player, card)

        case "move_relative":
            handle_chance_move_relative(player, card, all_players)

        case "pay_players":
            handle_chance_pay_players(player, card, all_players)

        case "move_to_field":
            handle_card_move_to_field(player, card, all_players)

        case "keep_jail_card":
            handle_card_keep_jail_card(player, card)

        case "go_to_jail":
            handle_card_go_to_jail(player, card)

        case "nearest_station":
            handle_chance_nearest_station(player, card)

        case "nearest_utility":
            handle_chance_nearest_utility(player, card)

        case "property_repairs":
            handle_card_property_repairs(player, card)


def handle_community_chest(player, field, all_players):
    card = community_chest_cards.pop(0)
    community_chest_cards.append(card)

    print(f"\n {player['name']} draws a community chest card: ")
    print()
    print(f"  \"{card['text']}\"\n")

    match card["action_type"]:
        case "bank_money":
            handle_card_bank_money(player, card)

        case "go_to_jail":
            handle_card_go_to_jail(player, card)

        case "keep_jail_card":
            handle_card_keep_jail_card(player, card)

        case "property_repairs":
            handle_card_property_repairs(player, card)

        case "move_to_field":
            handle_card_move_to_field(player, card, all_players)

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
            handle_go_to_jail(player)
        case "chance":
            handle_chance(player, field, all_players)
        case "community_chest":
            handle_community_chest(player, field, all_players)
        case "station":
            handle_station(player, field)
        case "company":
            handle_company(player, field, dice_total)
        case "start" | "jail" | "parking":
            print(
                f"{player['name']} stood on {field['name']}, there is no action on this field"
            )
