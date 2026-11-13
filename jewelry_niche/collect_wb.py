"""Сбор выдачи Wildberries по запросам — запускать с российского IP (ноутбук).

Только стандартная библиотека Python 3.9+, ничего ставить не нужно:
    python3 collect_wb.py                    # 6 запросов × 5 страниц (до 500 карточек на запрос)
    python3 collect_wb.py --pages 3          # быстрее
    python3 collect_wb.py --no-details       # без материала и без фото

Что делает:
  1. Публичная поисковая выдача WB (то же, что видит покупатель в браузере), сортировка «по популярности».
  2. Для карточек дешевле --photo-max-price (3000 ₽) с самыми большими отзывами — card.json (материал)
     и первые 3 фото, чтобы оценить визуал (студия/на человеке).
Пишет:
  out/wb_cards.csv           — все карточки (формат для analyze_cards.py)
  out/photos/<nm_id>_<n>.webp — фото топ-карточек
  out/raw/                   — сырые ответы (если что-то сломается, пришли эту папку)

Пауза между запросами ~1.5 с; весь прогон ~5–10 минут.
"""
import argparse
import csv
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES = [
    "мужская цепочка",
    "цепь на шею мужская",
    "браслет мужской",
    "кольцо мужское",
    "набор украшений мужской",
    "мужские украшения сталь",
]
DEST = "-1257786"  # Москва
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
# WB периодически меняет версию/хост поиска — пробуем по очереди, запоминаем рабочий.
SEARCH_ENDPOINTS = [
    "https://search.wb.ru/exactmatch/ru/common/v18/search",
    "https://u-search.wb.ru/exactmatch/ru/common/v18/search",
    "https://search.wb.ru/exactmatch/ru/common/v14/search",
    "https://search.wb.ru/exactmatch/ru/common/v13/search",
    "https://search.wb.ru/exactmatch/ru/common/v9/search",
    "https://search.wb.ru/exactmatch/ru/common/v7/search",
]
# Известные диапазоны vol -> basket-NN; дальше подбираем перебором и кэшируем.
BASKET_RANGES = [(143, 1), (287, 2), (431, 3), (719, 4), (1007, 5), (1061, 6), (1115, 7),
                 (1169, 8), (1313, 9), (1601, 10), (1655, 11), (1919, 12), (2045, 13),
                 (2189, 14), (2405, 15), (2621, 16), (2837, 17), (3053, 18), (3269, 19),
                 (3485, 20), (3701, 21), (3917, 22), (4133, 23), (4349, 24), (4565, 25)]

OUT = Path("out")
RAW = OUT / "raw"
PHOTOS = OUT / "photos"


