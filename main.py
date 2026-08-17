import sys

import engine
import models
from board import board

JAIL_FINE = 50

RULES_TEXT = """
=== COMMANDS / RULES ===
Type (play)       - to start game
Type (c)          - to roll dice and continue
Type (i)          - for your status
Type (com)        - for computer status
Type (rules)      - to display rules
Type (house)      - to buy a new house
Type (restart)    - to restart the game
Type (sell)       - to sell house(s) / hotel(s)
Type (mortgage)   - to mortgage property(s) | station(s) | company(s)
Type (unmortgage) - to unmortgage property(s) | station(s) | company(s)
========================
"""


def print_player_status(player):
    current_position = player["position_index"]
    current_field_name = board[current_position]["name"]

    print(f"=== PLAYER STATUS: {player['name']} ===")

    if player.get("is_in_debt", False):
        debt_val = abs(player["budget"])
        creditor_name = player["creditor"]["name"] if player.get("creditor") else "Bank"
        print(f"⚠️ STATUS: IN DEBT (-${debt_val}) | Owed to: {creditor_name}")

    print(f"Position: {current_field_name} (Field: #{current_position})")
    print(f"Budget: ${player['budget']}")
    print(f"Jail cards count: {player['jail_cards_count']}")
    if not player["in_jail"]:
        print("In Jail: No")
    else:
        print(f"In Jail: Yes (Turn: {player['jail_turns'] + 1}/3)")

    if player["properties"]:
        property_names = [
            f"{p['name']} [MORTGAGED]" if p.get("is_mortgaged", False) else p["name"]
            for p in player["properties"]
        ]
        print(f"Properties ({len(property_names)}): {', '.join(property_names)}")
    else:
        print("No properties owned.")
    print("=" * 32 + "\n")


def get_sellable_property(player):
    # Zwraca pierwszą napotkaną nieruchomość, którą można legalnie sprzedać
    for prop in player["properties"]:
        if engine.can_sell_house(prop):
            return prop
    return None


def get_mortgageable_property(player):
    # Zwraca pierwszą napotkaną nieruchomość, którą można legalnie zastawić
    for prop in player["properties"]:
        if prop.get("is_mortgaged", False):
            continue
        group = prop.get("group")
        if group and engine.group_has_houses(group):
            continue
        return prop
    return None


def handle_computer_debt_resolution(player):
    print(f"🤖 {player['name']} is automatically resolving debt...")

    # 1. Najpierw sprzedaje domki/hotele
    while player["is_in_debt"]:
        prop = get_sellable_property(player)
        if prop is None:
            break
        engine.sell_house(player, prop, models.bank)
        engine.check_and_flag_debt(player, creditor=player.get("creditor"))

    # 2. Jeśli to nie wystarczy, zastawia nieruchomości
    while player["is_in_debt"]:
        prop = get_mortgageable_property(player)
        if prop is None:
            break
        engine.mortgage_property(player, prop)
        engine.check_and_flag_debt(player, creditor=player.get("creditor"))

    # 3. Jeśli nadal jest w długu, jest bankrutem
    if player["is_in_debt"]:
        print(f"\n💀 {player['name']} cannot cover the debt and is BANKRUPT!")


def declare_bankruptcy(player, all_players):
    creditor, inherited_props = engine.execute_bankruptcy(
        player, all_players, models.bank
    )

    if creditor and inherited_props:
        handle_inherited_mortgages(creditor, inherited_props)

    # Odsetki zapłacone przez wierzyciela mogą utworzyć nowy dług.
    if creditor in all_players and creditor.get("is_in_debt"):
        handle_debt_menu(creditor, all_players)

    return "BANKRUPT"


