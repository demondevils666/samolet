# -*- coding: utf-8 -*-
"""Собирает ../sport_career.xlsx из результатов monitor.py (out/current.csv, out/raw_*.json)
и ручных справочников data/*.csv (люди, события, каналы, ручные оценки фита).

Запуск: python build_xlsx.py   (после python monitor.py)
"""
import csv
import glob
import json
import os
import statistics as st
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monitor as M  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_XLSX = os.path.join(os.path.dirname(HERE), "sport_career.xlsx")
NDFL = 0.87  # gross -> на руки (13%), упрощение

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(bold=True, color="FFFFFF")
FIT_FILL = {5: "63BE7B", 4: "A9D08E", 3: "FFEB84", 2: "F8CBAD", 1: "E6B8B7"}
CONF_FILL = {"высокая": "A9D08E", "средняя": "FFEB84", "низкая": "F8CBAD"}


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def sheet(ws, headers, rows, widths, link_cols=(), wrap=True):
    ws.append(headers)
    for c in ws[1]:
        c.fill, c.font = HEAD_FILL, HEAD_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=wrap, vertical="top")
            if c.column in link_cols and isinstance(c.value, str) and c.value.startswith("http"):
                c.hyperlink = c.value
                c.font = Font(color="0563C1", underline="single")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


# ----------------------------------------------------------------------------- вакансии
CAT_ORDER = {"спорт": 0, "смежное (Плюс Фантех/Яндекс)": 1, "смежное (спортмедиа/стриминг)": 2, "беттинг": 3}


def vacancies():
    rows = read_csv(os.path.join(HERE, "out", "current.csv"))
    over = {r["id"]: r for r in read_csv(os.path.join(HERE, "data", "fit_overrides.csv"))}
    out = []
    for r in rows:
        o = over.get(r["id"])
        if o and o.get("exclude") == "1":
            continue
        if o:
            if o.get("fit"):
                r["fit"], r["fit_reason"] = o["fit"], o["fit_reason"]
            if o.get("category"):
                r["category"] = o["category"]
        elif r["category"] == "беттинг":
            r["fit_reason"] = "Беттинг: по навыкам может подойти, но сейчас против твоего желания"
        out.append(r)
    for m in read_csv(os.path.join(HERE, "data", "vacancies_manual.csv")):
        out.append(m)
    out.sort(key=lambda r: (CAT_ORDER.get(r["category"], 9), -int(r["fit"] or 0), r.get("published", "")))
    return out


def place(r):
    parts = [r.get("city", "")]
    if r.get("work_format"):
        parts.append(r["work_format"])
    return " / ".join(p for p in parts if p)


# ----------------------------------------------------------------------------- зарплаты
def monthly_net(v):
    f, t = v.get("salary_from"), v.get("salary_to")
    f = float(f) if f not in (None, "") else None
    t = float(t) if t not in (None, "") else None
    if f is None and t is None:
        return None
    mid = (f + t) / 2 if f and t else (f or t)
    gross = v.get("gross")
    if gross in (True, "True"):
        mid *= NDFL
    return round(mid)


def stats(vals):
    vals = sorted(vals)
    if not vals:
        return ["0", "—", "—", "—", "—", "—"]
    q = st.quantiles(vals, n=4) if len(vals) >= 4 else [None, None, None]
    fmt = lambda x: f"{int(x):,}".replace(",", " ") if x is not None else "—"
    return [str(len(vals)), fmt(st.median(vals)), fmt(q[0]), fmt(q[2]), fmt(vals[0]), fmt(vals[-1])]


