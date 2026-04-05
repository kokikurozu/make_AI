"""
カードテキストをClaude APIで解析して構造化JSONに変換するモジュール。
解析結果はdata/effect_cache.jsonにキャッシュされる。
"""
from __future__ import annotations
import json
import os
import anthropic

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_PATH = os.path.join(DATA_DIR, "effect_cache.json")

SYSTEM_PROMPT = """
あなたはワンピースカードゲームのカード効果を解析するエキスパートです。
カードの効果テキストを受け取り、以下のJSONスキーマに従って構造化してください。
JSONのみを返してください。説明文や```は不要です。

## 効果スキーマ
{"effects": [{"trigger": "トリガー種別", "condition": null, "actions": [アクションのリスト]}]}

## trigger の種別
- "on_play"       : 登場時
- "when_attacking": アタック時
- "activate_main" : 起動メイン
- "counter"       : カウンター
- "trigger"       : トリガー（ライフから手札に来たとき）
- "passive"       : 常時効果
- "don_x"         : ドン!!×N条件付き

## condition の種別
- null
- {"don_gte": N}
- {"power_gte": N}
- {"feature": "特徴名"}

## actions の種別
{"type": "draw", "player": "self", "count": N}
{"type": "add_to_life", "player": "self", "count": N}
{"type": "ko_character", "target": "opponent", "cost_lte": N}
{"type": "ko_character", "target": "opponent", "power_lte": N}
{"type": "rest_character", "target": "opponent", "count": N}
{"type": "power_boost", "target": "self_leader_or_char", "value": N, "duration": "battle"}
{"type": "attach_don", "target": "self_leader_or_char", "count": N}
{"type": "return_don", "count": N}
{"type": "blocker"}
{"type": "rush"}
{"type": "cannot_block", "power_gte": N}
{"type": "play_from_hand", "target": "self"}

## 例
入力: "[登場時] 自分のデッキの上から1枚を手札に加える。"
出力: {"effects": [{"trigger": "on_play", "condition": null, "actions": [{"type": "draw", "player": "self", "count": 1}]}]}

入力: "[ブロッカー]"
出力: {"effects": [{"trigger": "passive", "condition": null, "actions": [{"type": "blocker"}]}]}

入力: "[ドン!!×2] このキャラは速攻を得る。"
出力: {"effects": [{"trigger": "don_x", "condition": {"don_gte": 2}, "actions": [{"type": "rush"}]}]}

入力テキストが空または「–」の場合: {"effects": []}
"""


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def parse_effect(card_id: str, effect_text: str, force: bool = False) -> dict:
    """
    カードテキストを解析して構造化JSONを返す。
    キャッシュがあればAPIを呼ばない。
    """
    if not effect_text or effect_text.strip() in ("", "-", "–"):
        return {"effects": []}

    cache = _load_cache()
    if card_id in cache and not force:
        return cache[card_id]

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"カードID: {card_id}\n効果テキスト: {effect_text}"}
        ]
    )

    raw = message.content[0].text.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[EffectParser] JSONパース失敗 ({card_id}): {raw}")
        result = {"effects": [], "parse_error": raw}

    cache[card_id] = result
    _save_cache(cache)
    return result


def parse_all_cards(set_file: str, force: bool = False):
    """セットファイルの全カードを一括解析してキャッシュする。"""
    path = os.path.join(DATA_DIR, set_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n=== {data['set_name']} 効果解析開始 ===")
    cache = _load_cache()
    results = {}

    for c in data["cards"]:
        card_id = c["card_id"]
        effect = c.get("effect", "")

        if card_id in cache and not force:
            print(f"  skip {card_id} (キャッシュ済み)")
            results[card_id] = cache[card_id]
            continue

        print(f"  解析中: {card_id} {c['name']}...")
        result = parse_effect(card_id, effect, force=force)
        results[card_id] = result
        print(f"    → {json.dumps(result, ensure_ascii=False)}")

    print(f"\n完了: {len(results)}枚解析")
    return results


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    parse_all_cards("st01.json", force=force)