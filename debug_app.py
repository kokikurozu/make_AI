from flask import Flask, jsonify, request, send_from_directory
import random, os, json

from engine.card import Card, CardType, Color
from engine.state import GameState
from engine.engine import GameEngine, create_initial_state
from engine.actions import Action, ActionType

app = Flask(__name__, static_folder="debug_ui")
engine = GameEngine()
state: GameState = None


def make_test_deck(color: Color):
    leader = Card("L001", "ルフィ（リーダー）", CardType.LEADER, color, 0, 5000)
    deck = []
    for i in range(50):
        cost = (i % 5) + 1
        deck.append(Card(
            f"C{i:03d}", f"キャラ{i}", CardType.CHARACTER, color,
            cost, cost * 1000,
            counter=1000 if i % 3 == 0 else None,
            has_rush=(i % 10 == 0),
            has_blocker=(i % 7 == 0),
        ))
    return leader, deck


def serialize_card(card):
    if card is None:
        return None
    return {
        "id": card.card_id, "name": card.name,
        "cost": card.cost, "power": card.power,
        "type": card.card_type.value, "color": card.color.value,
        "counter": card.counter,
        "has_rush": card.has_rush, "has_blocker": card.has_blocker,
    }


def serialize_char(char):
    return {
        **serialize_card(char.card),
        "don_attached": char.don_attached,
        "is_resting": char.is_resting,
        "summoning_sick": char.summoning_sick,
        "effective_power": char.effective_power(),
    }


def serialize_state(state: GameState):
    if state is None:
        return {"error": "ゲームが開始されていません"}
    players = []
    for i, p in enumerate(state.players):
        players.append({
            "index": i,
            "leader": serialize_char(p.leader),
            "life_count": len(p.life),
            "hand": [serialize_card(c) for c in p.hand],
            "hand_count": len(p.hand),
            "field": [serialize_char(c) for c in p.field],
            "deck_count": len(p.deck),
            "trash_count": len(p.trash),
            "don_available": p.don_available,
            "don_deck": p.don_deck,
        })
    actions = []
    for i, a in enumerate(state.get_legal_actions()):
        actions.append({"index": i, "label": str(a), "type": a.action_type.value})
    return {
        "turn": state.turn,
        "phase": state.phase,
        "current_player": state.current_player,
        "winner": state.winner,
        "players": players,
        "legal_actions": actions,
        "pending_attack": str(state.pending_attack) if state.pending_attack else None,
    }


@app.route("/api/new_game", methods=["POST"])
def new_game():
    global state
    l0, d0 = make_test_deck(Color.RED)
    l1, d1 = make_test_deck(Color.BLUE)
    state = create_initial_state(d0, l0, d1, l1)
    return jsonify(serialize_state(state))


@app.route("/api/state")
def get_state():
    return jsonify(serialize_state(state))


@app.route("/api/action/<int:action_index>", methods=["POST"])
def apply_action(action_index):
    global state
    if state is None or state.is_terminal():
        return jsonify({"error": "ゲームが終了または未開始"}), 400
    actions = state.get_legal_actions()
    if action_index >= len(actions):
        return jsonify({"error": "無効なアクション番号"}), 400
    engine.apply_action(state, actions[action_index])
    return jsonify(serialize_state(state))


@app.route("/api/random_step", methods=["POST"])
def random_step():
    global state
    if state is None or state.is_terminal():
        return jsonify({"error": "ゲーム終了または未開始"}), 400
    actions = state.get_legal_actions()
    if actions:
        engine.apply_action(state, random.choice(actions))
    return jsonify(serialize_state(state))


@app.route("/")
def index():
    return send_from_directory("debug_ui", "index.html")


if __name__ == "__main__":
    print("デバッグUI: http://localhost:5000")
    app.run(debug=True, port=5000)