from dotenv import load_dotenv
load_dotenv()  # .envを自動で読み込む
import json
import os
import time
import glob
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.effect_parser import parse_all_cards

DATA_DIR = "data"
EFFECTS_DIR = os.path.join(DATA_DIR, "effects")


def parse_set(set_file: str, force: bool = False):
    set_path = os.path.join(DATA_DIR, set_file)
    with open(set_path, encoding="utf-8") as f:
        data = json.load(f)

    set_id = data["set_id"].lower().replace("-", "")  # ST-01 → st01
    out_path = os.path.join(EFFECTS_DIR, f"{set_id}_effects.json")

    # すでに解析済みならスキップ
    if os.path.exists(out_path) and not force:
        print(f"スキップ（既存）: {out_path}")
        return

    os.makedirs(EFFECTS_DIR, exist_ok=True)
    results = {}

    print(f"\n=== {data['set_name']} ({data['set_id']}) の効果を解析中 ===")
    for card in data["cards"]:
        effect_text = card.get("effect", "")
        card_id = card["card_id"]

        if not effect_text:
            results[card_id] = {"effects": [{"trigger": "none", "actions": [{"type": "none"}]}]}
            print(f"  skip {card_id} {card['name']} (効果なし)")
            continue

        print(f"  解析中: {card_id} {card['name']}")
        parsed = parse_card_effect(card_id, card["name"], effect_text)
        results[card_id] = parsed
        print(f"    → {json.dumps(parsed, ensure_ascii=False)[:80]}...")
        time.sleep(0.5)  # API制限対策

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n保存完了: {out_path} ({len(results)}件)")


if __name__ == "__main__":
    force = "--force" in sys.argv
    json_files = [os.path.basename(p) for p in glob.glob("data/*.json")]
    if not json_files:
        print("data/*.json が見つかりません")
    for f in json_files:
        parse_all_cards(f, force=force)
    print("\n全セット解析完了!")