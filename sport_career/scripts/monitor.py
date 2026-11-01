# -*- coding: utf-8 -*-
"""Монитор вакансий на стыке спорта и аналитики / стратегии / коммерции / продукта.

Источники:
  * hh.ru: через api.hh.ru, если задан HH_TOKEN, иначе через публичную выдачу hh.ru/search/vacancy
    (без логина; если hh покажет капчу, скрипт остановит hh и напишет об этом, обходить не будет);
  * Яндекс (yandex.ru/jobs/api/publications), Хабр Карьера, getmatch (их публичные списки).

Запуск:   python monitor.py            # все источники, только новые вакансии в out/new_<дата>.md
          python monitor.py --all      # показать все актуальные, а не только новые
          python monitor.py --sources hh,yandex --max-pages 2
Состояние (id уже виденных) хранится в state/seen.json.
"""
import argparse
import csv
import datetime as dt
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state", "seen.json")
OUT = os.path.join(HERE, "out")
TODAY = dt.date.today().isoformat()

FIELDS = ["id", "source", "category", "title", "employer", "city", "work_format", "employment",
          "salary_from", "salary_to", "currency", "gross", "salary_text", "experience",
          "requirements", "url", "published", "query", "fit", "fit_reason", "first_seen"]

session = requests.Session()
session.headers["User-Agent"] = C.USER_AGENT


class Blocked(Exception):
    """Сайт показал капчу/запрет: прекращаем работу с ним."""


def get(url, params=None, headers=None, tries=4, as_json=False):
    for i in range(tries):
        try:
            r = session.get(url, params=params, headers=headers, timeout=40)
            if r.status_code in (403, 429) or "captcha" in r.url.lower():
                raise Blocked(f"{r.status_code} {r.url}")
            r.raise_for_status()
            time.sleep(C.REQUEST_PAUSE_SEC)
            return r.json() if as_json else r.text
        except Blocked:
            raise
        except Exception as e:  # сетевые сбои: повтор с паузой
            if i == tries - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** (i + 1))


# ----------------------------------------------------------------------------- hh.ru
def _hh_state(page_html):
    m = re.search(r'<template style="display:none" id="HH-Lux-InitialState">(.*?)</template>',
                  page_html or "", re.S)
    if not m:
        raise Blocked("на странице hh нет данных (капча или смена верстки)")
    return json.loads(htmlmod.unescape(m.group(1)))


def _fmt_list(v, key):
    try:
        return [x for el in v for x in el.get(key, [])]
    except Exception:
        return []


def _norm_hh_web(v, query):
    comp = v.get("compensation") or {}
    wf = _fmt_list(v.get("workFormats") or [], "workFormatsElement")
    emp_form = v.get("employmentForm") or (v.get("employment") or {}).get("@type")
    return {
        "id": f"hh:{v['vacancyId']}", "source": "hh.ru", "title": v.get("name", ""),
        "employer": (v.get("company") or {}).get("visibleName") or (v.get("company") or {}).get("name", ""),
        "employer_id": (v.get("company") or {}).get("id"),
        "city": (v.get("area") or {}).get("name", ""),
        "work_format_raw": wf, "employment_raw": emp_form, "internship": bool(v.get("internship")),
        "salary_from": comp.get("from"), "salary_to": comp.get("to"),
        "currency": comp.get("currencyCode"), "gross": comp.get("gross"),
        "salary_mode": comp.get("mode"),
        "experience": v.get("workExperience", ""),
        "url": f"https://hh.ru/vacancy/{v['vacancyId']}",
        "published": ((v.get("publicationTime") or {}).get("$") or "")[:10],
        "query": query, "description": "",
    }


def _norm_hh_api(v, query):
    sal = v.get("salary") or v.get("salary_range") or {}
    wf = [x.get("id") for x in (v.get("work_format") or [])]
    return {
        "id": f"hh:{v['id']}", "source": "hh.ru (API)", "title": v.get("name", ""),
        "employer": (v.get("employer") or {}).get("name", ""),
        "employer_id": (v.get("employer") or {}).get("id"),
        "city": (v.get("area") or {}).get("name", ""),
        "work_format_raw": wf,
        "employment_raw": ((v.get("employment_form") or v.get("employment") or {}).get("id") or "").upper(),
        "internship": bool(v.get("internship")),
        "salary_from": sal.get("from"), "salary_to": sal.get("to"), "currency": sal.get("currency"),
        "gross": sal.get("gross"), "salary_mode": ((sal.get("mode") or {}).get("id") or "MONTH").upper(),
        "experience": (v.get("experience") or {}).get("id", ""),
        "url": v.get("alternate_url"), "published": (v.get("published_at") or "")[:10],
        "query": query,
        "description": " ".join(filter(None, [(v.get("snippet") or {}).get("requirement"),
                                               (v.get("snippet") or {}).get("responsibility")])),
    }