def get(url, binary=False, tries=3):
    for i in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "*/*", "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://www.wildberries.ru", "Referer": "https://www.wildberries.ru/"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(10 * (i + 1))
                continue
            print(f"  HTTP {e.code} {url[:90]}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"  {type(e).__name__}: {e} {url[:90]}", file=sys.stderr)
        time.sleep(2 * (i + 1))
    return None


def pause():
    time.sleep(1.2 + random.random() * 0.8)


def price_rub(p):
    # новые версии: sizes[].price.product (копейки); старые: salePriceU (копейки)
    for s in p.get("sizes") or []:
        pr = (s.get("price") or {})
        if pr.get("product"):
            return pr["product"] / 100, (pr.get("basic") or 0) / 100
    if p.get("salePriceU"):
        return p["salePriceU"] / 100, (p.get("priceU") or 0) / 100
    return None, None


def products_of(js):
    if not js:
        return []
    d = js.get("data") if isinstance(js.get("data"), dict) else js
    return d.get("products") or []


_endpoint = None


def search(query, page):
    global _endpoint
    params = urllib.parse.urlencode({
        "ab_testing": "false", "appType": 1, "curr": "rub", "dest": DEST, "hide_dtype": 13,
        "lang": "ru", "page": page, "query": query, "resultset": "catalog", "sort": "popular",
        "spp": 30, "suppressSpellcheck": "false"})
    endpoints = [_endpoint] if _endpoint else SEARCH_ENDPOINTS
    for ep in endpoints:
        txt = get(f"{ep}?{params}")
        if not txt:
            continue
        (RAW / f"search_{abs(hash(query))}_{page}.json").write_text(txt, encoding="utf-8")
        try:
            js = json.loads(txt)
        except json.JSONDecodeError:
            continue
        prods = products_of(js)
        if prods or _endpoint:
            if not _endpoint:
                _endpoint = ep
                print(f"  рабочий эндпоинт: {ep}")
            return prods
        pause()
    return []


_vol_host = {}


def basket_host(nm):
    vol = nm // 100000
    if vol in _vol_host:
        return _vol_host[vol]
    guess = next((n for top, n in BASKET_RANGES if vol <= top), 26)
    candidates = [guess] + [n for n in range(1, 41) if n != guess]
    if vol > BASKET_RANGES[-1][0]:  # новые карточки — сначала самые «старшие» корзины
        candidates = list(range(40, 0, -1))
    for n in candidates:
        url = f"https://basket-{n:02d}.wbbasket.ru/vol{vol}/part{nm // 1000}/{nm}/info/ru/card.json"
        txt = get(url, tries=1)
        if txt and txt.lstrip().startswith("{"):
            _vol_host[vol] = n
            return n
    return None


def card_details(nm):
    n = basket_host(nm)
    if not n:
        return None, None
    base = f"https://basket-{n:02d}.wbbasket.ru/vol{nm // 100000}/part{nm // 1000}/{nm}"
    txt = get(f"{base}/info/ru/card.json")
    if not txt:
        return None, base
    (RAW / f"card_{nm}.json").write_text(txt, encoding="utf-8")
    js = json.loads(txt)
    mats = []
    for o in js.get("options") or []:
        if any(k in (o.get("name") or "").lower() for k in ("материал", "металл", "покрытие")):
            mats.append(f"{o['name']}: {o.get('value')}")
    for c in js.get("compositions") or []:
        mats.append(c.get("name", ""))
    return "; ".join(m for m in mats if m), base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=5, help="страниц по 100 карточек на запрос")
    ap.add_argument("--no-details", action="store_true")
    ap.add_argument("--top-details", type=int, default=60,
                    help="сколько топ-карточек (по отзывам, ≤ цены) догрузить с материалом и фото")
    ap.add_argument("--photo-max-price", type=float, default=3000)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    PHOTOS.mkdir(parents=True, exist_ok=True)

    rows = []
    for q in QUERIES:
        print(f"[{q}]")
        pos = 0
        for page in range(1, a.pages + 1):
            prods = search(q, page)
            print(f"  стр. {page}: {len(prods)}")
            if not prods:
                break
            for p in prods:
                pos += 1
                price, basic = price_rub(p)
                rows.append({
                    "platform": "wb", "query": q, "position": pos, "nm_id": p.get("id"),
                    "name": p.get("name"), "brand": p.get("brand"),
                    "price_rub": price, "price_before_discount_rub": basic,
                    "rating": p.get("reviewRating") or p.get("rating"),
                    "reviews": p.get("nmFeedbacks") if p.get("nmFeedbacks") is not None else p.get("feedbacks"),
                    "reviews_all_colors": p.get("feedbacks"),
                    "seller": p.get("supplier"), "seller_id": p.get("supplierId"),
                    "seller_rating": p.get("supplierRating"), "photos_count": p.get("pics"),
                    "is_ad": bool(p.get("log")), "material": "",
                    "url": f"https://www.wildberries.ru/catalog/{p.get('id')}/detail.aspx",
                })
            pause()
        if _endpoint is None:
            print("Поиск WB не ответил. Проверь, что открыт wildberries.ru в браузере с этого IP, "
                  "и пришли папку out/raw.", file=sys.stderr)
            sys.exit(1)

    if not a.no_details:
        uniq = {}
        for r in rows:
            if r["price_rub"] and r["price_rub"] <= a.photo_max_price:
                uniq.setdefault(r["nm_id"], r)
        top = sorted(uniq.values(), key=lambda r: -(r["reviews"] or 0))[:a.top_details]
        print(f"Детали и фото для {len(top)} карточек…")
        mat = {}
        for i, r in enumerate(top, 1):
            nm = int(r["nm_id"])
            m, base = card_details(nm)
            mat[nm] = m or ""
            if base:
                for k in range(1, 4):
                    img = get(f"{base}/images/big/{k}.webp", binary=True, tries=1)
                    if img:
                        (PHOTOS / f"{i:02d}_{nm}_{k}.webp").write_bytes(img)
            print(f"  {i}/{len(top)} {nm} {mat[nm][:60]}")
            pause()
        for r in rows:
            r["material"] = mat.get(int(r["nm_id"]), "")

    with (OUT / "wb_cards.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Готово: {len(rows)} строк -> {OUT / 'wb_cards.csv'}; фото в {PHOTOS}")
    print("Пришли out/wb_cards.csv и папку out/photos (можно архивом).")


if __name__ == "__main__":
    main()
