"""Tasks 2-3 on a card dump you collect yourself (WB/Ozon are not reachable
from the environment where this was written).

Input CSV columns (any extra columns are ignored):
  platform, query, position, nm_id, name, price_rub, rating, reviews, seller, material, url

Usage:  python3 analyze_cards.py cards.csv
Writes next to the input: *_price_dist.csv, *_sellers.csv, *_top_under3000.csv

NB: отзывы — прокси продаж, не продажи. Соотношение отзывы/продажи
различается между карточками и категориями.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

BINS = [0, 300, 500, 750, 1000, 1500, 2000, 2500, 3000, 5000, 10**9]

src = Path(sys.argv[1])
rows = list(csv.DictReader(src.open(encoding="utf-8")))
for r in rows:
    r["price_rub"] = float(r["price_rub"] or 0)
    r["reviews"] = int(float(r["reviews"] or 0))

# dedupe across queries per platform
uniq = {(r["platform"], r["nm_id"]): r for r in rows}.values()


def label(lo, hi):
    return f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"


dist = []
groups = defaultdict(list)
for r in rows:
    groups[(r["platform"], r["query"])].append(r)
for (platform, query), grp in sorted(groups.items()):
    prices = sorted(r["price_rub"] for r in grp)
    for lo, hi in zip(BINS, BINS[1:]):
        n = sum(lo <= p < hi for p in prices)
        dist.append({"platform": platform, "query": query, "bin": label(lo, hi),
                     "cards": n, "share_pct": round(100 * n / len(prices), 1)})
    dist.append({"platform": platform, "query": query, "bin": "median",
                 "cards": len(prices), "share_pct": prices[len(prices) // 2]})

sellers = []
for (platform, query), grp in sorted(groups.items()):
    cards = Counter(r["seller"] for r in grp)
    revs = Counter()
    for r in grp:
        revs[r["seller"]] += r["reviews"]
    tot_c, tot_r = len(grp), sum(revs.values()) or 1
    top10 = [s for s, _ in revs.most_common(10)]
    sellers.append({"platform": platform, "query": query, "sellers": len(cards),
                    "top10_share_cards_pct": round(100 * sum(cards[s] for s in top10) / tot_c, 1),
                    "top10_share_reviews_pct": round(100 * sum(revs[s] for s in top10) / tot_r, 1),
                    "top10": "; ".join(top10)})

top = sorted((r for r in uniq if r["price_rub"] <= 3000), key=lambda r: -r["reviews"])[:50]


def dump(name, data):
    p = src.with_name(f"{src.stem}_{name}.csv")
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
    print("wrote", p)


dump("price_dist", dist)
dump("sellers", sellers)
dump("top_under3000", [{k: r.get(k) for k in
                        ("platform", "nm_id", "name", "price_rub", "rating", "reviews",
                         "seller", "material", "url")} | {"visual_type": ""} for r in top])
print("Колонку visual_type (studio_white / on_model / lifestyle) заполнить вручную по фото карточек.")
