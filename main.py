import sys

import engine
from game_state import create_game

JAIL_FINE = 50

RULES_TEXT = """
=== COMMANDS / RULES ===
Type (play)             - to start game
Type (c)                - to roll dice and continue
Type (i)                - for your status
Type (status <nick>)    - for another player's status
Type (rules)            - to display rules
Type (house)            - to buy a new house
Type (restart)          - to restart the game
Type (sell)             - to sell house(s) / hotel(s)
Type (mortgage)         - to mortgage property(s) | station(s) | company(s)
Type (unmortgage)       - to unmortgage property(s) | station(s) | company(s)
========================
"""

MIN_BOTS = 1
MAX_BOTS = 5


def prompt_for_nickname():
    while True:
        nickname = input("Choose your nick: ").strip()
        if nickname:
            return nickname
        print("❌ Nick cannot be empty.")


def prompt_for_bot_count():
    while True:
        raw = input(
            f"How many bots do you want to play against ({MIN_BOTS}-{MAX_BOTS})? "
        ).strip()
        if raw.isdigit() and MIN_BOTS <= int(raw) <= MAX_BOTS:
            return int(raw)
        print(f"❌ Enter a number from {MIN_BOTS} to {MAX_BOTS}.")


def print_player_status(game, player):
    current_position = player.position_index
    current_field_name = game.board[current_position].name

    print(f"=== PLAYER STATUS: {player.name} ===")

    if player.is_in_debt:
        debt_val = abs(player.budget)
        creditor_name = player.creditor.name if player.creditor else "Bank"
        print(f"⚠️ STATUS: IN DEBT (-${debt_val}) | Owed to: {creditor_name}")

    print(f"Position: {current_field_name} (Field: #{current_position})")
    print(f"Budget: ${player.budget}")
    print(f"Jail cards count: {player.jail_cards_count}")
    if not player.in_jail:
        print("In Jail: No")
    else:
        print(f"In Jail: Yes (Turn: {player.jail_turns + 1}/3)")

    if player.properties:
        property_names = [
            f"{p.name} [MORTGAGED]" if p.is_mortgaged else p.name
            for p in player.properties
        ]
        print(f"Properties ({len(property_names)}): {', '.join(property_names)}")
    else:
        print("No properties owned.")
    print("=" * 32 + "\n")


def get_sellable_property(game, player):
    # Zwraca pierwszą napotkaną nieruchomość, którą można legalnie sprzedać.
    # Hotel pomijamy, jeśli Bank nie ma 4 domków potrzebnych do jego zejścia
    # (inaczej sell_house odrzuciłby sprzedaż i pętla AI utknęłaby w miejscu).
    for prop in player.properties:
        if not engine.can_sell_house(game, prop):
            continue
        if prop.houses == 5 and game.bank["houses"] < 4:
            continue
        return prop
    return None


def get_mortgageable_property(game, player):
    # Zwraca pierwszą napotkaną nieruchomość, którą można legalnie zastawić
    for prop in player.properties:
        if prop.is_mortgaged:
            continue
        group = prop.group
        if group and engine.group_has_houses(game, group):
            continue
        return prop
    return None


def handle_computer_debt_resolution(game, player):
    print(f"🤖 {player.name} is automatically resolving debt...")

    # 1. Najpierw sprzedaje domki/hotele
    while player.is_in_debt:
        prop = get_sellable_property(game, player)
        if prop is None:
            break
        engine.sell_house(game, player, prop, game.bank)
        engine.check_and_flag_debt(game, player, creditor=player.creditor)

    # 2. Jeśli to nie wystarczy, zastawia nieruchomości
    while player.is_in_debt:
        prop = get_mortgageable_property(game, player)
        if prop is None:
            break
        engine.mortgage_property(game, player, prop)
        engine.check_and_flag_debt(game, player, creditor=player.creditor)

    # 3. Jeśli nadal jest w długu, jest bankrutem
    if player.is_in_debt:
        print(f"\n💀 {player.name} cannot cover the debt and is BANKRUPT!")


def declare_bankruptcy(game, player, all_players):
    creditor, inherited_props = engine.execute_bankruptcy(
        game, player, all_players, game.bank
    )

    if creditor and inherited_props:
        handle_inherited_mortgages(creditor, inherited_props)

    # Odsetki zapłacone przez wierzyciela mogą utworzyć nowy dług. Wynik tego
    # wywołania celowo nie jest przekazywany dalej: niezależnie od tego, czy
    # wierzyciel również zbankrutuje, all_players jest już poprawnie
    # zaktualizowane (execute_bankruptcy usuwa go z listy), a to ta lista —
    # nie zwracana wartość — jest źródłem prawdy dla zakończenia tury/gry.
    if creditor in all_players and creditor.is_in_debt:
        handle_debt_menu(game, creditor, all_players)

    return "BANKRUPT"