def handle_debt_menu(player, all_players):
    # 1. KROK SZYBKIEGO BANKRUCTWA:
    if engine.get_player_liquidation_value(player) < 0:
        return declare_bankruptcy(player, all_players)

    # 2. PĘTLIA RATUNKOWA:
    # Jeśli wycena majątku >= 0, gracz MOŻE wyjść z długu, więc dajemy mu wybór
    debt_amount = abs(player["budget"])
    creditor_name = player["creditor"]["name"] if player["creditor"] else "Bank"

    print(
        f"\n🚨 {player['name']} MUST COVER DEBT OF ${debt_amount} (Owed to: {creditor_name})"
    )

    if player["name"] == "Computer":
        handle_computer_debt_resolution(player)
        if player["is_in_debt"]:
            return declare_bankruptcy(player, all_players)
        return "RESOLVED"

    while player["is_in_debt"]:
        print("\n=== DEBT RESOLUTION MENU ===")
        print("Type 'sell'     - to sell houses/hotels")
        print("Type 'mortgage' - to mortgage properties")

        try:
            choice = input("\nChoose action: ").strip().lower()
        except EOFError:
            print("\n❌ No more input available. Exiting game.")
            sys.exit(0)

        if choice == "sell":
            handle_sell_menu(player)
        elif choice == "mortgage":
            handle_mortgage_menu(player)
        else:
            print("❌ You must resolve your debt first! Choose 'sell' or 'mortgage'.")

        engine.check_and_flag_debt(player, creditor=player.get("creditor"))

    return "RESOLVED"


def handle_inherited_mortgages(creditor, inherited_props):
    if not inherited_props:
        return

    print(f"\n=== MORTGAGE RESOLUTION FOR {creditor['name'].upper()} ===")

    for prop in inherited_props:
        principal = prop["price"] // 2

        # Jeśli wierzyciel to AI (Komputer)
        if creditor["name"] == "Computer":
            # Komputer zdejmuje hipotekę od razu, jeśli zostanie mu bezpieczny bufor gotówki (np. $200)
            if creditor["budget"] >= principal + 200:
                creditor["budget"] -= principal
                prop["is_mortgaged"] = False
                print(
                    f"🤖 Computer decided to instantly unmortgage {prop['name']} for ${principal}."
                )
            else:
                print(f"🤖 Computer leaves {prop['name']} mortgaged.")
            continue

        # Jeśli wierzyciel to żywy gracz (Ty)
        while True:
            print(f"\n🏷️ You inherited {prop['name']} [MORTGAGED].")
            print(f"   You already paid the 10% tax.")
            print(
                f"   Do you want to pay the principal (${principal}) to unmortgage it NOW?"
            )
            print(
                f"   (If you wait, it will cost you principal + ANOTHER 10% later: ${engine.calculate_unmortgage_value(prop)})"
            )

            choice = (
                input(f"Unmortgage {prop['name']} for ${principal}? (y/n): ")
                .strip()
                .lower()
            )

            if choice == "y":
                if creditor["budget"] >= principal:
                    creditor["budget"] -= principal
                    prop["is_mortgaged"] = False
                    print(
                        f"✅ You unmortgaged {prop['name']}! Current budget: ${creditor['budget']}"
                    )
                    break
                else:
                    print(
                        f"❌ You only have ${creditor['budget']}. You cannot afford this now."
                    )
                    print(f"   {prop['name']} remains mortgaged.")
                    break
            elif choice == "n":
                print(f"   {prop['name']} remains mortgaged.")
                break
            else:
                print("❌ Invalid input. Type 'y' or 'n'.")


