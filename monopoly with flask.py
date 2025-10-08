# ---------------------------------------------
# backend.py
# Monopoly Game Backend (Extended Version)
# ---------------------------------------------
# Flask server that simulates Monopoly-style gameplay
# Supports: Jail, Houses, Hotels, Trading, Mortgage, Reset, Chance & Community Chest
# ---------------------------------------------

from flask import Flask, request, jsonify
import random

app = Flask(__name__)

# ---------------------------------------------
# GAME CLASSES
# ---------------------------------------------

class Player:
    def __init__(self, name):
        self.name = name
        self.money = 1500
        self.position = 0
        self.properties = []
        self.bankrupt = False
        self.in_jail = False           # Jail status
        self.jail_turns = 0            # Number of turns in jail
        self.doubles_count = 0         # Doubles rolled consecutively
        self.get_out_of_jail_cards = 0 # Get Out of Jail Free cards

    def move(self, steps, board_size):
        self.position = (self.position + steps) % board_size

    def adjust_money(self, amount):
        self.money += amount
        return self.money >= 0

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
    def __init__(self, name, cost, base_rent, rent_levels):
        self.name = name
        self.cost = cost
        self.base_rent = base_rent
        self.rent_levels = rent_levels
        self.owner = None
        self.mortgaged = False
        self.houses = 0
        self.hotel = False

    def get_rent(self):
        if self.mortgaged:
            return 0
        if self.hotel:
            return self.rent_levels[-1]
        return self.rent_levels[self.houses]

    def buy(self, player):
        if self.owner is None and player.money >= self.cost:
            player.adjust_money(-self.cost)
            self.owner = player
            player.properties.append(self)
            return True
        return False

    def build_house(self, player):
        if self.owner == player and not self.mortgaged and self.houses < 4 and not self.hotel:
            cost = int(self.cost * 0.5)
            if player.money >= cost:
                player.adjust_money(-cost)
                self.houses += 1
                return True
        return False

    def build_hotel(self, player):
        if self.owner == player and not self.mortgaged and self.houses == 4 and not self.hotel:
            cost = int(self.cost * 0.75)
            if player.money >= cost:
                player.adjust_money(-cost)
                self.hotel = True
                self.houses = 0
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
            Property("Renzo House", 100, 50, [10, 50, 150, 450, 625, 750]),
            "Community Chest",
            Property("Kyle Tower", 120, 50, [12, 60, 180, 500, 700, 900]),
            "Income Tax",
            Property("Crisostomo Plaza", 200, 100, [25, 100, 300, 750, 925, 1100]),
            "Chance",
            Property("Macmac Pavilion", 140, 70, [14, 70, 200, 550, 750, 950]),
            Property("Mike House", 160, 80, [16, 80, 220, 600, 800, 1000]),
            "Jail",
            Property("Leenor Estate", 200, 100, [25, 100, 300, 750, 925, 1100]),
            "Community Chest",
            Property("Malate", 100, 50, [10, 50, 150, 450, 625, 750]),
            "Income Tax",
            Property("Bagong Pook", 120, 50, [12, 60, 180, 500, 700, 900]),
            "Free Parking",
            Property("Dark Tower", 200, 100, [25, 100, 300, 750, 925, 1100]),
        ]

    def get_space(self, position):
        return self.spaces[position]


class Game:
    def __init__(self):
        self.players = []
        self.board = Board()
        self.turn_index = 0
        self.ended = False

    def add_player(self, name):
        self.players.append(Player(name))

    def current_player(self):
        if not self.players:
            return None
        return self.players[self.turn_index]

    def roll_dice(self):
        return random.randint(1, 6), random.randint(1, 6)

    def next_turn(self):
        if not self.players:
            return
        self.turn_index = (self.turn_index + 1) % len(self.players)

        # Skip bankrupt players automatically
        for _ in range(len(self.players)):
            if not self.players[self.turn_index].bankrupt:
                break
            self.turn_index = (self.turn_index + 1) % len(self.players)

    def check_game_end(self):
        active = [p for p in self.players if not p.bankrupt]
        if len(active) == 1:
            self.ended = True
            return active[0].name
        return None

    def reset(self):
        self.__init__()