def handle_debt_menu(game, player, all_players):
    # 1. KROK SZYBKIEGO BANKRUCTWA:
    if engine.get_player_liquidation_value(player) < 0:
        return declare_bankruptcy(game, player, all_players)

    # 2. PĘTLIA RATUNKOWA:
    # Jeśli wycena majątku >= 0, gracz MOŻE wyjść z długu, więc dajemy mu wybór
    debt_amount = abs(player.budget)
    creditor_name = player.creditor.name if player.creditor else "Bank"

    print(
        f"\n🚨 {player.name} MUST COVER DEBT OF ${debt_amount} (Owed to: {creditor_name})"
    )

    if player.is_ai:
        handle_computer_debt_resolution(game, player)
        if player.is_in_debt:
            return declare_bankruptcy(game, player, all_players)
        return "RESOLVED"

    while player.is_in_debt:
        print("\n=== DEBT RESOLUTION MENU ===")
        print("Type 'sell'     - to sell houses/hotels")
        print("Type 'mortgage' - to mortgage properties")

        try:
            choice = input("\nChoose action: ").strip().lower()
        except EOFError:
            print("\n❌ No more input available. Exiting game.")
            sys.exit(0)

        if choice == "sell":
            handle_sell_menu(game, player)
        elif choice == "mortgage":
            handle_mortgage_menu(game, player)
        else:
            print("❌ You must resolve your debt first! Choose 'sell' or 'mortgage'.")

        engine.check_and_flag_debt(game, player, creditor=player.creditor)

    return "RESOLVED"


def handle_inherited_mortgages(creditor, inherited_props):
    if not inherited_props:
        return

    print(f"\n=== MORTGAGE RESOLUTION FOR {creditor.name.upper()} ===")

    for prop in inherited_props:
        principal = prop.price // 2

        # Jeśli wierzyciel to AI (Komputer)
        if creditor.is_ai:
            # Komputer zdejmuje hipotekę od razu, jeśli zostanie mu bezpieczny bufor gotówki (np. $200)
            if creditor.budget >= principal + 200:
                creditor.budget -= principal
                prop.is_mortgaged = False
                print(
                    f"🤖 Computer decided to instantly unmortgage {prop.name} for ${principal}."
                )
            else:
                print(f"🤖 Computer leaves {prop.name} mortgaged.")
            continue

        # Jeśli wierzyciel to żywy gracz (Ty)
        while True:
            print(f"\n🏷️ You inherited {prop.name} [MORTGAGED].")
            print(f"   You already paid the 10% tax.")
            print(
                f"   Do you want to pay the principal (${principal}) to unmortgage it NOW?"
            )
            print(
                f"   (If you wait, it will cost you principal + ANOTHER 10% later: ${engine.calculate_unmortgage_value(prop)})"
            )

            choice = (
                input(f"Unmortgage {prop.name} for ${principal}? (y/n): ")
                .strip()
                .lower()
            )

            if choice == "y":
                if creditor.budget >= principal:
                    creditor.budget -= principal
                    prop.is_mortgaged = False
                    print(
                        f"✅ You unmortgaged {prop.name}! Current budget: ${creditor.budget}"
                    )
                    break
                else:
                    print(
                        f"❌ You only have ${creditor.budget}. You cannot afford this now."
                    )
                    print(f"   {prop.name} remains mortgaged.")
                    break
            elif choice == "n":
                print(f"   {prop.name} remains mortgaged.")
                break
            else:
                print("❌ Invalid input. Type 'y' or 'n'.")


