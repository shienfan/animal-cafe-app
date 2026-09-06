"""CLI版のエントリポイント。
DB接続はdb.py、採点ロジックはscoring.pyに任せ、ここでは入力処理と表示に専念する。
"""

import argparse
import datetime
import sys

import psycopg2

from db import fetch_all_shops
from scoring import calculate_scores, sort_shops_by_score

ANIMAL_EMOJI = {
    "猫": "🐱",
    "サモエド": "🐶",
    "ハリネズミ": "🦔",
    "ブタ": "🐷",
}

# Windowsのコンソール(cp932)は絵文字を出力できないため、標準出力をUTF-8に切り替える
sys.stdout.reconfigure(encoding="utf-8")


def filter_by_animal(shops, animal):
    # 「ぜんぶ」指定のときは絞り込まずそのまま返す
    if not animal or animal == "ぜんぶ":
        return shops
    return [shop for shop in shops if shop["animal"] == animal]


def filter_open_now(shops, now_time):
    # 現在時刻がopen_time〜close_timeに含まれる店だけ残す(日またぎ営業は今回未対応)
    return [
        shop for shop in shops if shop["open_time"] <= now_time <= shop["close_time"]
    ]


def print_ranking(shops):
    # 絵文字対応表に無い動物種は既定値🐾を使い、例外を発生させない
    for rank, shop in enumerate(shops, start=1):
        emoji = ANIMAL_EMOJI.get(shop["animal"], "🐾")
        print(
            f"{rank}位  {emoji} {shop['name']}  {shop['score']:.2f}点  "
            f"({shop['area']} / 徒歩{shop['walk_min']}分 / {shop['price_30min']}円)"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="動物カフェ検索CLI")
    parser.add_argument(
        "--animal", default="ぜんぶ", help="絞り込む動物の種類(既定:ぜんぶ)"
    )
    parser.add_argument(
        "--all-hours", action="store_true", help="営業時間外の店も表示する"
    )
    parser.add_argument(
        "--w-contact", type=float, default=5, help="ふれあい重視の重み(0-10)"
    )
    parser.add_argument("--w-price", type=float, default=5, help="安さ重視の重み(0-10)")
    parser.add_argument("--w-walk", type=float, default=5, help="近さ重視の重み(0-10)")
    return parser.parse_args()


def main():
    args = parse_args()

    # DB接続に失敗してもスタックトレースを見せず、案内メッセージだけ出して終了する
    try:
        shops = fetch_all_shops()
    except psycopg2.Error:
        print("データベースに接続できませんでした")
        return

    shops = filter_by_animal(shops, args.animal)

    if not args.all_hours:
        now_time = datetime.datetime.now().time()
        shops = filter_open_now(shops, now_time)

    # 重みが全て0だとスコアが意味を持たなくなるため、先に案内して終了する
    if args.w_contact == 0 and args.w_price == 0 and args.w_walk == 0:
        print("重みを1つ以上設定してください")
        return

    if not shops:
        print("いま行けるお店が見つかりませんでした")
        return

    scored_shops = calculate_scores(shops, args.w_contact, args.w_price, args.w_walk)
    ranked_shops = sort_shops_by_score(scored_shops)
    print_ranking(ranked_shops)


if __name__ == "__main__":
    main()
