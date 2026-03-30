from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ActionType(Enum):
    PLAY_CARD  = "play_card"   # 手札からキャラを出す
    ATTACH_DON = "attach_don"  # DONをリーダー/キャラにつける
    ATTACK     = "attack"      # アタック宣言
    BLOCK      = "block"       # ブロック
    PASS_BLOCK = "pass_block"  # ブロックしない
    END_TURN   = "end_turn"    # ターン終了


@dataclass(frozen=True)
class Action:
    action_type: ActionType
    # play_card 用
    hand_index: Optional[int] = None
    # attach_don 用: -1=リーダー, 0以上=場のキャラindex
    attach_target: Optional[int] = None
    don_count: int = 0
    # attack 用: attacker_index=-1はリーダー, 0以上は場のキャラ
    attacker_index: Optional[int] = None
    # attack / block 用: target_index=-1はリーダー, 0以上は場のキャラ
    target_index: Optional[int] = None

    def __repr__(self):
        if self.action_type == ActionType.PLAY_CARD:
            return f"PlayCard(hand[{self.hand_index}])"
        elif self.action_type == ActionType.ATTACH_DON:
            t = "Leader" if self.attach_target == -1 else f"Field[{self.attach_target}]"
            return f"AttachDON({self.don_count} -> {t})"
        elif self.action_type == ActionType.ATTACK:
            a = "Leader" if self.attacker_index == -1 else f"Field[{self.attacker_index}]"
            t = "Leader" if self.target_index == -1 else f"Field[{self.target_index}]"
            return f"Attack({a} -> {t})"
        elif self.action_type == ActionType.BLOCK:
            return f"Block(Field[{self.target_index}])"
        elif self.action_type == ActionType.PASS_BLOCK:
            return "PassBlock"
        elif self.action_type == ActionType.END_TURN:
            return "EndTurn"
        return f"Action({self.action_type})"