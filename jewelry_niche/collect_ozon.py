"""Сбор выдачи Ozon через настоящий браузер (Ozon не отдаёт данные без него).

Один раз:
    pip install playwright
    playwright install chromium
Запуск (откроется окно Chrome; если Ozon покажет проверку — пройди её руками, скрипт подождёт):
    python3 collect_ozon.py --pages 10

Пишет out/ozon_cards.csv (формат analyze_cards.py). Продавец в выдаче Ozon не показывается —
колонка seller пустая. Ozon часто меняет вёрстку: если в CSV пусто, пришли out/raw_ozon/*.html.
"""
import argparse
import csv
import re
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

from collect_wb import QUERIES

OUT = Path("out")
RAW = OUT / "raw_ozon"

JS_TILES = """
() => {
  const seen = new Set(), out = [];
  for (const a of document.querySelectorAll('a[href*="/product/"]')) {
    const href = a.href.split('?')[0];
    if (seen.has(href)) continue;
    // поднимаемся до плитки, где есть цена
    let el = a;
    for (let i = 0; i < 8 && el && !/₽/.test(el.innerText || ''); i++) el = el.parentElement;
    if (!el) continue;
    seen.add(href);
    out.push({href, text: el.innerText || ''});
  }
  return out;
}
"""


def parse_tile(t):
    text = t["text"].replace(" ", " ").replace("\xa0", " ")
    prices = [int(re.sub(r"\D", "", p)) for p in re.findall(r"(\d[\d ]{1,8})\s?₽", text)]
    rating = re.search(r"\b([1-5][.,]\d)\b", text)
    reviews = re.search(r"(\d[\d ]*)\s+отзыв", text)
    lines = [ln.strip() for ln in text.split("\n") if len(ln.strip()) > 20 and "₽" not in ln]
    nm = re.search(r"-(\d{6,})/?$", t["href"].rstrip("/"))
    return {
        "platform": "ozon", "nm_id": nm.group(1) if nm else t["href"],
        "name": lines[0] if lines else "",
        "price_rub": min(prices) if prices else "",
        "rating": rating.group(1).replace(",", ".") if rating else "",
        "reviews": int(re.sub(r"\D", "", reviews.group(1))) if reviews else 0,
        "seller": "", "material": "", "url": t["href"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=10, help="страниц выдачи (~36 карточек)")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=False)
        page = br.new_page(locale="ru-RU")
        for q in QUERIES:
            pos = 0
            for n in range(1, a.pages + 1):
                url = f"https://www.ozon.ru/search/?text={urllib.parse.quote(q)}&from_global=true&page={n}"
                page.goto(url, wait_until="domcontentloaded")
                for _ in range(60):  # до минуты на ручное прохождение проверки
                    if page.query_selector('a[href*="/product/"]'):
                        break
                    time.sleep(1)
                for _ in range(6):
                    page.mouse.wheel(0, 2500)
                    time.sleep(0.8)
                (RAW / f"{abs(hash(q))}_{n}.html").write_text(page.content(), encoding="utf-8")
                tiles = page.evaluate(JS_TILES)
                print(f"[{q}] стр. {n}: {len(tiles)}")
                if not tiles:
                    break
                for t in tiles:
                    pos += 1
                    rows.append({"query": q, "position": pos, **parse_tile(t)})
                time.sleep(2)
        br.close()
    fields = ["platform", "query", "position", "nm_id", "name", "price_rub", "rating",
              "reviews", "seller", "material", "url"]
    with (OUT / "ozon_cards.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Готово: {len(rows)} -> {OUT / 'ozon_cards.csv'}")


if __name__ == "__main__":
    main()
