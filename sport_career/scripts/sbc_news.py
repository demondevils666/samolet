# -*- coding: utf-8 -*-
"""Лента новостей журнала СБК (s-bc.ru) по рубрикам: заголовок, лид, дата, ссылка.

Нужна для карты спонсорских сделок и спецпроектов букмекеров. Только публичные страницы,
пауза между запросами. Год в списке не пишется: восстанавливаем его по порядку дат
(лента идет от новых к старым), а для важных статей дату берем со страницы статьи.

Запуск: python sbc_news.py [--since 2025-01-01] [--rubrics 17,58,1]
Результат: data/sbc_news.csv
"""
import argparse
import csv
import datetime as dt
import os
import re
import time

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MONTHS = {m: i for i, m in enumerate(["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
                                      "сентября", "октября", "ноября", "декабря"], 1)}
RUBRICS = {17: "Соглашения и сделки", 58: "Реклама и маркетинг", 1: "Назначения и отставки",
           2: "Выставки и конференции", 40: "Образование и карьера", 59: "Технологии"}


def get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
            time.sleep(1.0)
            if r.status_code == 200:
                return r.text
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def parse_list(page_html):
    soup = BeautifulSoup(page_html, "lxml")
    items = []
    for h4 in soup.find_all("h4"):
        a = h4.find("a", href=re.compile(r"^https?://s-bc\.ru/(news|articles)/"))
        if not a:
            continue
        box = h4.parent
        date = box.select_one(".text-date")
        lead = box.select_one(".copyright-content")
        rub = box.find("a", href=re.compile(r"/rubric/\d+"))
        items.append({"title": a.get_text(" ", strip=True), "url": a["href"],
                      "lead": lead.get_text(" ", strip=True) if lead else "",
                      "date_raw": date.get_text(" ", strip=True) if date else "",
                      "item_rubric": rub.get_text(" ", strip=True) if rub else ""})
    return items


def crawl(rubric, since, max_pages=120):
    out, year, prev_month = [], dt.date.today().year, 13
    for page in range(1, max_pages + 1):
        html = get(f"https://s-bc.ru/rubric/{rubric}?page={page}")
        if not html:
            break
        items = parse_list(html)  # в рубрике у новости может быть другой основной ярлык, не фильтруем
        if not items:
            break
        stop = False
        for it in items:
            m = re.match(r"(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?", it["date_raw"])
            if not m or m.group(2) not in MONTHS:
                continue
            month = MONTHS[m.group(2)]
            if m.group(3):
                year = int(m.group(3))
            elif month > prev_month:
                year -= 1  # перешли через Новый год вниз по ленте
            prev_month = month
            d = dt.date(year, month, int(m.group(1)))
            it["date"] = d.isoformat()
            it["rubric"] = RUBRICS.get(rubric, str(rubric))
            if d < since:
                stop = True
                break
            out.append(it)
        print(f"rubric {rubric} page {page}: {len(out)} items, last {out[-1]['date'] if out else '-'}", flush=True)
        if stop:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--rubrics", default="17,58,1")
    a = ap.parse_args()
    since = dt.date.fromisoformat(a.since)
    rows = []
    for r in [int(x) for x in a.rubrics.split(",")]:
        rows += crawl(r, since)
    path = os.path.join(HERE, "data", "sbc_news.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "rubric", "item_rubric", "title", "lead", "url"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("→", path, len(rows))


if __name__ == "__main__":
    main()
