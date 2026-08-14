import random


def roll_dice():
    dice_one = random.randint(1, 6)
    dice_two = random.randint(1, 6)
    return dice_one + dice_two


def move_player(player, steps):
    BOARD_SIZE = 40
    player["position_index"] = (player["position_index"] + steps) % BOARD_SIZE
    return player["position_index"]


def handle_property(player, field):
    pass


def handle_tax(player, field):
    pass


def handle_go_to_jail(player):
    pass


def handle_chance(player, field):
    pass


def handle_community_chest(player, field):
    pass


def handle_field_action(player, field):
    field_type = field["type"]

    match field_type:
        case "property" | "station" | "company":
            handle_property(player, field)
        case "tax":
            handle_tax(player, field)
        case "go_to_jail":
            handle_go_to_jail(player)
        case "chance":
            handle_chance(player, field)
        case "community_chest":
            handle_community_chest(player, field)
        case _:
            pass