def handle_jail_turn(player, all_players):
    print(f"\n🔒 {player['name']} is in Jail! (Turn {player['jail_turns'] + 1}/3)")

    is_computer = player["name"] == "Computer"

    while True:
        print("=== JAIL MENU ===")
        print("1. Pay $50 fine to get out")
        if player["jail_cards_count"] > 0:
            print("2. Use 'Get Out of Jail Free' card")
        print("3. Roll dice for doubles")

        if is_computer:
            # AI zawsze używa karty, jeśli ją ma, w przeciwnym razie rzuca kostką.
            choice = "2" if player["jail_cards_count"] > 0 else "3"
            print(f"🤖 Computer chooses option {choice}.")
        else:
            options = "1, 2, 3" if player["jail_cards_count"] > 0 else "1, 3"
            choice = input(f"\nChoose option ({options}): ").strip()

        # OPCJA 1: Zapłata $50
        if choice == "1":
            if player["budget"] >= JAIL_FINE:
                player["budget"] -= JAIL_FINE
                player["in_jail"] = False
                player["jail_turns"] = 0
                print(f"✅ {player['name']} paid $50 and is now free from Jail!")
                # Po uwolnieniu gracz może wykonać normalny ruch
                return True
            else:
                print("❌ You don't have enough money ($50)!")

        # OPCJA 2: Użycie karty (jeśli gracz ją ma)
        elif choice == "2" and player["jail_cards_count"] > 0:
            player["jail_cards_count"] -= 1
            held = player["jail_cards_held"].pop(0)
            held["deck"].append(held["card"])
            player["in_jail"] = False
            player["jail_turns"] = 0
            print(f"🎟️ {player['name']} used a Jail card and is now free!")
            return True

        # OPCJA 3: Rzut kostkami na dublet
        elif choice == "3":
            d1, d2 = engine.roll_dice()
            print(f"🎲 Jail roll: {d1} and {d2} (Total: {d1 + d2})")

            if d1 == d2:
                player["in_jail"] = False
                player["jail_turns"] = 0
                print(f"⚡ DOUBLE! {player['name']} rolled doubles and escaped Jail!")

                # Ruch o wyrzuconą sumę (ale BEZ dodatkowego rzutu za dublet w więzieniu!)
                dice_total = d1 + d2
                new_position = engine.move_player(player, dice_total)
                current_field = board[new_position]
                print(
                    f"{player['name']} moved to: {current_field['name']} (Field: #{new_position})"
                )
                engine.handle_field_action(
                    player, current_field, dice_total, all_players
                )

                engine.check_and_flag_debt(player, creditor=None)

                if player["is_in_debt"]:
                    if handle_debt_menu(player, all_players) == "BANKRUPT":
                        return "BANKRUPT"

                return False  # Tura dobiegła końca
            else:
                print(f"❌ No double. {player['name']} stays in Jail.")
                player["jail_turns"] += 1

                # Zasada 3 tur: jeśli po 3 próbach nie wyrzucił dubletu, musi zapłacić $50
                if player["jail_turns"] >= 3:
                    print(
                        f"⚠️ {player['name']} spent 3 turns in Jail and must pay $50 fine!"
                    )
                    player["budget"] -= JAIL_FINE
                    player["in_jail"] = False
                    player["jail_turns"] = 0
                    print(f"💸 Fine paid. Budget: ${player['budget']}")

                    dice_total = d1 + d2
                    new_position = engine.move_player(player, dice_total)
                    current_field = board[new_position]
                    print(
                        f"{player['name']} moved to: {current_field['name']} (Field: #{new_position})"
                    )
                    engine.handle_field_action(
                        player, current_field, dice_total, all_players
                    )

                engine.check_and_flag_debt(player, creditor=None)

                if player["is_in_debt"]:
                    if handle_debt_menu(player, all_players) == "BANKRUPT":
                        return "BANKRUPT"

                return False  # Tura mija
        else:
            print("❌ Invalid choice, try again.")


def get_next_active_player(player, all_players):
    if not all_players:
        return None

    if player not in all_players:
        return all_players[0]

    current_index = all_players.index(player)
    return all_players[(current_index + 1) % len(all_players)]


