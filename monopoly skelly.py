# backend.py
from flask import Flask, request, jsonify
import random

app = Flask(__name__)

# -----------------------------
# GAME CLASSES
# -----------------------------

class Player:
    def __init__(self, name):
        self.name = name
        self.money = 1500
        self.position = 0
        self.properties = []
        self.bankrupt = False
        self.in_jail = False
        self.jail_turns = 0
        self.doubles_count = 0
        self.get_out_of_jail_cards = 0

    def move(self, steps, board_size):
        self.position = (self.position + steps) % board_size

    def adjust_money(self, amount):
        self.money += amount
        if self.money < 0:
            return False
        return True

    def declare_bankruptcy(self):
        self.bankrupt = True
        self.money = 0
        for prop in self.properties:
            prop.owner = None
        self.properties = []

    def go_to_jail(self, jail_position):
        self.position = jail_position
        self.in_jail = True
        self.jail_turns = 0
        self.doubles_count = 0


class Property:
    def __init__(self, name, cost, base_rent):
        self.name = name
        self.cost = cost
        self.base_rent = base_rent
        self.owner = None
        self.mortgaged = False

    def get_rent(self):
        return 0 if self.mortgaged else self.base_rent

    def buy(self, player):
        if self.owner is None and player.money >= self.cost:
            player.adjust_money(-self.cost)
            self.owner = player
            player.properties.append(self)
            return True
        return False

    def mortgage(self, player):
        if self.owner == player and not self.mortgaged:
            self.mortgaged = True
            player.adjust_money(self.cost // 2)
            return True
        return False

    def unmortgage(self, player):
        if self.owner == player and self.mortgaged:
            fee = int(self.cost * 0.6)
            if player.money >= fee:
                player.adjust_money(-fee)
                self.mortgaged = False
                return True
        return False


class Board:
    def __init__(self):
        self.spaces = [
            "GO",
            Property("Renzo House", 100, 10),
            "Community Chest",
            Property("Kyle Tower", 120, 12),
            "Income Tax",
            Property("Crisostomo Plaza", 200, 25),
            "Chance",
            Property("Macmac Pavilion", 140, 14),
            Property("Mike House", 160, 16),
            "Jail",
            Property("Leenor Estate", 200, 25),
            "Community Chest",
            Property("Malate", 100, 10),
            "Income Tax",
            Property("Bagong Pook", 120, 12),
            "Free Parking",
            Property("Dark Tower", 200, 25),
        ]

    def get_space(self, position):
        return self.spaces[position]


class Game:
    def __init__(self):
        self.players = []
        self.board = Board()
        self.turn_index = 0
        self.ended = False

        # Define card decks
        self.community_chest = [
            ("earn", 200, "Bank error in your favor. Collect 200."),
            ("pay", 50, "Doctor’s fees. Pay 50."),
            ("move", 0, "Advance to GO. Collect 200."),
            ("pay", 1000, "Post 'I am gae' in your FB account or pay 1000 to the bank.")
        ]
        self.chance = [
            ("earn", 100, "You won a crossword competition. Collect 100."),
            ("jail", None, "Go directly to Jail."),
            ("pay", 150, "Speeding fine. Pay 150."),
            ("pay", 5000, "Chat mo ngayon si Elizabeth, otherwise pay 5000 to the bank.")
        ]

    def add_player(self, name):
        self.players.append(Player(name))

    def current_player(self):
        return self.players[self.turn_index]

    def roll_dice(self):
        return random.randint(1, 6), random.randint(1, 6)

    def next_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.players)

    def check_game_end(self):
        active_players = [p for p in self.players if not p.bankrupt]
        if len(active_players) == 1:
            self.ended = True
            return active_players[0].name
        return None

    def draw_card(self, deck_type, player):
        if deck_type == "community":
            card = random.choice(self.community_chest)
        else:
            card = random.choice(self.chance)

        action, value, message = card

        if action == "earn":
            player.adjust_money(value)
        elif action == "pay":
            player.adjust_money(-value)
        elif action == "move":
            player.position = value
            if value == 0:  # GO
                player.adjust_money(200)
        elif action == "jail":
            jail_position = self.board.spaces.index("Jail")
            player.go_to_jail(jail_position)

        return message


# -----------------------------
# GAME INSTANCE
# -----------------------------
game = Game()


# -----------------------------
# FLASK ROUTES
# -----------------------------

@app.route("/start", methods=["POST"])
def start_game():
    data = request.json
    game.players = []
    for name in data.get("players", []):
        game.add_player(name)
    return jsonify({"message": "Game started!", "players": [p.name for p in game.players]})


@app.route("/roll", methods=["POST"])
def roll():
    player = game.current_player()
    dice = game.roll_dice()
    steps = sum(dice)
    result = {"player": player.name, "dice": dice}

    # Jail logic
    if player.in_jail:
        if dice[0] == dice[1]:  # rolled doubles → free
            player.in_jail = False
            result["action"] = f"{player.name} rolled doubles and got out of jail!"
            player.move(steps, len(game.board.spaces))
        else:
            player.jail_turns += 1
            result["action"] = f"{player.name} is still in jail (Turn {player.jail_turns})"
            game.next_turn()
            return jsonify(result)
    else:
        # Handle doubles outside jail
        if dice[0] == dice[1]:
            player.doubles_count += 1
            if player.doubles_count == 3:
                jail_position = game.board.spaces.index("Jail")
                player.go_to_jail(jail_position)
                result["action"] = f"{player.name} rolled doubles three times and is sent to jail!"
                game.next_turn()
                return jsonify(result)
        else:
            player.doubles_count = 0
        player.move(steps, len(game.board.spaces))

    # Resolve space
    space = game.board.get_space(player.position)
    result["new_position"] = player.position

    if isinstance(space, Property):
        if space.owner is None:
            result["action"] = f"Unowned property: {space.name} (Cost: {space.cost})"
        elif space.owner != player and not space.mortgaged:
            rent = space.get_rent()
            player.adjust_money(-rent)
            space.owner.adjust_money(rent)
            result["action"] = f"Paid rent of {rent} to {space.owner.name}"
    elif space == "Community Chest":
        desc = game.draw_card("community", player)
        result["action"] = f"Community Chest: {desc}"
    elif space == "Chance":
        desc = game.draw_card("chance", player)
        result["action"] = f"Chance: {desc}"
    elif space == "Jail":
        result["action"] = f"{player.name} is just visiting jail"
    else:
        result["action"] = f"Landed on {space}"

    # Check end game
    winner = game.check_game_end()
    if winner:
        result["game_over"] = True
        result["winner"] = winner

    game.next_turn()
    return jsonify(result)