def hh_search(params, query_label, max_pages, token=None):
    out = []
    for page in range(max_pages):
        if token:
            p = dict(params, per_page=100, page=page)
            if "employer_id" not in p:
                p.setdefault("area", 113)
            d = get("https://api.hh.ru/vacancies", params=p, as_json=True,
                    headers={"Authorization": f"Bearer {token}", "HH-User-Agent": C.API_USER_AGENT})
            if not d:
                break
            out += [_norm_hh_api(v, query_label) for v in d.get("items", [])]
            if page + 1 >= d.get("pages", 0):
                break
        else:
            p = dict(params, items_on_page=100, page=page, order_by="publication_time")
            if "employer_id" not in p:
                p.setdefault("area", 113)
            page_html = get("https://hh.ru/search/vacancy?" + urllib.parse.urlencode(p))
            if page_html is None:
                break
            vs = _hh_state(page_html)["vacancySearchResult"]
            items = vs.get("vacancies") or []
            out += [_norm_hh_web(v, query_label) for v in items]
            nxt = (vs.get("paging") or {}).get("next") or {}
            if not items or nxt.get("disabled", True):
                break
    return out


def hh_details(vac, token=None):
    """Описание вакансии: для фильтра по спорт-контексту и строки требований."""
    vid = vac["id"].split(":")[1]
    if token:
        d = get(f"https://api.hh.ru/vacancies/{vid}", as_json=True,
                headers={"Authorization": f"Bearer {token}", "HH-User-Agent": C.API_USER_AGENT})
        return (d or {}).get("description", "")
    page_html = get(f"https://hh.ru/vacancy/{vid}")
    if not page_html:
        return ""
    st = _hh_state(page_html)
    try:
        return st["vacancyView"]["vacancyFull"]["vacancy"].get("description", "")
    except Exception:
        return ""


# ----------------------------------------------------------------------------- прочие сайты
def yandex_jobs():
    out, url = [], "https://yandex.ru/jobs/api/publications?page_size=100"
    while url:
        d = get(url, as_json=True)
        if not d:
            break
        for x in d.get("results", []):
            svc = (x.get("public_service") or {}).get("name", "")
            vac = x.get("vacancy") or {}
            out.append({
                "id": f"yandex:{x['id']}", "source": "yandex.ru/jobs", "title": x.get("title", ""),
                "employer": f"Яндекс / {svc}", "employer_id": None,
                "city": ", ".join(c.get("name", "") for c in vac.get("cities", [])),
                "work_format_raw": [w.get("slug", "") for w in vac.get("work_modes", [])],
                "employment_raw": "", "internship": False,
                "salary_from": None, "salary_to": None, "currency": None, "gross": None, "salary_mode": None,
                "experience": "", "url": f"https://yandex.ru/jobs/vacancies/{x.get('publication_slug_url')}",
                "published": (x.get("modified") or "")[:10], "query": "yandex: все публикации",
                "description": x.get("short_summary") or "", "service": svc,
            })
        nxt = d.get("next")
        url = ("https://yandex.ru" + nxt) if nxt else None
    return out


def habr_career(queries=("спорт", "sport", "футбол", "хоккей", "fantasy", "букмекер", "ставки"), max_pages=3):
    out = []
    for q in queries:
        for page in range(1, max_pages + 1):
            page_html = get("https://career.habr.com/vacancies", params={"q": q, "type": "all", "page": page})
            if not page_html:
                break
            soup = BeautifulSoup(page_html, "lxml")
            data = None
            for sc in soup.find_all("script", type="application/json"):
                if sc.string and '"vacancies"' in sc.string:
                    data = json.loads(sc.string)
                    break
            lst = ((data or {}).get("vacancies") or {}).get("list") or []
            for x in lst:
                sal = x.get("salary") or {}
                out.append({
                    "id": f"habr:{x['id']}", "source": "career.habr.com", "title": x.get("title", ""),
                    "employer": (x.get("company") or {}).get("title", ""), "employer_id": None,
                    "city": ", ".join(l.get("title", "") for l in (x.get("locations") or [])),
                    "work_format_raw": ["REMOTE"] if x.get("remoteWork") else [],
                    "employment_raw": (x.get("employment") or "").upper(), "internship": False,
                    "salary_from": sal.get("from"), "salary_to": sal.get("to"),
                    "currency": (sal.get("currency") or "").upper() or None, "gross": None, "salary_mode": "MONTH",
                    "experience": x.get("qualification") or "",
                    "url": "https://career.habr.com" + x.get("href", ""),
                    "published": ((x.get("publishedDate") or {}).get("date") or "")[:10],
                    "query": f"habr: {q}",
                    "description": " ".join(s.get("title", "") for s in (x.get("skills") or [])),
                })
            meta = ((data or {}).get("vacancies") or {}).get("meta") or {}
            if page >= (meta.get("totalPages") or 1):
                break
    return out


