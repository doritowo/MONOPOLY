# 🎲 Monopoly Game Backend

A simple Flask-based backend inspired by the classic Monopoly board game.  
This backend handles all the game logic such as rolling dice, buying properties, paying rent, jail mechanics, and declaring bankruptcy.

---

## 🚀 Features
- Add and manage multiple players
- Property ownership, buying, and mortgaging
- Dice rolls with doubles and jail logic
- Turn-based system with automatic switching
- Bankrupt and forfeit handling
- JSON API for frontend integration

---

## 🧩 API Endpoints

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/start` | POST | Start a new game with player names |
| `/roll` | POST | Roll dice for the current player |
| `/state` | GET | Get the full game state |
| `/buy` | POST | Buy a property if available |
| `/mortgage` | POST | Mortgage one of your properties |
| `/unmortgage` | POST | Unmortgage a previously mortgaged property |
| `/bankrupt` | POST | Declare bankruptcy |
| `/forfeit` | POST | Forfeit the game |
| `/use_jail_card` | POST | Use a Get Out of Jail Free card |

---

## ⚙️ How to Run Locally

```bash
# 1. Clone this repository
git clone https://github.com/YOUR_USERNAME/monopoly-backend.git
cd monopoly-backend

# 2. (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python backend.py