def salary_rows(vac):
    # A. целевая выборка: лист «Вакансии»
    target = {"спорт": [], "беттинг": []}
    target_list = []
    for r in vac:
        cat = "беттинг" if r["category"].startswith("беттинг") else ("спорт" if r["category"] == "спорт" else None)
        if not cat or r["id"].startswith("manual:"):
            continue
        if (r.get("currency") or "RUR") not in ("RUR", "RUB", ""):
            continue
        n = monthly_net(r)
        if n:
            target[cat].append(n)
            target_list.append([cat, r["title"], r["employer"], r["salary_text"], n, r["url"]])
    # B. широкая выборка: все вакансии спортивных и беттинг-работодателей с вилкой из сырой выдачи
    raw_path = sorted(glob.glob(os.path.join(HERE, "out", "raw_*.json")))[-1]
    raw = {v["id"]: v for v in json.load(open(raw_path, encoding="utf-8"))}
    wide = {"клубы и лиги: офисные роли": [], "клубы и лиги: все роли": [], "беттинг: все роли": [],
            "беттинг: офис (по факту поддержка клиентов и бухгалтерия)": []}
    wide_list = []
    office_words = ("бухгалтер", "менеджер", "специалист", "аналит", "маркет", "юрис", "инженер",
                    "руковод", "директор", "заместител", "координатор", "hr", "продаж", "дизайн", "smm")
    for v in raw.values():
        if not v["source"].startswith("hh.ru") or (v.get("salary_mode") or "MONTH") != "MONTH":
            continue
        if (v.get("currency") or "RUR") not in ("RUR", "RUB"):
            continue
        n = monthly_net(v)
        if not n:
            continue
        emp_cat = M.SPORT_EMP_IDS.get(v.get("employer_id"), (0, 0, ""))[2]
        t = M.low(v["title"])
        office = any(w in t for w in office_words) and not any(M.has_word(t, w) for w in
                                                                ("кассир", "продавец", "официант", "уборщ", "повар",
                                                                 "мойщ", "бармен", "оператор", "вахтер", "слесар"))
        if emp_cat in ("rpl", "khl", "vtb", "league"):
            wide["клубы и лиги: все роли"].append(n)
            if office:
                wide["клубы и лиги: офисные роли"].append(n)
            wide_list.append(["клубы и лиги", v["title"], v["employer"], n, "офис" if office else "", v["url"]])
        elif M.is_betting(v):
            wide["беттинг: все роли"].append(n)
            if office:
                wide["беттинг: офис (по факту поддержка клиентов и бухгалтерия)"].append(n)
            wide_list.append(["беттинг", v["title"], v["employer"], n, "офис" if office else "", v["url"]])
    return target, target_list, wide, wide_list, os.path.basename(raw_path)


