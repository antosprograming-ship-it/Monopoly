import engine
import models
from board import board


def main():
    current_player = models.player1

    def play(player):
        roll_result = engine.roll_dice()
        print(f"Rolling the dice: {roll_result}")

        new_position = engine.move_player(player, roll_result)

        current_field = board[new_position]

        print(f"Position of {player['name']}: {current_field['name']} ")

        engine.handle_field_action(player, current_field)

        if player == models.player1:
            return models.player2
        else:
            return models.player1

    print("Rules: ")

    is_first_turn = True

    while True:
        if is_first_turn:
            user_input = input("Type (play) to start a Game! ")
            if user_input == "play":
                current_player = play(current_player)
                is_first_turn = False
        else:
            user_input = input("Type (c) to continue ")
            if user_input == "c":
                current_player = play(current_player)


if __name__ == "__main__":
    main()