def play(player, all_players):

    # 1. Obsługa tury w Więzieniu
    # JEŚLI GRACZ JEST W WIĘZIENIU -> Odpalamy menu więzienne
    if player["in_jail"]:
        jail_result = handle_jail_turn(player, all_players)
        if jail_result == "BANKRUPT":
            return get_next_active_player(player, all_players)
        if not jail_result:
            # Tura się kończy, przechodzimy do drugiego gracza
            return get_next_active_player(player, all_players)
        # Jeśli gracz właśnie zapłacił lub użył karty, przechodzimy poniżej do zwykłego rzutu!

    d1, d2 = engine.roll_dice()
    dice_total = d1 + d2
    is_double = d1 == d2

    print(f"\nRolling the dice: {d1} and {d2} (Total: {dice_total}) \n")

    # 2. Sprawdzanie serii dubletów
    if is_double:
        player["double_count"] += 1
        print(f"⚡ DOUBLE! ({player['double_count']}/3)")

        # ZASADA 3 DUBLETÓW Z RZĘDU
        if player["double_count"] == 3:
            print(f"🚨 3 DOUBLES IN A ROW! {player['name']} goes directly to Jail!")
            engine.send_to_jail(player)
            # Koniec tury – ruch przechodzi na przeciwnika
            return get_next_active_player(player, all_players)
    else:
        # Brak dubletu – zerujemy serię
        player["double_count"] = 0

    # 3. Standardowy ruch po planszy
    new_position = engine.move_player(player, dice_total)
    current_field = board[new_position]

    print(
        f"{player['name']} stood on: {current_field['name']} (Field: #{new_position})"
    )

    engine.handle_field_action(player, current_field, dice_total, all_players)

    if player["is_in_debt"]:
        if handle_debt_menu(player, all_players) == "BANKRUPT":
            return get_next_active_player(player, all_players)

    # 4. Przekazanie tury
    if is_double and not player["in_jail"]:
        return player  # Kolejny rzut tego samego gracza
    else:
        return get_next_active_player(player, all_players)


def handle_build_menu(player):
    # Pętla główna – pozwala wracać z wyboru ulicy do wyboru grupy kolorów
    while True:
        # 1. Pobieramy z silnika listę kolorów, na które gracz ma monopol
        monopolies = engine.get_player_monopolies(player)

        # 2. Jeśli brak monopolu, powiadamiamy i wychodzimy
        if not monopolies:
            print(
                "❌ You don't own any full color groups! Collect all properties of one color to build."
            )
            return

        # 3. Wybor grupy kolorów
        print("\n=== CHOOSE COLOR GROUP TO BUILD ON ===")
        for index, group_name in enumerate(monopolies, 1):
            print(f"{index}. {group_name.upper()}")

        group_choice = (
            input("\nSelect group number (or 'c' to cancel): ").strip().lower()
        )

        if group_choice == "c":
            return

        if group_choice.isdigit():
            group_index = int(group_choice)
            if 1 <= group_index <= len(monopolies):
                selected_group = monopolies[group_index - 1]
                print(f"✅ Selected group: {selected_group.upper()}")
            else:
                print("❌ Invalid number! Choose a number from the list.")
                continue
        else:
            print("❌ Invalid input! Please enter a valid number or 'c' to cancel.")
            continue

        # 4. Szukamy ulic należących do wybranego koloru
        group_properties = engine.get_group_properties(selected_group)

        # 5. Podmenu wyboru konkretnej ulicy do rozbudowy
        while True:
            print(f"\n=== PROPERTIES IN {selected_group.upper()} ===")
            for index, prop in enumerate(group_properties, 1):
                houses = prop.get("houses", 0)
                status = f"{houses} house(s)" if houses < 5 else "HOTEL (5)"
                mortgaged_tag = (
                    " [MORTGAGED]" if prop.get("is_mortgaged", False) else ""
                )
                print(
                    f"{index}. {prop['name']}{mortgaged_tag} | Status: {status} | Cost: ${prop['house_cost']}"
                )

            prop_choice = (
                input("\nSelect property number to build on (or type 'b' to go back): ")
                .strip()
                .lower()
            )

            if prop_choice == "b":
                break  # Przerywa podmenu ulic i wraca do pętli głównej (wyboru grupy)

            if prop_choice.isdigit():
                prop_index = int(prop_choice)
                # DOWÓD POPRAWKI: Używamy prop_index zamiast prop_choice
                if 1 <= prop_index <= len(group_properties):
                    selected_property = group_properties[prop_index - 1]
                    engine.build_house(player, selected_property, models.bank)
                else:
                    print("❌ Invalid number! Choose a number from the list.")
            else:
                print(
                    "❌ Invalid input! Please enter a valid number or 'b' to go back."
                )