def handle_jail_turn(game, player, all_players):
    print(f"\n🔒 {player.name} is in Jail! (Turn {player.jail_turns + 1}/3)")

    is_computer = player.is_ai

    while True:
        print("=== JAIL MENU ===")
        print("1. Pay $50 fine to get out")
        if player.jail_cards_count > 0:
            print("2. Use 'Get Out of Jail Free' card")
        print("3. Roll dice for doubles")

        if is_computer:
            # AI zawsze używa karty, jeśli ją ma, w przeciwnym razie rzuca kostką.
            choice = "2" if player.jail_cards_count > 0 else "3"
            print(f"🤖 Computer chooses option {choice}.")
        else:
            options = "1, 2, 3" if player.jail_cards_count > 0 else "1, 3"
            choice = input(f"\nChoose option ({options}): ").strip()

        # OPCJA 1: Zapłata $50
        if choice == "1":
            if player.budget >= JAIL_FINE:
                player.budget -= JAIL_FINE
                player.in_jail = False
                player.jail_turns = 0
                print(f"✅ {player.name} paid $50 and is now free from Jail!")
                # Po uwolnieniu gracz może wykonać normalny ruch
                return True
            else:
                print("❌ You don't have enough money ($50)!")

        # OPCJA 2: Użycie karty (jeśli gracz ją ma)
        elif choice == "2" and player.jail_cards_count > 0:
            player.jail_cards_count -= 1
            held = player.jail_cards_held.pop(0)
            held["deck"].append(held["card"])
            player.in_jail = False
            player.jail_turns = 0
            print(f"🎟️ {player.name} used a Jail card and is now free!")
            return True

        # OPCJA 3: Rzut kostkami na dublet
        elif choice == "3":
            d1, d2 = engine.roll_dice()
            print(f"🎲 Jail roll: {d1} and {d2} (Total: {d1 + d2})")

            if d1 == d2:
                player.in_jail = False
                player.jail_turns = 0
                print(f"⚡ DOUBLE! {player.name} rolled doubles and escaped Jail!")

                # Ruch o wyrzuconą sumę (ale BEZ dodatkowego rzutu za dublet w więzieniu!)
                dice_total = d1 + d2
                new_position = engine.move_player(game, player, dice_total)
                current_field = game.board[new_position]
                print(
                    f"{player.name} moved to: {current_field.name} (Field: #{new_position})"
                )
                engine.handle_field_action(
                    game, player, current_field, dice_total, all_players
                )

                engine.check_and_flag_debt(game, player, creditor=None)

                if player.is_in_debt:
                    if handle_debt_menu(game, player, all_players) == "BANKRUPT":
                        return "BANKRUPT"

                return False  # Tura dobiegła końca
            else:
                print(f"❌ No double. {player.name} stays in Jail.")
                player.jail_turns += 1

                # Zasada 3 tur: jeśli po 3 próbach nie wyrzucił dubletu, musi zapłacić $50
                if player.jail_turns >= 3:
                    print(
                        f"⚠️ {player.name} spent 3 turns in Jail and must pay $50 fine!"
                    )
                    player.budget -= JAIL_FINE
                    player.in_jail = False
                    player.jail_turns = 0
                    print(f"💸 Fine paid. Budget: ${player.budget}")

                    dice_total = d1 + d2
                    new_position = engine.move_player(game, player, dice_total)
                    current_field = game.board[new_position]
                    print(
                        f"{player.name} moved to: {current_field.name} (Field: #{new_position})"
                    )
                    engine.handle_field_action(
                        game, player, current_field, dice_total, all_players
                    )

                engine.check_and_flag_debt(game, player, creditor=None)

                if player.is_in_debt:
                    if handle_debt_menu(game, player, all_players) == "BANKRUPT":
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


def play(game, player, all_players):

    # 1. Obsługa tury w Więzieniu
    # JEŚLI GRACZ JEST W WIĘZIENIU -> Odpalamy menu więzienne
    if player.in_jail:
        jail_result = handle_jail_turn(game, player, all_players)
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
        player.double_count += 1
        print(f"⚡ DOUBLE! ({player.double_count}/3)")

        # ZASADA 3 DUBLETÓW Z RZĘDU
        if player.double_count == 3:
            print(f"🚨 3 DOUBLES IN A ROW! {player.name} goes directly to Jail!")
            engine.send_to_jail(game, player)
            # Koniec tury – ruch przechodzi na przeciwnika
            return get_next_active_player(player, all_players)
    else:
        # Brak dubletu – zerujemy serię
        player.double_count = 0

    # 3. Standardowy ruch po planszy
    new_position = engine.move_player(game, player, dice_total)
    current_field = game.board[new_position]

    print(
        f"{player.name} stood on: {current_field.name} (Field: #{new_position})"
    )

    engine.handle_field_action(game, player, current_field, dice_total, all_players)

    if player.is_in_debt:
        if handle_debt_menu(game, player, all_players) == "BANKRUPT":
            return get_next_active_player(player, all_players)

    # 4. Przekazanie tury
    if is_double and not player.in_jail:
        return player  # Kolejny rzut tego samego gracza
    else:
        return get_next_active_player(player, all_players)


