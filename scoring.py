"""正規化とスコア計算を行う純粋関数群。
Streamlit や DB 接続には依存させない。CLI版・画面版の両方から同じ関数を呼び出す。
"""


def normalize_column(shops, key, higher_is_better):
    # 値の幅がゼロ(max == min)だと0除算になるため、その場合は全店に1.0を与える
    values = [shop[key] for shop in shops]
    min_value = min(values)
    max_value = max(values)

    if max_value == min_value:
        return [1.0 for _ in shops]

    normalized = []
    for value in values:
        if higher_is_better:
            normalized.append((value - min_value) / (max_value - min_value))
        else:
            normalized.append((max_value - value) / (max_value - min_value))
    return normalized


def calculate_scores(shops, w_contact, w_price, w_walk):
    # ふれあい・安さ・近さを個別に正規化してから重み付き合計をとる
    if not shops:
        return []

    n_contact = normalize_column(shops, "contact_level", higher_is_better=True)
    n_price = normalize_column(shops, "price_30min", higher_is_better=False)
    n_walk = normalize_column(shops, "walk_min", higher_is_better=False)

    scored_shops = []
    for shop, c, p, w in zip(shops, n_contact, n_price, n_walk):
        scored_shop = dict(shop)
        scored_shop["score"] = w_contact * c + w_price * p + w_walk * w
        scored_shops.append(scored_shop)
    return scored_shops


def sort_shops_by_score(shops):
    # スコアの降順に並べ替える。sorted()は安定ソートなので同点時は元の順序を保つ
    return sorted(shops, key=lambda shop: shop["score"], reverse=True)
