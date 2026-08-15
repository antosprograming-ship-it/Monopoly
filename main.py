import engine
import models
from board import board


def print_player_status(player):
    current_position = player["position_index"]
    current_field_name = board[current_position]["name"]

    print(f"\n=== PLAYER STATUS: {player['name']} ===")
    print(f" Position: {current_field_name} (Field: #{current_position})")
    print(f" Budget: ${player['budget']}")

    if player["properties"]:
        property_names = [p["name"] for p in player["properties"]]
        print(f" Properties ({len(property_names)}): {', '.join(property_names)}")
    else:
        print(" No any properties.")
    print("=" * 32 + "\n")


def play(player):
    roll_result = engine.roll_dice()
    print(f"Rolling the dice: {roll_result}")

    new_position = engine.move_player(player, roll_result)
    current_field = board[new_position]

    print(f" {player['name']} stood on: {current_field['name']} ")
    engine.handle_field_action(player, current_field)

    return models.player2 if player == models.player1 else models.player1


def main():
    current_player = models.player1
    is_first_turn = True
    print("Rules: \n")

    while True:
        prompt = (
            "Type (play) to start, or (check) to view status: "
            if is_first_turn
            else "Type (c) to roll dice, or (check) to view status: "
        )
        user_input = input(prompt).strip().lower()

        if user_input == "check":
            print_player_status(current_player)
        elif user_input in ["play", "c"]:
            current_player = play(current_player)
            is_first_turn = False
        else:
            expected = "'play' or 'check'" if is_first_turn else "'c' or 'check'"
            print(f"Invalid command! Type {expected}.")


if __name__ == "__main__":
    main()