def handle_sell_menu(player):
    while True:
        # 1. Pobieramy monopole i filtrujemy tylko te grupy, na których stoją budynki
        monopolies = engine.get_player_monopolies(player)
        sellable_groups = [
            group
            for group in monopolies
            if any(
                p.get("group") == group and p.get("houses", 0) > 0
                for p in player["properties"]
            )
        ]

        # 2. Jeśli brak jakichkolwiek budynków na sprzedaż, wychodzimy
        if not sellable_groups:
            print(f"❌ {player['name']} does not have any buildings to sell!")
            return

        # 3. Wyświetlamy TYLKO grupy posiadające budynki
        print("\n=== CHOOSE COLOR GROUP TO SELL ON ===")
        for index, group_name in enumerate(sellable_groups, 1):
            print(f"{index}. {group_name.upper()}")

        group_choice = (
            input("\nSelect group number (or 'c' to cancel): ").strip().lower()
        )

        if group_choice == "c":
            return

        if group_choice.isdigit():
            group_index = int(group_choice)
            if 1 <= group_index <= len(sellable_groups):
                selected_group = sellable_groups[group_index - 1]
                print(f"✅ Selected group: {selected_group.upper()}")
            else:
                print("❌ Invalid number! Choose a number from the list.")
                continue
        else:
            print("❌ Invalid input! Please enter a valid number or 'c' to cancel.")
            continue

        # 4. Szukamy ulic należących do wybranego koloru
        group_properties = engine.get_group_properties(selected_group)

        # 5. Podmenu wyboru konkretnej ulicy
        while True:
            print(f"\n=== PROPERTIES IN {selected_group.upper()} ===")
            for index, prop in enumerate(group_properties, 1):
                houses = prop.get("houses", 0)
                status = f"{houses} house(s)" if houses < 5 else "HOTEL (5)"
                refund = prop["house_cost"] // 2  # Bank oddaje 50% wartości budynku
                mortgaged_tag = (
                    " [MORTGAGED]" if prop.get("is_mortgaged", False) else ""
                )
                print(
                    f"{index}. {prop['name']}{mortgaged_tag} | Status: {status} | Sell price: ${refund}"
                )

            prop_choice = (
                input(
                    "\nSelect property number to sell from (or type 'b' to go back): "
                )
                .strip()
                .lower()
            )

            if prop_choice == "b":
                break

            if prop_choice.isdigit():
                prop_index = int(prop_choice)
                if 1 <= prop_index <= len(group_properties):
                    selected_property = group_properties[prop_index - 1]
                    engine.sell_house(player, selected_property, models.bank)
                else:
                    print("❌ Invalid number! Choose a number from the list.")
            else:
                print(
                    "❌ Invalid input! Please enter a valid number or 'b' to go back."
                )


def handle_mortgage_menu(player):
    while True:
        # 1. Wyciągamy nieruchomości, które NIE SĄ zastawione ORAZ NIE MAJĄ budynków w całej grupie
        eligible_properties = [
            pro
            for pro in player["properties"]
            if not pro.get("is_mortgaged", False)
            and not (pro.get("group") and engine.group_has_houses(pro.get("group")))
        ]

        # 2. Jeśli brak jakichkolwiek nieruchomości pod zastaw, wychodzimy
        if not eligible_properties:
            print(f"❌ {player['name']} has no properties available to mortgage!")
            return

        # 3. Wyświetlamy konkretne nieruchomości gotowe do zastawienia
        print("\n=== CHOOSE PROPERTY TO MORTGAGE ===")
        for index, prop in enumerate(eligible_properties, 1):
            mortgage_value = prop["price"] // 2
            group_label = prop.get("group", prop["type"]).upper()
            print(
                f"{index}. {prop['name']} ({group_label}) | Mortgage value: ${mortgage_value}"
            )

        choice = input("\nSelect property number (or 'c' to cancel): ").strip().lower()

        if choice == "c":
            return

        if choice.isdigit():
            prop_index = int(choice)
            if 1 <= prop_index <= len(eligible_properties):
                selected_property = eligible_properties[prop_index - 1]
                print(f"✅ Selected property: {selected_property['name']}")
                engine.mortgage_property(player, selected_property)
            else:
                print("❌ Invalid number! Choose a number from the list.")
        else:
            print("❌ Invalid input! Please enter a valid number or 'c' to cancel.")