def getmatch(queries=("спорт", "sport", "футбол", "fantasy", "betting", "ставки"), limit=100, max_pages=3):
    out = []
    for q in queries:
        for page in range(max_pages):
            d = get("https://getmatch.ru/api/offers", params={"q": q, "limit": limit, "offset": page * limit},
                    as_json=True)
            if not d:
                break
            for o in d.get("offers", []):
                comp = o.get("company") or {}
                out.append({
                    "id": f"getmatch:{o['id']}", "source": "getmatch.ru", "title": o.get("position", ""),
                    "employer": comp.get("name", "") if isinstance(comp, dict) else str(comp), "employer_id": None,
                    "city": ", ".join(l.get("label", "") for l in (o.get("location_items") or [])),
                    "work_format_raw": [l.get("format", "") for l in (o.get("location_items") or [])],
                    "employment_raw": "", "internship": False,
                    "salary_from": o.get("salary_display_from"), "salary_to": o.get("salary_display_to"),
                    "currency": (o.get("salary_currency") or None), "gross": (o.get("salary_taxes") == "gross")
                    if o.get("salary_display_from") or o.get("salary_display_to") else None, "salary_mode": "MONTH",
                    "experience": "", "url": "https://getmatch.ru" + (o.get("url") or ""),
                    "published": (o.get("published_at") or "")[:10], "query": f"getmatch: {q}",
                    "description": re.sub("<[^>]+>", " ", o.get("offer_description") or ""),
                })
            if (page + 1) * limit >= (d.get("meta") or {}).get("total", 0):
                break
    return out


# ----------------------------------------------------------------------------- классификация
SPORT_EMP_IDS = {e[0]: e for e in C.HH_EMPLOYERS}


def low(s):
    return (s or "").lower()


def is_betting(v):
    emp = low(v["employer"])
    if v.get("employer_id") in SPORT_EMP_IDS and SPORT_EMP_IDS[v["employer_id"]][2] == "betting":
        return True
    for w in C.BETTING_EMPLOYER_WORDS:
        if w in emp:
            if w in C.BETTING_AMBIGUOUS:
                ctx = emp + " " + low(v.get("description"))[:3000]
                if any(c in ctx for c in C.BETTING_CONTEXT) and "страхов" not in emp:
                    return True
            else:
                return True
    return False


def desc_hits(v):
    desc = low(BeautifulSoup(v.get("description") or "", "lxml").get_text(" "))
    return [w for w in C.SPORT_DESC_STRONG if has_word(desc, w)]


def sport_signal(v):
    """0 = нет спорта, 1 = спорт только в описании, 2 = спортивный работодатель или спорт в названии."""
    emp = low(v["employer"])
    if any(w in emp for w in C.SPORT_EMPLOYER_STOP):
        return 0
    if v.get("employer_id") in SPORT_EMP_IDS and SPORT_EMP_IDS[v["employer_id"]][2] not in ("media",):
        return 2
    title = low(v["title"])
    if any(has_word(title, w) for w in C.SPORT_TITLE) or any(has_word(emp, w) for w in ("спорт", "sport")):
        return 2
    if v["source"] == "yandex.ru/jobs":
        return 0
    return 1 if len(desc_hits(v)) >= C.SPORT_DESC_MIN_HITS else 0


def has_word(text, w):
    """Слово/начало слова (граница слева): "водител" не ловит "руководитель"."""
    return re.search(r"(?<![а-яёa-z])" + re.escape(w), text) is not None


def role_ok(v):
    t = low(v["title"])
    if any(has_word(t, w) for w in C.EXCLUDE_TITLE):
        return False
    return any(w in t for w in C.ROLE_TITLE)


def work_format(v):
    raw = [low(x) for x in v.get("work_format_raw") or []]
    if any("remote" in x for x in raw):
        return "удаленка" + (" / гибрид" if any("hybrid" in x or "mixed" in x for x in raw) else "")
    if any("hybrid" in x or "mixed" in x for x in raw):
        return "гибрид"
    if any("on_site" in x or "office" in x for x in raw):
        return "офис"
    return ""


