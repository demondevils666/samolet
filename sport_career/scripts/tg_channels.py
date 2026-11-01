# -*- coding: utf-8 -*-
"""Поиск и проверка Telegram-каналов про спортивную аналитику / бизнес / спорттех.

Берем только публичные превью t.me/s/<канал> (без логина и без API Telegram):
название, описание, подписчики, даты последних постов. Новые кандидаты ищем "снежным комом":
каналы, на которые ссылаются или которые репостят стартовые каналы.

Запуск:  python tg_channels.py                # обход от стартовых каналов
         python tg_channels.py имя1 имя2      # проверить конкретные каналы
Результат: data/tg_channels.csv (все проверенные) — в xlsx идут только живые и тематические.
tgstat.ru из контейнера отвечает 403 (антибот), его не обходим.
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
TODAY = dt.date.today()

SEEDS = ["sbcru", "SportTechSkolkovo", "ikatanaev", "FNL_org", "sportbizinfo", "kickordie", "xgblocknote",
         "pgorodnitskiy", "nakarandasherus", "eventdata", "fitnessdataru"]
TOPIC = re.compile(r"(спортивн\w* (бизнес|индустр|маркетинг|аналитик|менеджмент|технолог|право|экономик)|"
                   r"бизнес\w* (в )?спорт|спорттех|sporttech|sport tech|sports? business|аналитик\w* (футбол|хоккей|"
                   r"баскет|спорт)|футбольн\w* аналит|xg\b|скаутинг|селекци|трансфер\w* (рын|аналит)|медиаправ|"
                   r"спонсорств|экономик\w* (футбол|спорт)|деньги в (футбол|спорт)|менеджмент\w* (футбол|спорт)|"
                   r"data|данн\w+ (в|о) спорт|спортивн\w+ данн|\bxg|expected goals|статистик\w* (футбол|матч|игрок)|"
                   r"аналитик|скаут|футбол\w*,? деньги|экономик|бизнес)", re.I)
BETTING = re.compile(r"(прогноз|каппер|ставк|ставоч|экспресс|коэфф|кф\b|vip|вип|букмекер|бетт|betting|"
                     r"проход|value ?bet|джекпот|казино|слот|фрибет)", re.I)
SKIP_HANDLES = {"share", "joinchat", "addstickers", "proxy", "iv", "s", "c", "addlist", "boost"}


def parse_count(s):
    s = s.replace(" ", "").replace(",", ".").upper()
    m = re.match(r"([\d.]+)([KM]?)", s)
    if not m:
        return None
    n = float(m.group(1))
    return int(n * (1000 if m.group(2) == "K" else 1_000_000 if m.group(2) == "M" else 1))


def fetch(handle):
    url = f"https://t.me/s/{handle}"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    except Exception as e:
        return {"handle": handle, "error": str(e)}
    time.sleep(1.0)
    if r.status_code != 200 or "tgme_channel_info" not in r.text:
        return {"handle": handle, "error": f"нет публичного превью (HTTP {r.status_code})"}
    soup = BeautifulSoup(r.text, "lxml")
    title = soup.select_one(".tgme_channel_info_header_title")
    desc = soup.select_one(".tgme_channel_info_description")
    subs = None
    for c in soup.select(".tgme_channel_info_counter"):
        if "subscriber" in c.get_text() or "подпис" in c.get_text():
            subs = parse_count(c.select_one(".counter_value").get_text())
    dates = [t.get("datetime", "")[:10] for t in soup.select(".tgme_widget_message_date time")]
    dates = sorted(d for d in dates if d)
    texts = " ".join(m.get_text(" ", strip=True) for m in soup.select(".tgme_widget_message_text"))
    links = set()
    for a in soup.select(".tgme_widget_message a[href]"):
        m = re.match(r"https?://t\.me/([A-Za-z0-9_]{4,})", a["href"])
        if m and m.group(1).lower() not in SKIP_HANDLES:
            links.add(m.group(1))
    last = dates[-1] if dates else ""
    days = (TODAY - dt.date.fromisoformat(last)).days if last else None
    return {
        "handle": handle, "url": f"https://t.me/{handle}",
        "title": title.get_text(" ", strip=True) if title else "",
        "description": desc.get_text(" ", strip=True)[:400] if desc else "",
        "subscribers": subs, "last_post": last, "days_since_last_post": days,
        "posts_on_page": len(dates), "first_post_on_page": dates[0] if dates else "",
        "topic_hit": bool(TOPIC.search((title.get_text() if title else "") + " " +
                                       (desc.get_text() if desc else "") + " " + texts[:6000])),
        "betting_hit": bool(BETTING.search((title.get_text() if title else "") + " " +
                                           (desc.get_text() if desc else ""))),
        "links": sorted(links), "checked": TODAY.isoformat(), "error": "",
    }


def crawl(seeds, max_channels=250, depth=2):
    seen, out, frontier = set(), [], [(s, 0) for s in seeds]
    while frontier and len(seen) < max_channels:
        h, d = frontier.pop(0)
        if h.lower() in seen:
            continue
        seen.add(h.lower())
        info = fetch(h)
        out.append(info)
        print(f"{h:30} {info.get('subscribers')} {info.get('last_post')} topic={info.get('topic_hit')} "
              f"bet={info.get('betting_hit')} {info.get('error', '')}", flush=True)
        # расширяем обход только от живых тематических не-ставочных каналов
        if d < depth and not info.get("error") and info.get("topic_hit") and not info.get("betting_hit"):
            frontier += [(l, d + 1) for l in info.get("links", []) if l.lower() not in seen]
    return out


def main():
    handles = sys.argv[1:]
    rows = [fetch(h) for h in handles] if handles else crawl(SEEDS)
    path = os.path.join(HERE, "data", "tg_channels_raw.csv")
    fields = ["handle", "url", "title", "description", "subscribers", "last_post", "days_since_last_post",
              "posts_on_page", "first_post_on_page", "topic_hit", "betting_hit", "checked", "error"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("→", path, len(rows))


if __name__ == "__main__":
    main()