# ---------------------------------------------
# GAME INSTANCE
# ---------------------------------------------
game = Game()

# ---------------------------------------------
# RANDOM CARDS
# ---------------------------------------------
CHANCE_CARDS = [
    {"text": "Advance to GO", "type": "move", "position": 0},
    {"text": "Go to Jail", "type": "jail"},
    {"text": "Bank error in your favor, collect $200", "type": "money", "amount": 200},
    {"text": "Doctor's fees, pay $50", "type": "money", "amount": -50},
]

COMMUNITY_CHEST_CARDS = [
    {"text": "You inherit $100", "type": "money", "amount": 100},
    {"text": "Pay hospital fees of $100", "type": "money", "amount": -100},
    {"text": "Get Out of Jail Free card", "type": "card"},
    {"text": "Go back 3 spaces", "type": "move_relative", "steps": -3},
]


# ---------------------------------------------
# HELPER: CARD EFFECTS
# ---------------------------------------------
def apply_card_effect(player, card, result):
    if card["type"] == "move":
        player.position = card.get("position", player.position)
        result["action"] = f"{player.name} moves to position {player.position}."
    elif card["type"] == "jail":
        jail_pos = game.board.spaces.index("Jail")
        player.go_to_jail(jail_pos)
        result["action"] = f"{player.name} is sent to jail!"
    elif card["type"] == "money":
        player.adjust_money(card["amount"])
        result["action"] = f"{player.name} {'receives' if card['amount']>0 else 'pays'} ${abs(card['amount'])}."
    elif card["type"] == "card":
        player.get_out_of_jail_cards += 1
        result["action"] = f"{player.name} receives a Get Out of Jail Free card."
    elif card["type"] == "move_relative":
        player.move(card["steps"], len(game.board.spaces))
        result["action"] = f"{player.name} moves {card['steps']} spaces."


# ---------------------------------------------
# FLASK ROUTES
# ---------------------------------------------

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
    if not player:
        return jsonify({"message": "No players in game."}), 400

    dice = game.roll_dice()
    steps = sum(dice)
    result = {"player": player.name, "dice": dice}

    # Jail logic
    if player.in_jail:
        if dice[0] == dice[1]:
            player.in_jail = False
            result["action"] = f"{player.name} rolled doubles and got out of jail!"
            player.move(steps, len(game.board.spaces))
        else:
            player.jail_turns += 1
            result["action"] = f"{player.name} is still in jail (Turn {player.jail_turns})"
            game.next_turn()
            return jsonify(result)
    else:
        # Doubles logic outside jail
        if dice[0] == dice[1]:
            player.doubles_count += 1
            if player.doubles_count == 3:
                jail_pos = game.board.spaces.index("Jail")
                player.go_to_jail(jail_pos)
                result["action"] = f"{player.name} rolled doubles thrice and is sent to jail!"
                game.next_turn()
                return jsonify(result)
        else:
            player.doubles_count = 0
        player.move(steps, len(game.board.spaces))

    space = game.board.get_space(player.position)
    result["new_position"] = player.position

    # Resolve space actions
    if isinstance(space, Property):
        if space.owner is None:
            result["action"] = f"Unowned property: {space.name} (Cost: {space.cost})"
        elif space.owner != player and not space.mortgaged:
            rent = space.get_rent()
            player.adjust_money(-rent)
            space.owner.adjust_money(rent)
            result["action"] = f"Paid rent of ${rent} to {space.owner.name}"
    elif space == "Income Tax":
        player.adjust_money(-200)
        result["action"] = f"{player.name} paid $200 in taxes."
    elif space == "Chance":
        card = random.choice(CHANCE_CARDS)
        result["card"] = card["text"]
        apply_card_effect(player, card, result)
    elif space == "Community Chest":
        card = random.choice(COMMUNITY_CHEST_CARDS)
        result["card"] = card["text"]
        apply_card_effect(player, card, result)
    elif space == "Jail":
        result["action"] = f"{player.name} is just visiting jail"
    else:
        result["action"] = f"Landed on {space}"

    # End game check
    winner = game.check_game_end()
    if winner:
        result["game_over"] = True
        result["winner"] = winner

    game.next_turn()
    return jsonify(result)