def choose_from_menu(items, format_item, prompt, cancel_word, cancel_action="cancel", header=None):
    # Wspólna pętla menu: drukuje ponumerowaną listę, czyta wybór, waliduje go
    # i zwraca wybraną pozycję (albo None po anulowaniu/cofnięciu).
    while True:
        if header:
            print(header)
        for index, item in enumerate(items, 1):
            print(f"{index}. {format_item(item)}")

        choice = input(prompt).strip().lower()

        if choice == cancel_word:
            return None

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]
            print("❌ Invalid number! Choose a number from the list.")
        else:
            print(
                f"❌ Invalid input! Please enter a valid number or '{cancel_word}' to {cancel_action}."
            )


def _build_property_line(prop):
    houses = prop.houses
    status = f"{houses} house(s)" if houses < 5 else "HOTEL (5)"
    mortgaged_tag = " [MORTGAGED]" if prop.is_mortgaged else ""
    return f"{prop.name}{mortgaged_tag} | Status: {status} | Cost: ${prop.house_cost}"


def _sell_property_line(prop):
    houses = prop.houses
    status = f"{houses} house(s)" if houses < 5 else "HOTEL (5)"
    refund = prop.house_cost // 2  # Bank oddaje 50% wartości budynku
    mortgaged_tag = " [MORTGAGED]" if prop.is_mortgaged else ""
    return f"{prop.name}{mortgaged_tag} | Status: {status} | Sell price: ${refund}"


def handle_build_menu(game, player):
    # Pętla główna – pozwala wracać z wyboru ulicy do wyboru grupy kolorów
    while True:
        # 1. Pobieramy z silnika listę kolorów, na które gracz ma monopol
        monopolies = engine.get_player_monopolies(game, player)

        # 2. Jeśli brak monopolu, powiadamiamy i wychodzimy
        if not monopolies:
            print(
                "❌ You don't own any full color groups! Collect all properties of one color to build."
            )
            return

        # 3. Wybor grupy kolorów
        selected_group = choose_from_menu(
            monopolies,
            lambda group_name: group_name.upper(),
            "\nSelect group number (or 'c' to cancel): ",
            "c",
            header="\n=== CHOOSE COLOR GROUP TO BUILD ON ===",
        )

        if selected_group is None:
            return

        print(f"✅ Selected group: {selected_group.upper()}")

        # 4. Szukamy ulic należących do wybranego koloru
        group_properties = engine.get_group_properties(game, selected_group)

        # 5. Podmenu wyboru konkretnej ulicy do rozbudowy
        while True:
            selected_property = choose_from_menu(
                group_properties,
                _build_property_line,
                "\nSelect property number to build on (or type 'b' to go back): ",
                "b",
                "go back",
                header=f"\n=== PROPERTIES IN {selected_group.upper()} ===",
            )

            if selected_property is None:
                break  # Przerywa podmenu ulic i wraca do pętli głównej (wyboru grupy)

            engine.build_house(game, player, selected_property, game.bank)


def handle_sell_menu(game, player):
    while True:
        # 1. Pobieramy monopole i filtrujemy tylko te grupy, na których stoją budynki
        monopolies = engine.get_player_monopolies(game, player)
        sellable_groups = [
            group
            for group in monopolies
            if any(
                p.group == group and p.houses > 0 for p in player.properties
            )
        ]

        # 2. Jeśli brak jakichkolwiek budynków na sprzedaż, wychodzimy
        if not sellable_groups:
            print(f"❌ {player.name} does not have any buildings to sell!")
            return

        # 3. Wyświetlamy TYLKO grupy posiadające budynki
        selected_group = choose_from_menu(
            sellable_groups,
            lambda group_name: group_name.upper(),
            "\nSelect group number (or 'c' to cancel): ",
            "c",
            header="\n=== CHOOSE COLOR GROUP TO SELL ON ===",
        )

        if selected_group is None:
            return

        print(f"✅ Selected group: {selected_group.upper()}")

        # 4. Szukamy ulic należących do wybranego koloru
        group_properties = engine.get_group_properties(game, selected_group)

        # 5. Podmenu wyboru konkretnej ulicy
        while True:
            selected_property = choose_from_menu(
                group_properties,
                _sell_property_line,
                "\nSelect property number to sell from (or type 'b' to go back): ",
                "b",
                "go back",
                header=f"\n=== PROPERTIES IN {selected_group.upper()} ===",
            )

            if selected_property is None:
                break

            engine.sell_house(game, player, selected_property, game.bank)


def _mortgage_property_line(prop):
    mortgage_value = prop.price // 2
    group_label = (prop.group or prop.type).upper()
    return f"{prop.name} ({group_label}) | Mortgage value: ${mortgage_value}"


def _unmortgage_property_line(prop):
    unmortgage_value = engine.calculate_unmortgage_value(prop)
    group_label = (prop.group or prop.type).upper()
    return f"{prop.name} ({group_label}) | Unmortgage value: ${unmortgage_value}"


