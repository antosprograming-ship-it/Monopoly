import engine
import models
from board import board

RULES_TEXT = """
=== COMMANDS / RULES ===
Type (play)  - to start game
Type (c)     - to roll dice and continue
Type (i)     - for your status
Type (com)   - for computer status
Type (rules) - to display rules
Type (house) - to buy a new house
========================
"""


def print_player_status(player):
    current_position = player["position_index"]
    current_field_name = board[current_position]["name"]

    print(f"=== PLAYER STATUS: {player['name']} ===")
    print(f"Position: {current_field_name} (Field: #{current_position})")
    print(f"Budget: ${player['budget']}")
    print(f"Jail cards count: {player['jail_cards_count']}")

    if player["properties"]:
        property_names = [p["name"] for p in player["properties"]]
        print(f"Properties ({len(property_names)}): {', '.join(property_names)}")
    else:
        print("No properties owned.")
    print("=" * 32 + "\n")


def play(player):
    d1, d2 = engine.roll_dice()
    dice_total = d1 + d2
    is_double = d1 == d2

    all_players = [models.player1, models.player2]

    print(f"\n Rolling the dice: {d1} and {d2} (Total: {dice_total}) \n")

    if is_double:
        print(f"⚡ DOUBLE! {player['name']} has extra roll!")

    new_position = engine.move_player(player, dice_total)
    current_field = board[new_position]

    print(
        f"{player['name']} stood on: {current_field['name']} (Field: #{new_position})"
    )

    engine.handle_field_action(player, current_field, dice_total, all_players)

    if is_double:
        return player
    else:
        return models.player2 if player == models.player1 else models.player1


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
        group_properties = [
            field
            for field in board
            if field.get("type") == "property" and field.get("group") == selected_group
        ]

        # 5. Podmenu wyboru konkretnej ulicy do rozbudowy
        while True:
            print(f"\n=== PROPERTIES IN {selected_group.upper()} ===")
            for index, prop in enumerate(group_properties, 1):
                houses = prop.get("houses", 0)
                status = f"{houses} house(s)" if houses < 5 else "HOTEL (5)"
                print(
                    f"{index}. {prop['name']} | Status: {status} | Cost: ${prop['house_cost']}"
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


def main():
    current_player = models.player1
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
            current_player = play(current_player)
            is_first_turn = False

        elif not is_first_turn and user_input == "c":
            current_player = play(current_player)

        elif user_input == "house":
            handle_build_menu(current_player)

        else:
            expected = "'play', 'i' or 'com'" if is_first_turn else "'c', 'i' or 'com'"
            print(f"Invalid command! Type {expected}.")


if __name__ == "__main__":
    main()
