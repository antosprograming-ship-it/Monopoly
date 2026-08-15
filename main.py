import engine
import models
from board import board

RULES_TEXT = """
=== COMMANDS / RULES ===
Type (play)  - to start game
Type (c)     - to roll dice and continue
Type (I)   - for your status
Type (com)   - for computer status
Type (rules) - to display rules
========================
"""


def print_player_status(player):
    current_position = player["position_index"]
    current_field_name = board[current_position]["name"]

    print(f"=== PLAYER STATUS: {player['name']} ===")
    print(f"Position: {current_field_name} (Field: #{current_position})")
    print(f"Budget: ${player['budget']}")

    if player["properties"]:
        property_names = [p["name"] for p in player["properties"]]
        print(f"Properties ({len(property_names)}): {', '.join(property_names)}")
    else:
        print("No properties owned.")
    print("=" * 32 + "\n")


def play(player):
    d1, d2 = engine.roll_dice()
    total_steps = d1 + d2
    is_double = d1 == d2

    print(f"\n Rolling the dice: {d1} and {d2} (Total: {total_steps}) \n")

    if is_double:
        print(f"⚡ DOUBLE! {player['name']} has extra roll!")

    new_position = engine.move_player(player, total_steps)
    current_field = board[new_position]

    print(
        f"{player['name']} stood on: {current_field['name']} (Field: #{new_position})"
    )
    engine.handle_field_action(player, current_field, total_steps)

    if is_double:
        return player
    else:
        return models.player2 if player == models.player1 else models.player1


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

        else:
            expected = "'play', 'i' or 'com'" if is_first_turn else "'c', 'i' or 'com'"
            print(f"Invalid command! Type {expected}.")


if __name__ == "__main__":
    main()
