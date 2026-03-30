from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import List, Optional, Set

from engine.card import Card, CardType
from engine.actions import Action, ActionType


@dataclass
class CharacterOnField:
    """場に出ているキャラ"""
    card: Card
    don_attached: int = 0     # 付与されたDON枚数
    is_resting: bool = False  # レスト状態（攻撃済み）
    summoning_sick: bool = True  # 召喚酔い（出したターンは攻撃不可、速攻除く）

    def effective_power(self) -> int:
        return self.card.power + self.don_attached * 1000

    def copy(self) -> "CharacterOnField":
        return copy.copy(self)


@dataclass
class PlayerState:
    leader: CharacterOnField
    life: List[Card]
    hand: List[Card]
    deck: List[Card]
    trash: List[Card]
    field: List[CharacterOnField]  # 場のキャラ（最大5体）
    don_deck: int = 10             # DONデッキ残枚数
    don_available: int = 0         # 未使用のDON

    def effective_leader_power(self) -> int:
        return self.leader.effective_power()

    def copy(self) -> "PlayerState":
        return copy.deepcopy(self)


# フェーズ定義
PHASE_REFRESH  = "refresh"   # リフレッシュ（レスト解除・DON追加）
PHASE_DRAW     = "draw"      # ドロー
PHASE_DON      = "don"       # DONフェーズ（2枚追加）
PHASE_MAIN     = "main"      # メインフェーズ（カード使用・DON付与）
PHASE_ATTACK   = "attack"    # アタックフェーズ
PHASE_BLOCK    = "block"     # ブロックフェーズ（相手のターン）
PHASE_DAMAGE   = "damage"    # ダメージ解決
PHASE_END      = "end"       # ターン終了


@dataclass
class GameState:
    players: List[PlayerState]       # [0]=先攻, [1]=後攻
    current_player: int = 0          # 現在の手番プレイヤー
    turn: int = 1
    phase: str = PHASE_REFRESH
    winner: Optional[int] = None

    # アタックフェーズ管理
    pending_attack: Optional[Action] = None   # 解決待ちのアタック
    already_attacked: Set[int] = field(default_factory=set)  # 攻撃済みindex集合（-1=リーダー）

    def opponent(self) -> int:
        return 1 - self.current_player

    def current(self) -> PlayerState:
        return self.players[self.current_player]

    def opp(self) -> PlayerState:
        return self.players[self.opponent()]

    def copy(self) -> "GameState":
        """MCTSで局面をコピーする際に使用"""
        new = copy.deepcopy(self)
        return new

    def is_terminal(self) -> bool:
        return self.winner is not None

    def get_legal_actions(self) -> List[Action]:
        """現局面で合法な全行動を列挙（AIの核心）"""
        if self.is_terminal():
            return []

        if self.phase == PHASE_MAIN:
            return self._legal_main_actions()
        elif self.phase == PHASE_ATTACK:
            return self._legal_attack_actions()
        elif self.phase == PHASE_BLOCK:
            return self._legal_block_actions()
        return []

    # ------------------------------------------------------------------ #
    #  メインフェーズの合法手                                              #
    # ------------------------------------------------------------------ #
    def _legal_main_actions(self) -> List[Action]:
        actions = []
        p = self.current()

        # 1. 手札からキャラクターを出す
        for i, card in enumerate(p.hand):
            if card.card_type == CardType.CHARACTER:
                if p.don_available >= card.cost:
                    actions.append(Action(
                        action_type=ActionType.PLAY_CARD,
                        hand_index=i
                    ))

        # 2. DONをリーダーにつける（1枚ずつ）
        if p.don_available > 0:
            actions.append(Action(
                action_type=ActionType.ATTACH_DON,
                attach_target=-1,  # -1 = リーダー
                don_count=1
            ))
            # 場のキャラにつける
            for i in range(len(p.field)):
                actions.append(Action(
                    action_type=ActionType.ATTACH_DON,
                    attach_target=i,
                    don_count=1
                ))

        # 3. ターン終了（常に可能）
        actions.append(Action(action_type=ActionType.END_TURN))

        return actions

    # ------------------------------------------------------------------ #
    #  アタックフェーズの合法手                                            #
    # ------------------------------------------------------------------ #
    def _legal_attack_actions(self) -> List[Action]:
        actions = []
        p = self.current()
        opp = self.opp()

        # アタック可能なキャラを列挙
        attackers = []

        # リーダーは毎ターン1回攻撃可能
        if -1 not in self.already_attacked and not p.leader.is_resting:
            attackers.append(-1)

        # 場のキャラ（召喚酔いなし、かつ未攻撃）
        for i, char in enumerate(p.field):
            if i not in self.already_attacked and not char.is_resting:
                if not char.summoning_sick or char.card.has_rush:
                    attackers.append(i)

        # 各アタッカーの攻撃先を列挙
        for attacker_idx in attackers:
            # 相手リーダーへの攻撃
            actions.append(Action(
                action_type=ActionType.ATTACK,
                attacker_index=attacker_idx,
                target_index=-1
            ))
            # 相手の場のキャラへの攻撃（レスト状態のみ攻撃可能）
            for j, target in enumerate(opp.field):
                if target.is_resting:
                    actions.append(Action(
                        action_type=ActionType.ATTACK,
                        attacker_index=attacker_idx,
                        target_index=j
                    ))

        # アタックしないでターン終了
        actions.append(Action(action_type=ActionType.END_TURN))

        return actions

    # ------------------------------------------------------------------ #
    #  ブロックフェーズの合法手（相手ターン中）                             #
    # ------------------------------------------------------------------ #
    def _legal_block_actions(self) -> List[Action]:
        actions = []
        # ブロッカーを持つキャラでブロック可能
        defender = self.opp()  # ブロックするのは相手プレイヤー
        for i, char in enumerate(defender.field):
            if char.card.has_blocker and not char.is_resting:
                actions.append(Action(
                    action_type=ActionType.BLOCK,
                    target_index=i
                ))
        # ブロックしない
        actions.append(Action(action_type=ActionType.PASS_BLOCK))
        return actions

    def __repr__(self):
        p = self.current()
        return (
            f"Turn {self.turn} | Phase: {self.phase} | "
            f"Player {self.current_player} | "
            f"Hand: {len(p.hand)} | Field: {len(p.field)} | "
            f"Life: {len(p.life)} | DON: {p.don_available}"
        )