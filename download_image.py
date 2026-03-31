"""
カード画像を一括ダウンロードするスクリプト。
一度だけ実行すればOK。data/images/ に保存されます。
"""
import requests
import os
import json
import time
import glob

DATA_DIR = "data"
IMAGE_DIR = os.path.join(DATA_DIR, "images")


def download_images_for_set(set_file: str):
    path = os.path.join(DATA_DIR, set_file)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    set_name = data.get("set_name", set_file)
    print(f"\n=== {set_name} ({data['set_id']}) ===")

    os.makedirs(IMAGE_DIR, exist_ok=True)

    success, skip, fail = 0, 0, 0
    for card in data["cards"]:
        url = card.get("image_url", "")
        if not url:
            continue

        filename = os.path.join(IMAGE_DIR, f"{card['card_id']}.webp")

        # すでにダウンロード済みならスキップ
        if os.path.exists(filename):
            print(f"  skip {card['card_id']}")
            skip += 1
            continue

        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print(f"  ✓ {card['card_id']} {card['name']}")
                success += 1
            else:
                print(f"  ✗ {card['card_id']} (HTTP {res.status_code})")
                fail += 1
        except Exception as e:
            print(f"  ✗ {card['card_id']} ({e})")
            fail += 1

        time.sleep(0.3)  # サーバー負荷対策

    print(f"完了: {success}枚ダウンロード / {skip}枚スキップ / {fail}枚失敗")


if __name__ == "__main__":
    # dataフォルダ内の全JSONを対象にする
    json_files = [os.path.basename(p) for p in glob.glob("data/*.json")]
    if not json_files:
        print("data/*.json が見つかりません")
    for f in json_files:
        download_images_for_set(f)
    print("\n全セット完了! data/images/ に保存されました。")