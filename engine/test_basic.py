import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random
from engine.card import Card, CardType, Color
from engine.state import GameState
from engine.engine import GameEngine, create_initial_state
from engine.actions import ActionType


def make_test_deck(color: Color) -> tuple:
    """テスト用デッキを作成"""
    leader = Card(
        card_id="L001", name="ルフィ（リーダー）",
        card_type=CardType.LEADER, color=color,
        cost=0, power=5000
    )
    deck = []
    for i in range(50):
        cost = (i % 5) + 1
        power = cost * 1000
        card = Card(
            card_id=f"C{i:03d}", name=f"キャラ{i}",
            card_type=CardType.CHARACTER, color=color,
            cost=cost, power=power,
            counter=1000 if i % 3 == 0 else None,
            has_rush=(i % 10 == 0),
            has_blocker=(i % 7 == 0),
        )
        deck.append(card)
    return leader, deck


def test_initial_state():
    """初期状態のテスト"""
    leader0, deck0 = make_test_deck(Color.RED)
    leader1, deck1 = make_test_deck(Color.BLUE)
    state = create_initial_state(deck0, leader0, deck1, leader1)

    assert len(state.players) == 2
    assert len(state.players[0].hand) == 5, f"先攻手札: {len(state.players[0].hand)}"
    assert len(state.players[1].hand) == 5, f"後攻手札: {len(state.players[1].hand)}"
    assert len(state.players[0].life) == 5
    assert len(state.players[1].life) == 5
    assert state.players[0].don_available == 1
    assert state.players[1].don_available == 2
    print("✓ test_initial_state passed")


def test_legal_actions_main():
    """メインフェーズの合法手テスト"""
    leader0, deck0 = make_test_deck(Color.RED)
    leader1, deck1 = make_test_deck(Color.BLUE)
    state = create_initial_state(deck0, leader0, deck1, leader1)

    actions = state.get_legal_actions()
    assert len(actions) > 0, "合法手が0件"

    action_types = {a.action_type for a in actions}
    assert ActionType.END_TURN in action_types, "EndTurnがない"

    print(f"✓ test_legal_actions_main passed ({len(actions)} actions)")


def test_play_card():
    """カードを出すテスト"""
    leader0, deck0 = make_test_deck(Color.RED)
    leader1, deck1 = make_test_deck(Color.BLUE)
    state = create_initial_state(deck0, leader0, deck1, leader1)
    engine = GameEngine()

    # cost=1のカードを手から探す
    p = state.current()
    play_actions = [a for a in state.get_legal_actions()
                    if a.action_type == ActionType.PLAY_CARD]

    if play_actions:
        before_field = len(p.field)
        before_hand = len(p.hand)
        engine.apply_action(state, play_actions[0])
        assert len(p.field) == before_field + 1, "場に出ていない"
        assert len(p.hand) == before_hand - 1, "手札が減っていない"
        print(f"✓ test_play_card passed (field: {len(p.field)}枚)")
    else:
        print("⚠ test_play_card skipped (no playable cards with available DON)")


def test_random_game():
    """ランダムエージェント同士でゲームを1回まわすテスト"""
    leader0, deck0 = make_test_deck(Color.RED)
    leader1, deck1 = make_test_deck(Color.BLUE)
    state = create_initial_state(deck0, leader0, deck1, leader1)
    engine = GameEngine()

    max_steps = 500
    steps = 0
    while not state.is_terminal() and steps < max_steps:
        actions = state.get_legal_actions()
        if not actions:
            break
        action = random.choice(actions)
        engine.apply_action(state, action)
        steps += 1

    print(f"✓ test_random_game passed ({steps} steps, winner={state.winner})")


def test_copy_state():
    """状態コピーのテスト（MCTSに必須）"""
    leader0, deck0 = make_test_deck(Color.RED)
    leader1, deck1 = make_test_deck(Color.BLUE)
    state = create_initial_state(deck0, leader0, deck1, leader1)

    copied = state.copy()
    engine = GameEngine()

    # コピーを変更してもオリジナルに影響しないことを確認
    original_hand_count = len(state.current().hand)
    actions = copied.get_legal_actions()
    play_actions = [a for a in actions if a.action_type == ActionType.PLAY_CARD]
    if play_actions:
        engine.apply_action(copied, play_actions[0])

    assert len(state.current().hand) == original_hand_count, "コピーがオリジナルに影響している！"
    print("✓ test_copy_state passed")


if __name__ == "__main__":
    print("=== ワンピカAI エンジンテスト ===\n")
    test_initial_state()
    test_legal_actions_main()
    test_play_card()
    test_copy_state()
    test_random_game()
    print("\n全テスト完了!")