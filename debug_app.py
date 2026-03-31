from flask import Flask, jsonify, request, send_from_directory
import random, os, json

from engine.card import Card, CardType, Color
from engine.state import GameState
from engine.engine import GameEngine, create_initial_state
from engine.actions import Action, ActionType
from engine.card_loader import load_deck

app = Flask(__name__, static_folder="debug_ui")
engine = GameEngine()
state: GameState = None


def serialize_card(card):
    if card is None:
        return None
    return {
        "id": card.card_id, "name": card.name,
        "cost": card.cost, "power": card.power,
        "type": card.card_type.value, "color": card.color.value,
        "counter": card.counter,
        "has_rush": card.has_rush, "has_blocker": card.has_blocker,
        "image_url": card.image_url,
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
    l0, d0 = load_deck("st01.json")
    l1, d1 = load_deck("st01.json")
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


@app.route("/images/<path:filename>")
def card_image(filename):
    """ローカルに保存した画像を返す"""
    return send_from_directory(os.path.join("data", "images"), filename)


@app.route("/")
def index():
    return send_from_directory("debug_ui", "index.html")


if __name__ == "__main__":
    print("デバッグUI: http://localhost:5000")
    app.run(debug=True, port=5000)