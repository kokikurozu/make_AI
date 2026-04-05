"""
parse_all_effects.py で生成した構造化JSONをもとに
実際のゲーム効果を適用するモジュール。
"""
from __future__ import annotations
import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.state import GameState, CharacterOnField

EFFECTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "effects")

# 解析済み効果のキャッシュ
_effect_cache: dict = {}


def _load_effects(set_id: str) -> dict:
    """data/effects/{set_id}_effects.json を読み込む"""
    key = set_id.lower().replace("-", "")
    if key in _effect_cache:
        return _effect_cache[key]
    path = os.path.join(EFFECTS_DIR, f"{key}_effects.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _effect_cache[key] = data
    return data


def get_card_effects(card_id: str) -> list:
    """カードIDから効果リストを取得"""
    set_id = card_id.split("-")[0]  # ST01-001 → ST01
    effects_data = _load_effects(set_id)
    parsed = effects_data.get(card_id, {})
    return parsed.get("effects", [])


def execute_trigger(trigger: str, state: "GameState",
                    card_id: str, player_idx: int,
                    char_on_field: "CharacterOnField | None" = None):
    """
    指定トリガーの効果を実行する。
    trigger: "on_play" | "on_attack" | "activate_main" | "trigger"
    player_idx: 効果を使うプレイヤーのindex
    """
    effects = get_card_effects(card_id)
    for effect in effects:
        if effect.get("trigger") != trigger:
            continue

        condition = effect.get("condition", {})
        if not _check_condition(condition, state, player_idx, char_on_field):
            continue

        for action in effect.get("actions", []):
            _execute_action(action, state, player_idx, char_on_field)


def _check_condition(condition: dict, state: "GameState",
                     player_idx: int, char_on_field) -> bool:
    """条件チェック"""
    ctype = condition.get("type", "none")
    if ctype == "none":
        return True
    if ctype == "don_attached":
        required = condition.get("value", 0)
        if char_on_field:
            return char_on_field.don_attached >= required
        # リーダーの場合
        return state.players[player_idx].leader.don_attached >= required
    return True


def _execute_action(action: dict, state: "GameState",
                    player_idx: int, char_on_field):
    """アクション実行"""
    atype = action.get("type", "none")
    p = state.players[player_idx]
    opp = state.players[1 - player_idx]

    if atype == "none":
        pass

    elif atype == "draw":
        count = action.get("count", 1)
        for _ in range(count):
            if p.deck:
                p.hand.append(p.deck.pop(0))

    elif atype == "add_life":
        count = action.get("count", 1)
        for _ in range(count):
            if p.deck:
                p.life.insert(0, p.deck.pop(0))

    elif atype == "add_don":
        count = action.get("count", 1)
        gain = min(count, p.don_deck)
        p.don_deck -= gain
        p.don_available += gain

    elif atype == "give_rush":
        if char_on_field:
            char_on_field.summoning_sick = False

    elif atype == "rest_opponent_character":
        target = action.get("target", "any")
        if target == "any" and opp.field:
            # 最初のアクティブキャラをレスト（AIが選択する場合は別途対応）
            for char in opp.field:
                if not char.is_resting:
                    char.is_resting = True
                    break

    elif atype == "ko_opponent_character":
        target = action.get("target", "cost_le")
        value = action.get("value", 0)
        if target == "cost_le":
            for i, char in enumerate(opp.field):
                if char.card.cost <= value:
                    opp.trash.append(opp.field.pop(i).card)
                    break

    elif atype == "power_boost":
        # パワーブーストは一時的なもの → 現状はフラグで管理（将来対応）
        pass

    elif atype == "blocker_disable":
        # ブロッカー封じ → state にフラグを立てる（将来対応）
        pass

    elif atype == "attach_don_from_rest":
        # レストDONをキャラに付与（リーダー効果）→ UIから選択式で対応予定
        pass

    elif atype == "play_from_hand":
        # トリガー効果でカードを登場させる → 将来対応
        pass