def handle_unmortgage_menu(player):
    while True:
        # 1. Wyciągamy nieruchomości, które SĄ zastawione
        eligible_properties = [
            pro for pro in player["properties"] if pro.get("is_mortgaged", False)
        ]

        # 2. Jeśli brak jakichkolwiek zastawionych nieruchomości, wychodzimy
        if not eligible_properties:
            print(f"❌ {player['name']} has no any mortgaged properties!")
            return

        # 3. Wyświetlamy konkretne nieruchomości gotowe do wykupienia
        print("\n=== CHOOSE PROPERTY TO UNMORTGAGE ===")
        for index, prop in enumerate(eligible_properties, 1):
            unmortgage_value = engine.calculate_unmortgage_value(prop)
            group_label = prop.get("group", prop["type"]).upper()
            print(
                f"{index}. {prop['name']} ({group_label}) | Unmortgage value: ${unmortgage_value}"
            )

        choice = input("\nSelect property number (or 'c' to cancel): ").strip().lower()

        if choice == "c":
            return

        if choice.isdigit():
            prop_index = int(choice)
            if 1 <= prop_index <= len(eligible_properties):
                selected_property = eligible_properties[prop_index - 1]
                print(f"✅ Selected property: {selected_property['name']}")
                engine.unmortgage_property(player, selected_property)
            else:
                print("❌ Invalid number! Choose a number from the list.")
        else:
            print("❌ Invalid input! Please enter a valid number or 'c' to cancel.")


def main():
    current_player = models.player1
    active_players = [models.player1, models.player2]
    is_first_turn = True

    print(RULES_TEXT)

    while True:
        print()
        user_input = input("Type command: ").strip().lower()
        print()

        if user_input == "i":
            print_player_status(models.player1)

        elif user_input == "com":
            print_player_status(models.player2)

        elif user_input == "rules":
            print(RULES_TEXT)

        elif is_first_turn and user_input == "play":
            current_player = play(current_player, active_players)
            is_first_turn = False
            if len(active_players) <= 1:
                if active_players:
                    print(f"🏆 {active_players[0]['name']} wins the game!")
                else:
                    print("🏦 All players went bankrupt. The Bank wins!")
                return

        elif not is_first_turn and user_input == "c":
            current_player = play(current_player, active_players)
            if len(active_players) <= 1:
                if active_players:
                    print(f"🏆 {active_players[0]['name']} wins the game!")
                else:
                    print("🏦 All players went bankrupt. The Bank wins!")
                return

        elif user_input == "house":
            handle_build_menu(current_player)

        elif user_input == "restart":
            engine.reset_game(models.player1, models.player2, models.bank)
            current_player = models.player1
            active_players = [models.player1, models.player2]
            is_first_turn = True
            print("🔄 Game has been completely restarted!\n")
            print(RULES_TEXT)

        elif user_input == "sell":
            handle_sell_menu(current_player)

        elif user_input == "mortgage":
            handle_mortgage_menu(current_player)

        elif user_input == "unmortgage":
            handle_unmortgage_menu(current_player)

        else:
            expected = "'play', 'i' or 'com'" if is_first_turn else "'c', 'i' or 'com'"
            print(f"Invalid command! Type {expected}.")


if __name__ == "__main__":
    # Windows domyślnie uruchamia konsolę w kodowaniu innym niż UTF-8 (np. cp1250),
    # co powoduje UnicodeEncodeError przy pierwszym print() z emoji.
    sys.stdout.reconfigure(encoding="utf-8")
    main()
