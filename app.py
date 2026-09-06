"""Streamlit版のエントリポイント。
採点ロジックはscoring.py、データ取得はdb.pyに任せ、ここでは画面表示に専念する。
画面とロジックを分けているので、CLI版(main.py)と同じ関数をそのまま共有でき、
採点部分だけをapp.py抜きでテストすることもできる。
"""

import datetime

import psycopg2
import streamlit as st

from db import fetch_all_shops
from scoring import calculate_scores, sort_shops_by_score

ANIMAL_EMOJI = {
    "猫": "🐱",
    "サモエド": "🐶",
    "ハリネズミ": "🦔",
    "ブタ": "🐷",
}


@st.cache_data(ttl=60)
def load_shops():
    # スライダー操作のたびに毎回DBへ問い合わせないよう、短時間だけ結果をキャッシュする
    return fetch_all_shops()


def get_animal_options(shops):
    # DBに実在する動物だけを選択肢にする(架空の動物種を選べないようにするため)
    animals = {shop["animal"] for shop in shops}
    return ["ぜんぶ"] + sorted(animals)


def filter_by_animal(shops, animal):
    # 「ぜんぶ」のときは絞り込まずそのまま返す
    if animal == "ぜんぶ":
        return shops
    return [shop for shop in shops if shop["animal"] == animal]


def filter_open_now(shops, now_time):
    # 現在時刻がopen_time〜close_timeに含まれる店だけ残す(日またぎ営業は今回未対応)
    return [
        shop for shop in shops if shop["open_time"] <= now_time <= shop["close_time"]
    ]


def build_card_html(shop, rank, top_score):
    # 1位のスコアを100%とした相対バーで見せ、1位のカードだけ枠線を太くして強調する
    emoji = ANIMAL_EMOJI.get(shop["animal"], "🐾")
    percent = 0 if top_score == 0 else min(shop["score"] / top_score, 1.0) * 100
    border = "3px solid #E8A0B4" if rank == 1 else "1px solid #ddd"

    return f"""
    <div style="border:{border}; border-radius:10px; padding:16px; margin-bottom:12px;">
        <div style="font-size:14px; color:#5C4A42;">{rank}位</div>
        <div style="font-size:20px; font-weight:bold;">{emoji} {shop['name']}</div>
        <div style="font-size:14px; color:#5C4A42;">
            {shop['area']} / 徒歩{shop['walk_min']}分 / {shop['price_30min']}円
        </div>
        <div style="font-size:16px; margin-top:8px;">スコア: {shop['score']:.2f}点</div>
        <div style="background-color:#eee; border-radius:6px; height:10px; margin-top:4px;">
            <div style="width:{percent}%; background-color:#E8A0B4;
                        height:10px; border-radius:6px;"></div>
        </div>
    </div>
    """


def render_sidebar(shops):
    # サイドバーの入力を1か所にまとめ、main()側は値を受け取るだけにする
    st.sidebar.header("こだわり条件")
    w_contact = st.sidebar.slider("ふれあい重視", 0, 10, 5)
    w_price = st.sidebar.slider("安さ重視", 0, 10, 5)
    w_walk = st.sidebar.slider("近さ重視", 0, 10, 5)
    animal = st.sidebar.selectbox("動物のしゅるい", get_animal_options(shops))
    open_only = st.sidebar.checkbox("いま営業中の店のみ表示", value=True)
    return w_contact, w_price, w_walk, animal, open_only


def main():
    st.title("いまから、もふもふ")
    st.caption("いま営業中の動物カフェを、あなたの好みに合わせてスコアで比較できます")

    # DB接続に失敗してもスタックトレースを見せず、案内メッセージだけ出して止める
    try:
        shops = load_shops()
    except psycopg2.Error:
        st.error("データベースに接続できませんでした")
        st.stop()

    w_contact, w_price, w_walk, animal, open_only = render_sidebar(shops)

    filtered_shops = filter_by_animal(shops, animal)
    if open_only:
        now_time = datetime.datetime.now().time()
        filtered_shops = filter_open_now(filtered_shops, now_time)

    # 重みが全て0だとスコアが意味を持たなくなるため、先に案内して終了する
    if w_contact == 0 and w_price == 0 and w_walk == 0:
        st.info("重みを1つ以上設定してください")
        return

    if not filtered_shops:
        st.info("いま行けるお店が見つかりませんでした。条件を緩めてみてください。")
        return

    scored_shops = calculate_scores(filtered_shops, w_contact, w_price, w_walk)
    ranked_shops = sort_shops_by_score(scored_shops)
    top_score = ranked_shops[0]["score"]

    for rank, shop in enumerate(ranked_shops, start=1):
        st.markdown(build_card_html(shop, rank, top_score), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