def employment(v):
    t = low(v["title"])
    raw = low(v.get("employment_raw"))
    if v.get("internship") or "стаж" in t or "intern" in t:
        return "стажировка"
    if "part" in raw:
        return "парт-тайм"
    if "project" in raw:
        return "проект"
    if "full" in raw:
        return "фулл"
    return ""


def salary_text(v):
    f, t, c = v.get("salary_from"), v.get("salary_to"), v.get("currency") or ""
    if not f and not t:
        return ""
    cur = {"RUR": "₽", "RUB": "₽"}.get(str(c).upper(), c)
    rng = f"{int(f):,}".replace(",", " ") if f else ""
    if t:
        rng = (rng + "–" if rng else "до ") + f"{int(t):,}".replace(",", " ")
    elif f:
        rng = "от " + rng
    tax = " до вычета" if v.get("gross") is True else (" на руки" if v.get("gross") is False else "")
    mode = "" if (v.get("salary_mode") or "MONTH") == "MONTH" else f" ({v.get('salary_mode')})"
    return f"{rng} {cur}{tax}{mode}".strip()


REQ_HEAD = re.compile(r"(требован|ожида|что нужно|нам важно|кого мы ищем|вы нам подходите|подойд|"
                      r"необходим|мы ждем|мы ждём|для нас важно|ищем человека|requirements|you have)", re.I)


def requirements(desc_html):
    if not desc_html:
        return ""
    soup = BeautifulSoup(desc_html, "lxml")
    items = []
    for tag in soup.find_all(["p", "strong", "b", "h3", "h2"]):
        if REQ_HEAD.search(tag.get_text(" ", strip=True)):
            ul = tag.find_next("ul")
            if ul:
                items = [li.get_text(" ", strip=True) for li in ul.find_all("li")][:2]
                break
    if not items:
        lis = [li.get_text(" ", strip=True) for li in soup.find_all("li")]
        items = [x for x in lis if re.search(r"опыт|знан|умени|владен|образован|студент|курс", x, re.I)][:2]
    txt = "; ".join(items) if items else soup.get_text(" ", strip=True)[:200]
    return (txt[:260] + "…") if len(txt) > 260 else txt


def fit(v):
    """Эвристика 1–5. Финальные оценки в xlsx проверены вручную (data/fit_overrides.csv)."""
    if v["category"] == "беттинг":
        return 2, "беттинг: по навыкам подходит, но сейчас против твоего желания"
    t = low(v["title"])
    score, why_plus, why_minus = 2, [], []
    for w, s in C.FIT_PLUS.items():
        if w in t:
            score += s
            why_plus.append(w)
    for w, s in C.FIT_MINUS.items():
        if w in t:
            score -= s
            why_minus.append(w)
    score -= C.EXPERIENCE_PENALTY.get(v.get("experience"), 0)
    if v.get("experience") in C.EXPERIENCE_PENALTY:
        why_minus.append("опыт 3+ лет")
    if v.get("sport") == 2:
        score += 1
    city, wf = low(v.get("city")), low(v.get("work_format"))
    if city and "москва" not in city and "удален" not in wf:
        score -= 1
        why_minus.append("офис не в Москве")
    score = max(1, min(5, score))
    why = []
    if why_plus:
        why.append("плюс: " + ", ".join(why_plus[:3]))
    if why_minus:
        why.append("минус: " + ", ".join(why_minus[:3]))
    return score, "; ".join(why) or "нейтрально"