def handle_mortgage_menu(game, player):
    while True:
        # 1. Wyciągamy nieruchomości, które NIE SĄ zastawione ORAZ NIE MAJĄ budynków w całej grupie
        eligible_properties = [
            pro
            for pro in player.properties
            if not pro.is_mortgaged
            and not (pro.group and engine.group_has_houses(game, pro.group))
        ]

        # 2. Jeśli brak jakichkolwiek nieruchomości pod zastaw, wychodzimy
        if not eligible_properties:
            print(f"❌ {player.name} has no properties available to mortgage!")
            return

        # 3. Wyświetlamy konkretne nieruchomości gotowe do zastawienia
        selected_property = choose_from_menu(
            eligible_properties,
            _mortgage_property_line,
            "\nSelect property number (or 'c' to cancel): ",
            "c",
            header="\n=== CHOOSE PROPERTY TO MORTGAGE ===",
        )
        if selected_property is None:
            return

        print(f"✅ Selected property: {selected_property.name}")
        engine.mortgage_property(game, player, selected_property)


def handle_unmortgage_menu(game, player):
    while True:
        # 1. Wyciągamy nieruchomości, które SĄ zastawione
        eligible_properties = [pro for pro in player.properties if pro.is_mortgaged]

        # 2. Jeśli brak jakichkolwiek zastawionych nieruchomości, wychodzimy
        if not eligible_properties:
            print(f"❌ {player.name} has no any mortgaged properties!")
            return

        # 3. Wyświetlamy konkretne nieruchomości gotowe do wykupienia
        selected_property = choose_from_menu(
            eligible_properties,
            _unmortgage_property_line,
            "\nSelect property number (or 'c' to cancel): ",
            "c",
            header="\n=== CHOOSE PROPERTY TO UNMORTGAGE ===",
        )
        if selected_property is None:
            return

        print(f"✅ Selected property: {selected_property.name}")
        engine.unmortgage_property(game, player, selected_property)


def _report_game_over_if_finished(active_players):
    # Generyczne dla N graczy: gra kończy się, gdy zostaje 1 lub 0 aktywnych.
    if len(active_players) > 1:
        return False
    if active_players:
        print(f"🏆 {active_players[0].name} wins the game!")
    else:
        print("🏦 All players went bankrupt. The Bank wins!")
    return True


def find_player_by_name(game, name):
    return next((p for p in game.players if p.name.lower() == name.lower()), None)


def main():
    nickname = prompt_for_nickname()
    bot_count = prompt_for_bot_count()
    game = create_game(player_name=nickname, bot_count=bot_count)
    current_player = game.players[0]
    active_players = game.players
    is_first_turn = True

    print(RULES_TEXT)

    while True:
        print()
        user_input = input("Type command: ").strip().lower()
        print()

        if user_input == "i":
            print_player_status(game, game.players[0])

        elif user_input.startswith("status "):
            target_name = user_input[len("status ") :].strip()
            target = find_player_by_name(game, target_name)
            if target:
                print_player_status(game, target)
            else:
                print(f"❌ No player named '{target_name}'.")

        elif user_input == "rules":
            print(RULES_TEXT)

        elif is_first_turn and user_input == "play":
            current_player = play(game, current_player, active_players)
            is_first_turn = False
            if _report_game_over_if_finished(active_players):
                return

        elif not is_first_turn and user_input == "c":
            current_player = play(game, current_player, active_players)
            if _report_game_over_if_finished(active_players):
                return

        elif user_input == "house":
            handle_build_menu(game, current_player)

        elif user_input == "restart":
            game = create_game(player_name=nickname, bot_count=bot_count)
            current_player = game.players[0]
            active_players = game.players
            is_first_turn = True
            print("🔄 Game has been completely restarted!\n")
            print(RULES_TEXT)

        elif user_input == "sell":
            handle_sell_menu(game, current_player)

        elif user_input == "mortgage":
            handle_mortgage_menu(game, current_player)

        elif user_input == "unmortgage":
            handle_unmortgage_menu(game, current_player)

        else:
            expected = (
                "'play', 'i' or 'status <nick>'"
                if is_first_turn
                else "'c', 'i' or 'status <nick>'"
            )
            print(f"Invalid command! Type {expected}.")


if __name__ == "__main__":
    # Windows domyślnie uruchamia konsolę w kodowaniu innym niż UTF-8 (np. cp1250),
    # co powoduje UnicodeEncodeError przy pierwszym print() z emoji.
    sys.stdout.reconfigure(encoding="utf-8")
    main()
