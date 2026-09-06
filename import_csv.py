"""data/shops.csv の内容をPostgreSQLのshopsテーブルに投入するスクリプト。
何度実行しても重複登録されないよう、投入前に必ずTRUNCATEしてIDを振り直す。
"""

import csv
import datetime
from pathlib import Path

from db import get_connection

# 実行時のカレントディレクトリに依存しないよう、このファイルの場所を起点にする
CSV_PATH = Path(__file__).parent / "data" / "shops.csv"

# SQLインジェクション対策として、値の埋め込みには文字列連結ではなくプレースホルダ(%s)を使う
INSERT_SQL = """
    INSERT INTO shops
        (name, animal, area, walk_min, price_30min,
         contact_level, animal_count, quietness, open_time, close_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def parse_row(row):
    # 数値・時刻に変換できない値が来たら例外を送出し、呼び出し側でその行をスキップする
    return (
        row["name"],
        row["animal"],
        row["area"],
        int(row["walk_min"]),
        int(row["price_30min"]),
        int(row["contact_level"]),
        int(row["animal_count"]),
        int(row["quietness"]),
        datetime.datetime.strptime(row["open_time"], "%H:%M").time(),
        datetime.datetime.strptime(row["close_time"], "%H:%M").time(),
    )


def load_rows(csv_path):
    # 欠損値や不正な値がある行はスキップし、何行目をスキップしたか標準出力に表示する
    valid_rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_number, row in enumerate(reader, start=2):
            try:
                valid_rows.append(parse_row(row))
            except (ValueError, KeyError, TypeError):
                print(f"{line_number}行目をスキップしました: {row}")
    return valid_rows


def import_shops(csv_path):
    rows = load_rows(csv_path)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 再実行時に重複投入されないよう、投入前に必ず空にしてIDを1から振り直す
            cur.execute("TRUNCATE TABLE shops RESTART IDENTITY;")
            cur.executemany(INSERT_SQL, rows)
        conn.commit()
    finally:
        conn.close()

    print(f"{len(rows)}件のデータを投入しました")


if __name__ == "__main__":
    import_shops(CSV_PATH)
