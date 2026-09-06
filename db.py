"""PostgreSQLへの接続とSELECTを行うモジュール。
接続情報(ホスト・パスワード等)はコードに書かず、環境変数(.env)から読む(秘匿情報の漏洩防止)。
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    # 呼び出すたびに環境変数を読み直すことで、.envを書き換えたらすぐ反映される
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def fetch_all_shops():
    # SQLインジェクション対策として、値を埋め込む場合は必ずプレースホルダ(%s)を使う
    query = (
        "SELECT name, animal, area, walk_min, price_30min, "
        "contact_level, animal_count, quietness, open_time, close_time "
        "FROM shops"
    )
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()

    shops = [dict(zip(columns, row)) for row in rows]
    return shops
