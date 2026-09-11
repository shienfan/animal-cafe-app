"""Streamlit版のエントリポイント。
採点ロジックはscoring.py、データ取得はdb.pyに任せ、ここでは画面表示に専念する。
画面とロジックを分けているので、CLI版(main.py)と同じ関数をそのまま共有でき、
採点部分だけをapp.py抜きでテストすることもできる。
"""

import base64
import datetime
from functools import lru_cache
from pathlib import Path

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

ASSETS_DIR = Path(__file__).parent / "assets"
CSS_PATH = ASSETS_DIR / "style.css"
HEADER_IMAGE_PATH = ASSETS_DIR / "hero" / "cat-rabbit-v2.webp"
DECOR_DIR = ASSETS_DIR / "decor"


@lru_cache(maxsize=1)
def load_css():
    return CSS_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=10)
def load_svg(name):
    return (DECOR_DIR / f"{name}.svg").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def header_image_uri():
    data = HEADER_IMAGE_PATH.read_bytes()
    return "data:image/webp;base64," + base64.b64encode(data).decode("ascii")


def render_header():
    # 同じ葉っぱの絵を、大きさと向き(mofu-header-leaf-1〜4)を変えて4枚散らす
    leaves = "".join(
        f'<span class="mofu-header-leaf mofu-header-leaf-{i}">{load_svg("leaf")}</span>'
        for i in range(1, 5)
    )
    return f"""
    <div class="mofu-header">
        <img class="mofu-header-photo" src="{header_image_uri()}" alt="カフェでくつろぐ猫とウサギ">
        <div class="mofu-header-title">いまから、もふもふ</div>
        {leaves}
    </div>
    """


def render_footer():
    # ページ最下部にも同じ葉っぱの絵を8枚散らす
    leaves = "".join(
        f'<span class="mofu-footer-leaf mofu-footer-leaf-{i}">{load_svg("leaf")}</span>'
        for i in range(1, 9)
    )
    return f'<div class="mofu-footer">{leaves}</div>'


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
    card_class = "mofu-card top" if rank == 1 else "mofu-card"

    return f"""
    <div class="{card_class}">
        <div class="mofu-card-rank">{rank}位</div>
        <div class="mofu-card-name">{emoji} {shop['name']}</div>
        <div class="mofu-card-meta">
            {shop['area']} / 徒歩{shop['walk_min']}分 / {shop['price_30min']}円
        </div>
        <div class="mofu-card-score">スコア: {shop['score']:.2f}点</div>
        <div class="mofu-bar">
            <div class="mofu-bar-fill" style="width:{percent}%;"></div>
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
    # set_page_configは他のst.*より先に呼ぶ必要がある。wideにして画面を広く使う
    st.set_page_config(layout="wide")

    # st.htmlはDOMPurifyでsvgタグを除去してしまうため、装飾には従来通りst.markdownを使う
    st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)
    st.markdown(render_header(), unsafe_allow_html=True)
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
        st.markdown(render_footer(), unsafe_allow_html=True)
        return

    if not filtered_shops:
        st.info("いま行けるお店が見つかりませんでした。条件を緩めてみてください。")
        st.markdown(render_footer(), unsafe_allow_html=True)
        return

    scored_shops = calculate_scores(filtered_shops, w_contact, w_price, w_walk)
    ranked_shops = sort_shops_by_score(scored_shops)
    top_score = ranked_shops[0]["score"]

    for rank, shop in enumerate(ranked_shops, start=1):
        st.markdown(build_card_html(shop, rank, top_score), unsafe_allow_html=True)

    st.markdown(render_footer(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