def build():
    vac = vacancies()
    wb = Workbook()

    # 1. Вакансии
    ws = wb.active
    ws.title = "Вакансии"
    rows = [[r["category"], int(r["fit"] or 0) or None, r["fit_reason"], r["title"], r["employer"], place(r),
             r.get("employment") or "", r.get("salary_text") or "нет", r.get("requirements") or "", r["url"],
             r.get("published", ""), r.get("source", "")] for r in vac]
    sheet(ws, ["Категория", "Фит 1–5", "Почему такой фит", "Вакансия", "Работодатель", "Город / удаленка",
               "Формат", "Вилка", "Требования (1–2 строки)", "Ссылка", "Дата публикации", "Источник"],
          rows, [14, 7, 48, 38, 26, 20, 11, 16, 55, 34, 12, 14], link_cols=(10,))
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        for c in row:
            if c.value in FIT_FILL:
                c.fill = PatternFill("solid", fgColor=FIT_FILL[c.value])

    # 2. Зарплаты
    ws = wb.create_sheet("Зарплаты")
    target, target_list, wide, wide_list, raw_name = salary_rows(vac)
    hdr = ["Выборка", "n", "Медиана, ₽/мес на руки", "P25", "P75", "Мин", "Макс"]
    ws.append(["Зарплаты по собранным вакансиям, 01.11.2026. Середина вилки; «до вычета» переведено в «на руки» "
               "умножением на 0,87; только вакансии в рублях с помесячной оплатой. P25/P75 считаются при n ≥ 4"])
    ws.append([])
    ws.append(["A. Целевая выборка: вакансии с листа «Вакансии» (аналитика, стратегия, коммерция, продукт)"])
    ws.append(hdr)
    for k in ("спорт", "беттинг"):
        ws.append([k] + stats(target[k]))
    tot = {k: sum(1 for r in vac if not r["id"].startswith("manual:") and
                  (r["category"].startswith("беттинг") if k == "беттинг" else r["category"] == "спорт"))
           for k in ("спорт", "беттинг")}
    ws.append([f"Вывод: в целевых ролях вилку почти не публикуют. Спорт: {len(target['спорт'])} из {tot['спорт']}, "
               f"беттинг: {len(target['беттинг'])} из {tot['беттинг']}, и это рутинные или нерелевантные позиции. "
               "Медиана по такой выборке ничего не говорит о цене аналитика"])
    ws.append([])
    ws.append(["Вакансии с вилкой из целевой выборки"])
    ws.append(["Категория", "Вакансия", "Работодатель", "Вилка как в вакансии", "Середина на руки", "Ссылка"])
    for r in target_list:
        ws.append(r)
    ws.append([])
    ws.append([f"B. Широкая выборка (ориентир уровня, не аналитики): все вакансии клубов, лиг и букмекеров "
               f"с вилкой из сырой выдачи hh ({raw_name})"])
    ws.append(hdr)
    for k, vals in wide.items():
        ws.append([k] + stats(vals))
    ws.append(["Офисные роли определены по словам в названии (бухгалтер, менеджер, специалист, инженер и т.п.) "
               "без кассиров, операторов, поваров и рабочих. Это фон для переговоров, а не цена аналитика"])
    ws.append([])
    ws.append(["Вакансии широкой выборки"])
    ws.append(["Группа", "Вакансия", "Работодатель", "Середина на руки", "Офисная?", "Ссылка"])
    for r in sorted(wide_list, key=lambda x: (x[0], -x[3])):
        ws.append(r)
    for i, w in enumerate([34, 48, 30, 22, 16, 40, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=False, vertical="top")
            if isinstance(c.value, str) and c.value.startswith("http"):
                c.hyperlink, c.font = c.value, Font(color="0563C1", underline="single")
            if c.value in ("Выборка", "Категория", "Группа") or (isinstance(c.value, str) and c.value[:2] in ("A.", "B.")):
                for cc in row:
                    cc.font = Font(bold=True)

    # 3. Люди
    ws = wb.create_sheet("Люди")
    ppl = read_csv(os.path.join(HERE, "data", "people.csv"))
    rows = [[p["org"], p["org_type"], p["name"], p["role"], p["role_group"], p["url"], p["source_date"],
             p["confidence"], p["public_channel"], p["note"], p["name_in_source"]] for p in ppl]
    sheet(ws, ["Организация", "Тип", "ФИО", "Роль", "Группа роли", "Ссылка на источник", "Дата источника",
               "Уверенность", "Публичный канал / выступления", "Комментарий", "Имя в источнике (лат.)"],
          rows, [22, 10, 22, 34, 14, 40, 18, 11, 34, 50, 18], link_cols=(6,))
    for row in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        for c in row:
            if c.value in CONF_FILL:
                c.fill = PatternFill("solid", fgColor=CONF_FILL[c.value])

    # 4. События и дедлайны
    ws = wb.create_sheet("События и дедлайны")
    ev = sorted(read_csv(os.path.join(HERE, "data", "events.csv")), key=lambda e: e["date"])
    rows = [[e["date"], e["date_status"], e["event"], e["type"], e["what_to_do"], e["cost_conditions"], e["url"],
             e["source_date"], e["note"]] for e in ev]
    sheet(ws, ["Дата", "Статус даты", "Событие", "Тип", "Что сделать", "Стоимость / условия", "Ссылка",
               "Дата источника", "Комментарий"], rows, [12, 16, 40, 10, 45, 40, 38, 18, 60], link_cols=(7,))

    # 5. Каналы
    ws = wb.create_sheet("Каналы")
    ch = read_csv(os.path.join(HERE, "data", "channels.csv"))
    rows = [[c["name"], c["url"], int(c["subscribers"]) if c["subscribers"] else None, c["last_post"], c["topic"],
             c["who"], c["kind"], c["note"]] for c in ch]
    sheet(ws, ["Название", "Ссылка", "Подписчики", "Последний пост", "О чем", "Кто ведет", "Тип", "Комментарий"],
          rows, [30, 30, 11, 13, 45, 40, 14, 55], link_cols=(2,))
    ws.append([])
    ws.append(["Подписчики и дата последнего поста взяты с публичных страниц t.me/s/<канал> 01.11.2026. tgstat.ru "
               "из контейнера отвечает 403 (антибот), его не обходил. Кандидатов искал обходом ссылок и репостов "
               "от стартовых каналов (scripts/tg_channels.py); ставочные и мертвые (3+ месяца без постов) отброшены"])

    wb.save(OUT_XLSX)
    print("→", OUT_XLSX, f"(вакансий: {len(vac)}, людей: {len(ppl)}, событий: {len(ev)}, каналов: {len(ch)})")


if __name__ == "__main__":
    build()