@app.route("/state", methods=["GET"])
def state():
    data = [
        {
            "name": p.name,
            "money": p.money,
            "position": p.position,
            "properties": [prop.name for prop in p.properties],
            "bankrupt": p.bankrupt,
            "in_jail": p.in_jail,
            "houses": sum(prop.houses for prop in p.properties),
            "hotels": sum(1 for prop in p.properties if prop.hotel),
        }
        for p in game.players
    ]
    return jsonify({"players": data, "game_over": game.ended})


@app.route("/buy", methods=["POST"])
def buy():
    player = game.current_player()
    space = game.board.get_space(player.position)
    if isinstance(space, Property) and space.buy(player):
        return jsonify({"message": f"{player.name} bought {space.name}"})
    return jsonify({"message": "Cannot buy this space"})


@app.route("/build_house", methods=["POST"])
def build_house():
    player = game.current_player()
    name = request.json.get("property")
    for prop in player.properties:
        if prop.name == name and prop.build_house(player):
            return jsonify({"message": f"Built a house on {prop.name}"})
    return jsonify({"message": "Failed to build house"})


@app.route("/build_hotel", methods=["POST"])
def build_hotel():
    player = game.current_player()
    name = request.json.get("property")
    for prop in player.properties:
        if prop.name == name and prop.build_hotel(player):
            return jsonify({"message": f"Built a hotel on {prop.name}"})
    return jsonify({"message": "Failed to build hotel"})


@app.route("/trade", methods=["POST"])
def trade():
    data = request.json
    from_p = next((p for p in game.players if p.name == data["from"]), None)
    to_p = next((p for p in game.players if p.name == data["to"]), None)
    if not from_p or not to_p:
        return jsonify({"message": "Invalid players"}), 400

    offer_money = data.get("offer", {}).get("money", 0)
    prop_name = data.get("request", {}).get("property")

    if offer_money > 0 and from_p.money >= offer_money:
        from_p.adjust_money(-offer_money)
        to_p.adjust_money(offer_money)

    for prop in from_p.properties:
        if prop.name == prop_name:
            from_p.properties.remove(prop)
            to_p.properties.append(prop)
            prop.owner = to_p

    return jsonify({"message": f"{from_p.name} traded with {to_p.name}"})


@app.route("/mortgage", methods=["POST"])
def mortgage():
    player = game.current_player()
    name = request.json.get("property")
    for prop in player.properties:
        if prop.name == name and prop.mortgage(player):
            return jsonify({"message": f"{player.name} mortgaged {prop.name}"})
    return jsonify({"message": "Mortgage failed"})


@app.route("/unmortgage", methods=["POST"])
def unmortgage():
    player = game.current_player()
    name = request.json.get("property")
    for prop in player.properties:
        if prop.name == name and prop.unmortgage(player):
            return jsonify({"message": f"{player.name} unmortgaged {prop.name}"})
    return jsonify({"message": "Unmortgage failed"})


@app.route("/bankrupt", methods=["POST"])
def bankrupt():
    player = game.current_player()
    player.declare_bankruptcy()
    return jsonify({"message": f"{player.name} is bankrupt"})


@app.route("/forfeit", methods=["POST"])
def forfeit():
    player = game.current_player()
    player.declare_bankruptcy()
    return jsonify({"message": f"{player.name} forfeited the game"})


@app.route("/use_jail_card", methods=["POST"])
def use_jail_card():
    player = game.current_player()
    if player.in_jail and player.get_out_of_jail_cards > 0:
        player.in_jail = False
        player.get_out_of_jail_cards -= 1
        return jsonify({"message": f"{player.name} used a Get Out of Jail Free card"})
    return jsonify({"message": "No card available or not in jail"})


@app.route("/reset", methods=["POST"])
def reset():
    game.reset()
    return jsonify({"message": "Game has been reset."})


# ---------------------------------------------
# RUN SERVER
# ---------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
