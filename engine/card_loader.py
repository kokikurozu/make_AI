from __future__ import annotations
import json
import os
from typing import List, Tuple

from engine.card import Card, CardType, Color


COLOR_MAP = {
    "red":    Color.RED,
    "blue":   Color.BLUE,
    "green":  Color.GREEN,
    "purple": Color.PURPLE,
    "black":  Color.BLACK,
    "yellow": Color.YELLOW,
}

TYPE_MAP = {
    "leader":    CardType.LEADER,
    "character": CardType.CHARACTER,
    "event":     CardType.EVENT,
    "stage":     CardType.STAGE,
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_set(set_file: str) -> List[Card]:
    """JSONファイルからカードリストを読み込む（copies_in_deck分だけ複製）"""
    path = os.path.join(DATA_DIR, set_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    cards = []
    for c in data["cards"]:
        card = Card(
            card_id=c["card_id"],
            name=c["name"],
            card_type=TYPE_MAP[c["card_type"]],
            color=COLOR_MAP[c["color"]],
            cost=c["cost"],
            power=c["power"],
            counter=c.get("counter"),
            has_rush=c.get("has_rush", False),
            has_blocker=c.get("has_blocker", False),
            don_requirement=c.get("don_requirement", 0),
        )
        copies = c.get("copies_in_deck", 1)
        if card.card_type != CardType.LEADER:
            cards.extend([card] * copies)

    return cards


def load_leader(set_file: str) -> Card:
    """JSONファイルからリーダーカードを読み込む"""
    path = os.path.join(DATA_DIR, set_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    for c in data["cards"]:
        if c["card_type"] == "leader":
            return Card(
                card_id=c["card_id"],
                name=c["name"],
                card_type=CardType.LEADER,
                color=COLOR_MAP[c["color"]],
                cost=0,
                power=c["power"],
                counter=None,
                has_rush=False,
                has_blocker=False,
            )
    raise ValueError(f"リーダーカードが見つかりません: {set_file}")


def load_deck(set_file: str) -> Tuple[Card, List[Card]]:
    """リーダーとデッキをまとめて返す"""
    leader = load_leader(set_file)
    deck = load_set(set_file)
    return leader, deck


def list_cards(set_file: str):
    """デッキの内容を表示（デバッグ用）"""
    path = os.path.join(DATA_DIR, set_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"=== {data['set_name']} ({data['set_id']}) ===")
    total = 0
    for c in data["cards"]:
        if c["card_type"] == "leader":
            print(f"  [LEADER] {c['card_id']} {c['name']} / power:{c['power']}")
        else:
            copies = c.get("copies_in_deck", 1)
            total += copies
            rush = "⚡速攻" if c.get("has_rush") else ""
            blocker = "🛡ブロッカー" if c.get("has_blocker") else ""
            print(f"  x{copies} {c['card_id']} {c['name']} "
                  f"/ cost:{c['cost']} power:{c['power']} "
                  f"counter:{c.get('counter', '-')} {rush}{blocker}")
    print(f"合計: {total}枚")


if __name__ == "__main__":
    list_cards("st01.json")