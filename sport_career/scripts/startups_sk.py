# -*- coding: utf-8 -*-
"""Стартапы СпортТех Сколково (1-й поток осень 2025, 2-й поток весна 2026) и номинанты премии
«Лидеры индустрии» 2026 (leaders.sk.ru).

Каталог акселератора (awards.sporttech.sk.ru) рисуется на клиенте, но данные лежат в публичном
JS-бандле сайта как JSON: название, описание, трек, сайт, one-pager, статус (победитель/финалист/
участник), запрос проекта, представитель. Личные контакты представителей (почта, Telegram) не
сохраняем: в таблицу идут сайт проекта и ссылка на каталог.

Запуск: python startups_sk.py  -> data/v2/startups_sk.csv, data/v2/leaders_2026.csv
"""
import ast
import csv
import datetime as dt
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "v2")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TRACKS = {"business": "Бизнес-решения", "digital": "Цифровые технологии", "mass": "Массовый спорт",
          "fitness": "Фитнес", "medicine": "Спортивная медицина", "infrastructure": "Инфраструктура",
          "media": "Медиа", "esports": "Киберспорт"}
BADGE = {"winner": "победитель", "finalist": "финалист", "participant": "участник"}
# Шаблон «чем я мог бы помочь» по треку: это гипотеза-предложение, а не факт о проекте
HELP = {
    "business": "Карта клиентов (клубы, лиги, школы), кто реально платит и сколько; разбор конкурентов",
    "digital": "Размер рынка и кто покупатель (клуб/федерация/любитель); конкуренты и цена",
    "mass": "Юнит-экономика B2C (CAC, удержание, LTV) и партнерства с брендами для привлечения",
    "fitness": "Экономика клуба/подписки и сравнение с сетями; каналы привлечения",
    "medicine": "Кто покупатель (клубы, клиники, B2C), регуляторика и цена; пилоты в клубах",
    "infrastructure": "Модель загрузки и окупаемость объекта; B2G/B2B-продажи",
    "media": "Монетизация аудитории: спонсорские пакеты, рекламодатели, беттинг-категория",
    "esports": "Аудитория и монетизация; кто спонсирует (банки, беттинг, телеком)",
}


def get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
            time.sleep(1.0)
            if r.status_code == 200:
                return r.text
        except Exception:
            time.sleep(3 * (i + 1))
    return ""


def accelerator():
    html = get("https://awards.sporttech.sk.ru/2026/")
    chunks = sorted(set(re.findall(r"_next/static/chunks/[A-Za-z0-9_\-/]+\.js", html)))
    rows = []
    for c in chunks:
        js = get("https://awards.sporttech.sk.ru/" + c)
        for m in re.finditer(r"(\d+):function\(e\)\{e\.exports=JSON\.parse\('(.*?)'\)\}", js, re.S):
            data = json.loads(ast.literal_eval("'" + m.group(2) + "'"))
            if not data or "badgeClassId" not in data[0]:
                continue
            cohort = "2-й поток (весна 2026)" if any(x.get("presentationPreview", "").startswith("/cohorts/2026")
                                                     for x in data) else "1-й поток (осень 2025)"
            year = "2026" if cohort.startswith("2") else "2025"
            for x in data:
                req = (x.get("request") or "").strip().replace("\r", " ").replace("\n", " ")
                rows.append({
                    "source": "СпортТех Сколково", "cohort": cohort, "status": BADGE.get(x["badgeClassId"], x["badgeClassId"]),
                    "track": TRACKS.get(x.get("trackId"), x.get("trackId")), "name": x["name"],
                    "what": (x.get("tagline") or x.get("description") or "").strip()[:300],
                    "stage": ("Запрос проекта: " + req[:200]) if req else "нет данных",
                    "team": (x.get("representative") or {}).get("name", ""),
                    "site": x.get("website") or "", "one_pager": x.get("onePager") or "",
                    "catalog": f"https://awards.sporttech.sk.ru/{year}/#projects-catalog",
                    "help": HELP.get(x.get("trackId"), "Рынок, конкуренты, юнит-экономика")
                            + ("; плюс инвест-обоснование под запрос" if re.search(r"инвест|млн|доли|%", req, re.I) else ""),
                    "checked": dt.date.today().isoformat(),
                })
    return rows


def leaders():
    html = get("https://leaders.sk.ru/")
    soup = BeautifulSoup(html, "lxml")
    rows = []
    track_names = {"professional-sport": "Профессиональный спорт", "amateur-sport": "Любительский спорт",
                   "fitness": "Фитнес", "esports-phygital": "Киберспорт и фиджитал",
                   "sports-medicine": "Спортивная медицина", "student-startup": "Студенческий стартап (спецноминация)"}
    for c in soup.select("li.nd-card"):
        a = c.select_one(".nd-card__name a")
        if not a:
            continue
        href = a.get("href", "")
        track = href.split("/")[1] if href.count("/") >= 2 else ""
        kick = c.select_one(".nd-card__kicker")
        text = c.select_one(".nd-detail__text") or c.select_one(".nd-card__text")
        site = c.select_one("a.nd-card__site") or c.select_one(".nd-card__site a")
        by = [x.get_text(" ", strip=True) for x in c.select(".nd-by__name")] or \
             [x.get_text(" ", strip=True) for x in c.select(".nd-detail__person span:last-child")]
        uni = c.get("data-uni", "")
        rows.append({
            "source": "Лидеры индустрии 2026", "track": track_names.get(track, track),
            "nomination": kick.get_text(" ", strip=True) if kick else "",
            "name": a.get_text(" ", strip=True),
            "what": (text.get_text(" ", strip=True) if text else "")[:300],
            "nominated_by": ", ".join(dict.fromkeys(by)),
            "university": uni,
            "site": (site.get("href") if site and site.name == "a" else "") or "",
            "page": "https://leaders.sk.ru/" + href,
            "checked": dt.date.today().isoformat(),
        })
    return rows


def save(rows, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("→", path, len(rows))


if __name__ == "__main__":
    save(accelerator(), "startups_sk.csv")
    save(leaders(), "leaders_2026.csv")
