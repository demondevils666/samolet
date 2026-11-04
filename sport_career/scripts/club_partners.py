# -*- coding: utf-8 -*-
"""Партнеры клубов с официальных сайтов: главная страница + страница «Партнеры», если есть.

Из блоков с партнерами берем подписи логотипов (alt/title) и внешние ссылки (домен партнера).
Это сырье: категории и уровни (титульный/генеральный/официальный) потом проставляются вручную
в data/sponsorship.csv со ссылкой на источник. Капчи и антиботы не обходим: если сайт
не отдал страницу, пишем это в status.

Запуск: python club_partners.py            -> data/club_partners_raw.csv
"""
import csv
import datetime as dt
import os
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

CLUBS = [
    # (лига, клуб, сайт)
    ("РПЛ", "Зенит", "https://fc-zenit.ru/"), ("РПЛ", "Спартак", "https://spartak.com/"),
    ("РПЛ", "ЦСКА", "https://pfc-cska.com/"), ("РПЛ", "Динамо Москва", "https://fcdynamo.ru/"),
    ("РПЛ", "Краснодар", "https://fckrasnodar.ru/"), ("РПЛ", "Локомотив", "https://www.fclm.ru/"),
    ("РПЛ", "Рубин", "https://rubin-kazan.ru/"), ("РПЛ", "Балтика", "https://fc-baltika.ru/"),
    ("РПЛ", "Ростов", "https://fc-rostov.ru/"), ("РПЛ", "Ахмат", "https://fc-akhmat.ru/"),
    ("РПЛ", "Акрон", "https://fcakron.ru/"), ("РПЛ", "Родина", "https://fcrodina.com/"),
    ("РПЛ", "Крылья Советов", "https://kc-camapa.ru/"), ("РПЛ", "Оренбург", "https://fcorenburg.ru/"),
    ("РПЛ", "Динамо Махачкала", "https://fcdinamomkh.ru/"), ("РПЛ", "Факел", "https://fakelfc.ru/"),
    ("КХЛ", "Металлург Мг", "https://metallurg.ru/"), ("КХЛ", "Авангард", "https://hawk.ru/"),
    ("КХЛ", "Локомотив", "https://www.hclokomotiv.ru/"), ("КХЛ", "Ак Барс", "https://www.ak-bars.ru/"),
    ("КХЛ", "Северсталь", "https://www.severstal-club.ru/"), ("КХЛ", "ЦСКА", "https://cska-hockey.ru/"),
    ("КХЛ", "Автомобилист", "https://www.hc-avto.ru/"), ("КХЛ", "СКА", "https://www.ska.ru/"),
    ("КХЛ", "Торпедо", "https://www.hctorpedo.ru/"), ("КХЛ", "Динамо Москва", "https://www.dynamo.ru/"),
    ("ВТБ", "ЦСКА", "https://cskabasket.com/"), ("ВТБ", "Зенит", "https://bc-zenit.com/"),
    ("ВТБ", "УНИКС", "https://www.unics.ru/"), ("ВТБ", "Локомотив-Кубань", "https://lokobasket.com/"),
    ("ВТБ", "Парма", "https://parmabasket.ru/"), ("ВТБ", "Автодор", "https://autodorbasket.ru/"),
    ("ВТБ", "Енисей", "https://bc-enisey.ru/"), ("ВТБ", "МБА-МАИ", "https://mba-basket.ru/"),
    ("ВТБ", "Самара", "https://bcsamara.ru/"), ("ВТБ", "Уралмаш", "https://uralmash-basket.ru/"),
    ("ВТБ", "Динамо Владивосток", "https://dynamo-vl.ru/"),
]
PARTNER_HINT = re.compile(r"(партн[её]р|спонсор|partner|sponsor)", re.I)
SKIP_DOMAINS = ("vk.com", "t.me", "youtube", "rutube", "ok.ru", "dzen", "yandex.ru/maps", "apple.com", "google",
                "max.ru", "instagram", "twitter", "x.com", "khl.ru", "premierliga.ru", "vtb-league.com",
                "metrika", "liveinternet", "tiktok", "telegram")


def get(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
        time.sleep(1.0)
        return r.status_code, r.text, r.url
    except Exception as e:
        return 0, "", str(e)[:80]


def partner_blocks(soup):
    """Элементы, похожие на блок партнеров: по классу/id или заголовку рядом."""
    blocks = []
    for el in soup.find_all(True, attrs={"class": PARTNER_HINT}):
        blocks.append(el)
    for el in soup.find_all(True, id=PARTNER_HINT):
        blocks.append(el)
    for h in soup.find_all(["h2", "h3", "h4", "div", "span"], string=PARTNER_HINT):
        par = h.find_parent(["section", "div", "footer"])
        if par:
            blocks.append(par)
    return blocks


def extract(block, base):
    names, domains = set(), set()
    for img in block.find_all("img"):
        for attr in ("alt", "title"):
            v = (img.get(attr) or "").strip()
            if 1 < len(v) < 60 and not re.search(r"(logo|лого|icon|image|img|\.png|\.svg)$", v, re.I):
                names.add(v)
    for a in block.find_all("a", href=True):
        href = urllib.parse.urljoin(base, a["href"])
        host = urllib.parse.urlparse(href).netloc.lower().replace("www.", "")
        if host and host not in urllib.parse.urlparse(base).netloc and not any(s in href for s in SKIP_DOMAINS):
            domains.add(host)
        t = (a.get("title") or a.get("aria-label") or "").strip()
        if 1 < len(t) < 60:
            names.add(t)
    return names, domains


def main():
    rows = []
    for league, club, url in CLUBS:
        code, html, final = get(url)
        pages = [(url, code, html, final)]
        if html:
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                if PARTNER_HINT.search(a.get_text(" ", strip=True) + " " + a["href"]):
                    purl = urllib.parse.urljoin(final, a["href"])
                    if urllib.parse.urlparse(purl).netloc == urllib.parse.urlparse(final).netloc and purl != final:
                        c2, h2, f2 = get(purl)
                        pages.append((purl, c2, h2, f2))
                        break
        names, domains = set(), set()
        for purl, c, h, f in pages:
            if not h:
                continue
            soup = BeautifulSoup(h, "lxml")
            for b in partner_blocks(soup):
                n, d = extract(b, f)
                names |= n
                domains |= d
        rows.append({"league": league, "club": club, "site": url,
                     "status": ";".join(f"{p[0]}={p[1]}" for p in pages),
                     "partner_names": " | ".join(sorted(names))[:2000],
                     "partner_domains": " | ".join(sorted(domains))[:2000],
                     "checked": dt.date.today().isoformat()})
        print(league, club, [p[1] for p in pages], len(names), len(domains), flush=True)
    path = os.path.join(HERE, "data", "club_partners_raw.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("→", path)


if __name__ == "__main__":
    main()
