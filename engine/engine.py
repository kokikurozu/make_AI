from __future__ import annotations
import random
from typing import List

from engine.card import Card, CardType
from engine.actions import Action, ActionType
from engine.state import (
    GameState, PlayerState, CharacterOnField,
    PHASE_REFRESH, PHASE_DRAW, PHASE_DON,
    PHASE_MAIN, PHASE_ATTACK, PHASE_BLOCK,
    PHASE_COUNTER, PHASE_DAMAGE, PHASE_END,
)


class GameEngine:
    """
    ゲームの状態遷移を管理するエンジン。
    apply_action() は現在の state を変更して返す。
    MCTSで使う場合は state.copy() を先に呼ぶこと。
    """

    def apply_action(self, state: GameState, action: Action) -> GameState:
        """行動を適用して次の状態を返す"""
        if state.phase == PHASE_MAIN:
            self._apply_main(state, action)
        elif state.phase == PHASE_ATTACK:
            self._apply_attack(state, action)
        elif state.phase == PHASE_BLOCK:
            self._apply_block(state, action)
        elif state.phase == PHASE_COUNTER:
            self._apply_counter(state, action)
        return state

    # ------------------------------------------------------------------ #
    #  メインフェーズの処理                                                #
    # ------------------------------------------------------------------ #
    def _apply_main(self, state: GameState, action: Action):
        p = state.current()

        if action.action_type == ActionType.PLAY_CARD:
            card = p.hand.pop(action.hand_index)
            p.don_available -= card.cost
            char = CharacterOnField(
                card=card,
                summoning_sick=not card.has_rush  # 速攻なら召喚酔いなし
            )
            p.field.append(char)

        elif action.action_type == ActionType.ATTACH_DON:
            p.don_available -= action.don_count
            if action.attach_target == -1:
                p.leader.don_attached += action.don_count
            else:
                p.field[action.attach_target].don_attached += action.don_count

        elif action.action_type == ActionType.END_TURN:
            # メイン終了 → アタックフェーズへ
            state.phase = PHASE_ATTACK
            state.already_attacked = set()

    # ------------------------------------------------------------------ #
    #  アタックフェーズの処理                                              #
    # ------------------------------------------------------------------ #
    def _apply_attack(self, state: GameState, action: Action):
        if action.action_type == ActionType.END_TURN:
            # アタック終了 → ターン終了処理
            self._end_turn(state)
            return

        if action.action_type == ActionType.ATTACK:
            # 攻撃宣言を保留してブロックフェーズへ
            state.pending_attack = action
            state.phase = PHASE_BLOCK

            # 攻撃者をレスト
            p = state.current()
            if action.attacker_index == -1:
                p.leader.is_resting = True
            else:
                p.field[action.attacker_index].is_resting = True

    # ------------------------------------------------------------------ #
    #  ブロックフェーズの処理                                              #
    # ------------------------------------------------------------------ #
    def _apply_block(self, state: GameState, action: Action):
        atk_action = state.pending_attack
        attacker_power = self._get_attacker_power(state, atk_action)

        if action.action_type == ActionType.BLOCK:
            # ブロッカーをレスト状態にする
            opp = state.opp()
            blocker = opp.field[action.target_index]
            blocker.is_resting = True
            blocker_power = blocker.effective_power()

            if attacker_power > blocker_power:
                # ブロッカーをKO
                opp.field.pop(action.target_index)
                opp.trash.append(blocker.card)

        # ブロック or パスどちらでもカウンターフェーズへ
        state.counter_power = 0
        state.phase = PHASE_COUNTER

    # ------------------------------------------------------------------ #
    #  カウンターフェーズの処理                                            #
    # ------------------------------------------------------------------ #
    def _apply_counter(self, state: GameState, action: Action):
        atk_action = state.pending_attack
        attacker_power = self._get_attacker_power(state, atk_action)
        defender = state.opp()

        if action.action_type == ActionType.USE_COUNTER:
            # カードを手札から捨ててカウンター値を加算
            card = defender.hand.pop(action.hand_index)
            defender.trash.append(card)
            state.counter_power += card.counter
            # カウンターフェーズは複数枚使えるのでフェーズ継続

        elif action.action_type == ActionType.PASS_COUNTER:
            # カウンター終了 → ダメージ解決
            self._resolve_damage_with_counter(state, atk_action, attacker_power)
            state.counter_power = 0
            state.pending_attack = None
            state.phase = PHASE_ATTACK
            state.already_attacked.add(atk_action.attacker_index)
            self._check_winner(state)

    def _get_attacker_power(self, state: GameState, atk_action: Action) -> int:
        p = state.current()
        if atk_action.attacker_index == -1:
            return p.leader.effective_power()
        return p.field[atk_action.attacker_index].effective_power()

    # ------------------------------------------------------------------ #
    #  ダメージ解決（カウンター対応）                                      #
    # ------------------------------------------------------------------ #
    def _resolve_damage_with_counter(self, state: GameState, atk_action: Action, attacker_power: int):
        opp_idx = state.opponent()
        opp = state.players[opp_idx]

        if atk_action.target_index == -1:
            # リーダーへのアタック
            defender_power = opp.leader.effective_power() + state.counter_power
            if attacker_power > defender_power:
                # ダメージ：ライフを1枚手札に加える
                if len(opp.life) > 0:
                    life_card = opp.life.pop(0)
                    opp.hand.append(life_card)
                else:
                    # ライフ0でダメージ → 敗北
                    state.winner = state.current_player
        else:
            # キャラへのアタック
            target = opp.field[atk_action.target_index]
            target_power = target.effective_power() + state.counter_power
            if attacker_power > target_power:
                opp.field.pop(atk_action.target_index)
                opp.trash.append(target.card)

    def _resolve_damage(self, state: GameState, atk_action: Action, attacker_power: int):
        """後方互換のため残す（内部でカウンター0として呼ぶ）"""
        state.counter_power = 0
        self._resolve_damage_with_counter(state, atk_action, attacker_power)

    # ------------------------------------------------------------------ #
    #  ターン終了処理                                                      #
    # ------------------------------------------------------------------ #
    def _end_turn(self, state: GameState):
        # 現プレイヤーの召喚酔いを解除
        p = state.current()
        for char in p.field:
            char.summoning_sick = False

        # 手番交代
        state.current_player = state.opponent()
        state.turn += 1

        # 次プレイヤーのリフレッシュフェーズ
        self._refresh_phase(state)

    def _refresh_phase(self, state: GameState):
        """レスト状態のカードをアクティブに戻す"""
        p = state.current()
        p.leader.is_resting = False
        for char in p.field:
            char.is_resting = False

        # DONフェーズ（2枚追加、最大10枚）
        don_gain = min(2, p.don_deck)
        p.don_deck -= don_gain
        p.don_available += don_gain

        # ドローフェーズ（1枚ドロー）
        if len(p.deck) > 0:
            p.hand.append(p.deck.pop(0))

        state.phase = PHASE_MAIN

    # ------------------------------------------------------------------ #
    #  勝敗チェック                                                        #
    # ------------------------------------------------------------------ #
    def _check_winner(self, state: GameState):
        """
        勝敗判定。
        メインの判定は _resolve_damage_with_counter 内で実施済み：
          ライフ0 かつ リーダーへのダメージが通る → state.winner = 攻撃側
        ここでは安全のため再確認のみ行う。
        """
        if state.winner is not None:
            return


def create_initial_state(deck0: List[Card], leader0: Card,
                          deck1: List[Card], leader1: Card) -> GameState:
    """ゲームの初期状態を作成"""

    def make_player(deck: List[Card], leader: Card) -> PlayerState:
        shuffled = deck.copy()
        random.shuffle(shuffled)
        # 最初の5枚を手札に
        hand = shuffled[:5]
        remaining = shuffled[5:]
        # ライフは5枚
        life = remaining[:5]
        deck_cards = remaining[5:]
        return PlayerState(
            leader=CharacterOnField(card=leader, summoning_sick=False),
            life=life,
            hand=hand,
            deck=deck_cards,
            trash=[],
            field=[],
            don_deck=10,
            don_available=0,
        )

    p0 = make_player(deck0, leader0)
    p1 = make_player(deck1, leader1)

    # 先攻プレイヤーは最初のDONを1枚だけ（公式ルール）
    p0.don_available = 1
    p0.don_deck -= 1
    # 後攻は2枚
    p1.don_available = 2
    p1.don_deck -= 2

    return GameState(
        players=[p0, p1],
        current_player=0,
        turn=1,
        phase=PHASE_MAIN,
    )