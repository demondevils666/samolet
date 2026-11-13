"""Collect public 1688 'market' SEO pages (JSON-LD ItemList) for given keywords.
Usage: python3 fetch_1688_market.py OUT.csv RAW_DIR kw1 kw2 ...
"""
import csv, json, re, sys, time, subprocess
from pathlib import Path

out, raw = Path(sys.argv[1]), Path(sys.argv[2]); raw.mkdir(parents=True, exist_ok=True)
rows = []
for kw in sys.argv[3:]:
    slug = kw.encode("gbk").hex().upper()
    for base in (f"https://www.1688.com/market/-{slug}.html", f"https://s.1688.com/kq/-{slug}.html"):
        f = raw / f"1688_{slug}_{'m' if 'market' in base else 'kq'}.html"
        subprocess.run(["curl", "-sS", "-m", "40", "-o", str(f), base], check=False)
        t = f.read_text(encoding="utf-8", errors="ignore") if f.exists() else ""
        n = 0
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
            try:
                d = json.loads(block)
            except Exception:
                continue
            for g in d.get("@graph", [d]):
                for el in g.get("itemListElement", []) if isinstance(g, dict) else []:
                    it = el.get("item", {}) if isinstance(el, dict) else {}
                    if not isinstance(it, dict):
                        continue
                    off = it.get("offers", {})
                    off = off[0] if isinstance(off, list) and off else off
                    off = off if isinstance(off, dict) else {}
                    rows.append({"keyword": kw, "source_page": base, "position": el.get("position"),
                                 "name": it.get("name"), "price_cny": off.get("price"),
                                 "url": it.get("url"), "image": it.get("image")})
                    n += 1
        print(kw, base.split('/')[3], "punish" in t, n, file=sys.stderr)
        time.sleep(2)
        if n:
            break
with out.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["keyword", "source_page", "position", "name", "price_cny", "url", "image"])
    w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", out, file=sys.stderr)