# ----------------------------------------------------------------------------- основной цикл
def collect(sources, max_pages, details=True):
    token = os.environ.get("HH_TOKEN")
    raw, notes = [], []
    if "hh" in sources:
        try:
            print(f"hh.ru: {'API с токеном' if token else 'публичная выдача (HH_TOKEN не задан)'}")
            for eid, label, cat in C.HH_EMPLOYERS:
                raw += hh_search({"employer_id": eid}, f"работодатель: {label}", max_pages, token)
            for label, q in C.HH_QUERIES:
                raw += hh_search({"text": q}, label, max_pages, token)
        except Blocked as e:
            notes.append(f"hh.ru остановлен: {e}. Капчу не обходим: запусти позже или задай HH_TOKEN.")
            print(notes[-1], file=sys.stderr)
    if "yandex" in sources:
        raw += yandex_jobs()
    if "habr" in sources:
        raw += habr_career()
    if "getmatch" in sources:
        raw += getmatch()
    print(f"сырых записей: {len(raw)}")
    with open(os.path.join(OUT, f"raw_{TODAY}.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in r.items() if k != "description"} for r in raw], f, ensure_ascii=False)

    # дедуп (одна вакансия могла прийти из нескольких запросов)
    uniq = {}
    for v in raw:
        if v["id"] in uniq:
            if v["query"] not in uniq[v["id"]]["query"]:
                uniq[v["id"]]["query"] += " | " + v["query"]
        else:
            uniq[v["id"]] = v
    cands = [v for v in uniq.values() if role_ok(v)]

    # Яндекс: берем только Плюс Фантех / Кинопоиск / Плюс и всё со спортом в названии
    def yandex_keep(v):
        if v["source"] != "yandex.ru/jobs":
            return True
        svc = low(v.get("service"))
        return any(w in svc for w in ("фантех", "кинопоиск", "плюс", "музык")) or \
            any(has_word(low(v["title"]), w) for w in ("спорт", "sport"))
    cands = [v for v in cands if yandex_keep(v)]

    hh_blocked = False
    for v in cands:
        if details and v["source"].startswith("hh.ru") and not hh_blocked:
            try:
                v["description"] = hh_details(v, token) or v.get("description", "")
            except Blocked as e:
                hh_blocked = True
                notes.append(f"описания hh не догружены: {e}")
        v["sport"] = sport_signal(v)
        v["category"] = "беттинг" if is_betting(v) else ("спорт" if v["sport"] else "")
        if v["source"] == "yandex.ru/jobs" and not v["category"]:
            v["category"] = "смежное (Плюс Фантех/Яндекс)"
        if not v["category"] and (SPORT_EMP_IDS.get(v.get("employer_id"), (0, 0, ""))[2] == "media"
                                  or any(w in low(v["employer"]) for w in C.MEDIA_EMPLOYER_WORDS)):
            v["category"] = "смежное (спортмедиа/стриминг)"
    keep = [v for v in cands if v["category"]]
    for v in keep:
        v["work_format"] = work_format(v)
        v["employment"] = employment(v)
        v["salary_text"] = salary_text(v)
        v["requirements"] = requirements(v.get("description")) if v["source"].startswith("hh.ru") \
            else (v.get("description") or "")[:260]
        v["fit"], v["fit_reason"] = fit(v)
    return keep, notes


def load_seen():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=0, sort_keys=True)


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_md(path, rows, notes, only_new):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {'Новые' if only_new else 'Все актуальные'} вакансии на {TODAY}: {len(rows)}\n\n")
        for n in notes:
            f.write(f"> {n}\n\n")
        for cat in ("спорт", "смежное (Плюс Фантех/Яндекс)", "смежное (спортмедиа/стриминг)", "беттинг"):
            part = [r for r in rows if r["category"] == cat]
            if not part:
                continue
            f.write(f"## {cat} ({len(part)})\n\n| фит | вакансия | работодатель | город / формат | вилка | дата |\n"
                    "|---|---|---|---|---|---|\n")
            for r in sorted(part, key=lambda r: (-r["fit"], r["published"]), reverse=False):
                f.write(f"| {r['fit']} | [{r['title']}]({r['url']}) | {r['employer']} | "
                        f"{r['city']} {('/ ' + r['work_format']) if r['work_format'] else ''} "
                        f"{('/ ' + r['employment']) if r['employment'] else ''} | {r['salary_text']} | "
                        f"{r['published']} |\n")
            f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", default="hh,yandex,habr,getmatch")
    ap.add_argument("--max-pages", type=int, default=3, help="страниц выдачи на запрос (по 100)")
    ap.add_argument("--all", action="store_true", help="в отчет попадают все, а не только новые")
    ap.add_argument("--no-details", action="store_true", help="не открывать карточки hh (быстрее, хуже фильтр)")
    ap.add_argument("--dry-run", action="store_true", help="не обновлять state/seen.json")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    rows, notes = collect(set(a.sources.split(",")), a.max_pages, details=not a.no_details)
    seen = load_seen()
    for r in rows:
        r["first_seen"] = seen.get(r["id"], TODAY)
    new = [r for r in rows if r["id"] not in seen]

    write_csv(os.path.join(OUT, "current.csv"), rows)
    report = rows if a.all else new
    write_csv(os.path.join(OUT, f"new_{TODAY}.csv"), new)
    write_md(os.path.join(OUT, f"{'all' if a.all else 'new'}_{TODAY}.md"), report, notes, not a.all)
    if not a.dry_run:
        for r in rows:
            seen.setdefault(r["id"], TODAY)
        save_seen(seen)
    print(f"актуальных: {len(rows)}, новых: {len(new)} → out/{'all' if a.all else 'new'}_{TODAY}.md")
    for n in notes:
        print("NB:", n)


if __name__ == "__main__":
    main()
