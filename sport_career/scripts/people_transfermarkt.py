# -*- coding: utf-8 -*-
"""Персонал клубов РПЛ с Transfermarkt (публичные страницы "Staff"/"Mitarbeiter").

Берем только профессиональные роли: руководство, спортивный директор, скаутинг, аналитика,
коммерция/маркетинг. Контакты не собираем (их там и нет). Результат: data/people_tm.csv.
Transfermarkt редактируется сообществом: уверенность по умолчанию "средняя".
"""
import csv
import datetime as dt
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# РПЛ 2026/27 (id Transfermarkt -> название клуба по-русски)
CLUBS = {
    964: ("zenit-st-petersburg", "ФК Зенит"), 232: ("spartak-moskau", "ФК Спартак"),
    2410: ("zska-moskau", "ПФК ЦСКА"), 121: ("dinamo-moskau", "ФК Динамо Москва"),
    16704: ("fk-krasnodar", "ФК Краснодар"), 932: ("lokomotiv-moskau", "ФК Локомотив"),
    2698: ("rubin-kazan", "ФК Рубин"), 2741: ("baltika-kaliningrad", "ФК Балтика"),
    1083: ("fk-rostov", "ФК Ростов"), 3725: ("akhmat-grozny", "ФК Ахмат"),
    71985: ("akron-togliatti", "ФК Акрон"), 59024: ("rodina-moskau", "ФК Родина"),
    2696: ("krylya-sovetov-samara", "ФК Крылья Советов"), 14589: ("fk-orenburg", "ФК Оренбург"),
    75231: ("fk-makhachkala", "ФК Динамо Махачкала"), 1124: ("fakel-voronezh", "ФК Факел"),
}
KEEP = re.compile(r"(chief executive|general director|managing director|president|chairman|sporting director|"
                  r"director of football|technical director|sports director|head of scouting|chief scout|scout|"
                  r"analys|data|head of recruitment|recruitment|commercial|marketing|strategy|development|"
                  r"general manager|ceo|executive)", re.I)
SKIP = re.compile(r"(coach|medical|doctor|physio|kit|press|media officer|team organi|goalkeeping|fitness|"
                  r"conditioning|youth|u19|u21|academy coach|board member|advisor)", re.I)


CACHE = os.path.join(HERE, "state", "tm_cache")


def fetch(url, cache_name):
    """Страница с кэшем на диске; при 405/429 (антибот) ждем и пробуем позже, капчи не обходим."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, cache_name)
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 7 * 86400:
        return open(path, encoding="utf-8").read()
    for wait in (0, 60, 180):
        time.sleep(wait)
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}, timeout=40)
        if r.status_code == 200:
            open(path, "w", encoding="utf-8").write(r.text)
            return r.text
        print(f"  {url}: HTTP {r.status_code}, жду", file=sys.stderr)
    raise RuntimeError(f"Transfermarkt не отдал {url}")


def staff(tm_id, slug):
    url = f"https://www.transfermarkt.com/{slug}/mitarbeiter/verein/{tm_id}"
    soup = BeautifulSoup(fetch(url, f"{tm_id}.html"), "lxml")
    rows = []
    for h in soup.find_all("h2"):
        section = h.get_text(strip=True)
        box = h.find_parent("div", class_=re.compile("box"))
        if not box:
            continue
        for tr in box.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 7:
                continue
            cells = [td.get_text(" ", strip=True) for td in tds]
            name_a = tr.find("a", href=re.compile(r"/profil/trainer/|/profil/mitarbeiter/|/profil/"))
            # формат строки: [имя+роль, '', имя, роль, возраст, '', с какого числа, до, ...]
            name, role = cells[2], cells[3]
            since = cells[6] if len(cells) > 6 else ""
            rows.append({"section": section, "name": name, "role": role, "since": since,
                         "profile": ("https://www.transfermarkt.com" + name_a["href"]) if name_a else url,
                         "page": url})
    return rows


def main():
    out = []
    today = dt.date.today().isoformat()
    for tm_id, (slug, ru) in CLUBS.items():
        try:
            rows = staff(tm_id, slug)
        except Exception as e:
            print(ru, "ошибка:", e, file=sys.stderr)
            continue
        for r in rows:
            if KEEP.search(r["role"]) and not SKIP.search(r["role"]):
                out.append({"org": ru, **r, "fetched": today})
        print(ru, len(rows))
        time.sleep(6)
    path = os.path.join(HERE, "data", "people_tm.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["org", "section", "name", "role", "since", "profile", "page", "fetched"])
        w.writeheader()
        w.writerows(out)
    print("→", path, len(out))


if __name__ == "__main__":
    main()
