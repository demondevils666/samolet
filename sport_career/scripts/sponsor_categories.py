# -*- coding: utf-8 -*-
"""Матрица «категория спонсора × клуб» по спискам партнеров с сайтов клубов (data/club_partners_raw.csv).

Домены партнеров вручную разложены по категориям (CAT ниже). Для клубов КХЛ общий блок партнеров
лиги (одинаковый на всех клубных сайтах) вычитается, чтобы остались клубные партнеры.
«Пусто» значит: на сайте клуба 04.11.2026 партнера этой категории не видно. Это не гарантия, что
его нет: сайт может показывать не всех.
Запуск: python sponsor_categories.py -> data/v2/sponsor_categories.csv
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = {
    "банк/платежи": ["psbank", "vtb.ru", "akbars.ru", "alfabank", "tbank", "sovcombank", "gazprombank", "vamprivet"],
    "беттинг": ["fon.bet", "betcity", "leon.ru", "olimp.bet", "winline", "pari.ru", "betboom", "ligastavok"],
    "телеком": ["rt.ru", "megafon", "t2.ru", "ertelecom", "beeline", "mts.ru", "novikom"],
    "напитки/пиво": ["abinbevefes", "svyatoyistochnik", "senegskaya", "volzhanka", "iceberg-aqua", "tbauwater",
                     "napitkivmeste", "redfinch", "oznwater", "7ozerka", "bochkari", "coffee-like", "baltika"],
    "ритейл/FMCG": ["5ka.ru", "dixy", "lemanapro", "fix-price", "citilink", "chitai-gorod", "kitfort", "digma",
                    "dreametech", "haieronline", "dodopizza", "pizzburg", "ekoniva", "рексона", "komus", "demidich"],
    "маркетплейс": ["wildberries", "ozon", "market.yandex"],
    "авто/шины": ["lada.ru", "changanauto", "nf-motors", "borauto", "pangocars", "gislaved", "avbas"],
    "авиа": ["aeroflot", "rossiya-airlines", "s7.ru", "flyredwings"],
    "энергетика/промышленность": ["rosneft", "gazprom", "g-energy", "nnk.ru", "nornickel", "polymetal", "rosseti",
                                  "mrsk", "sibur", "neftemash", "akron-holding", "electroshield", "esplus", "tns-e",
                                  "rifar", "dskts", "westpower", "ambercombine", "rostec", "rzd.ru", "railfgk", "uzpm"],
    "фарма/медицина": ["r-pharm", "nizhpharm", "invitro", "med-expert", "endopharm", "aviamed"],
    "экипировка": ["jako", "jogel", "primerasport", "maxxisport", "indever", "italsport", "bosco"],
    "медиа/стриминг": ["kinopoisk", "okko", "sports.ru", "sovsport", "championat", "sport-express", "sport24",
                       "nashe.ru", "newradio", "people-fm", "signalradio", "bimradio", "sportmailru"],
    "страхование": ["sogaz", "rgs", "ingos", "reso"],
}
# Беттинг-партнеры по данным СБК (имеют приоритет над сайтом: у КХЛ клубный Fonbet совпадает с титулом лиги)
BETTING_SBC = {
    ("КХЛ", "Авангард"): "Fonbet", ("КХЛ", "Локомотив"): "Fonbet", ("КХЛ", "Металлург Мг"): "Fonbet",
    ("КХЛ", "ЦСКА"): "Olimpbet", ("КХЛ", "Динамо Москва"): "Olimpbet", ("КХЛ", "СКА"): "Olimpbet",
    ("КХЛ", "Северсталь"): "Olimpbet", ("КХЛ", "Автомобилист"): "Winline", ("КХЛ", "Ак Барс"): "Winline",
    ("КХЛ", "Торпедо"): "пусто (СБК: без беттинг-партнера в 2026/27)",
    ("РПЛ", "Спартак"): "Winline", ("РПЛ", "Зенит"): "Winline", ("РПЛ", "Краснодар"): "Winline",
    ("РПЛ", "Динамо Москва"): "Бетсити", ("РПЛ", "Родина"): "PARI (без размещения на форме)",
    ("РПЛ", "Динамо Махачкала"): "Бетсити", ("РПЛ", "Балтика"): "Бетсити", ("ВТБ", "Парма"): "Бетсити (титул)",
    ("ВТБ", "Зенит"): "Лига ставок",
}
# Известное из новостей СБК для клубов, чьи сайты не читаются или показывают не всех
SBC_EXTRA = {
    ("РПЛ", "Локомотив"): {"банк/платежи": "Совкомбанк (СБК, до 2028)"},
    ("РПЛ", "Спартак"): {"напитки/пиво": "Балтика (СБК, до 06.2027)"},
    ("РПЛ", "Зенит"): {"ритейл/FMCG": "Пятерочка (СБК)", "энергетика/промышленность": "Газпром (сайт)"},
    ("РПЛ", "Краснодар"): {"маркетплейс": "Ozon, нейминг стадиона (СБК)"},
    ("РПЛ", "Динамо Махачкала"): {"банк/платежи": "Совкомбанк (СБК)", "ритейл/FMCG": "Магнит (СБК)"},
    ("РПЛ", "Динамо Москва"): {"напитки/пиво": "Балтика (СБК, до 2027)"},
    ("КХЛ", "Авангард"): {"банк/платежи": "Альфа-Банк (СБК)", "телеком": "Т2 (СБК)"},
    ("КХЛ", "Торпедо"): {"банк/платежи": "Альфа-Банк (СБК)"},
    ("ВТБ", "Парма"): {"банк/платежи": "Газпромбанк (СБК)"},
}
NAME_HINTS = {"беттинг": ["фонбет", "fonbet", "бетсити", "betcity", "winline", "леон", "олимпбет", "pari"],
              "банк/платежи": ["банк", "мир"], "маркетплейс": ["wildberries", "rwb", "ozon"],
              "телеком": ["мегафон", "ростелеком", "т2", "билайн", "мтс"], "авиа": ["аэрофлот", "s7"]}
KHL_LEAGUE = {"fon.bet", "gislaved-tire.ru", "haieronline.ru", "hd.kinopoisk.ru", "lada.ru", "rt.ru", "s7.ru",
              "sogaz.ru", "tbank.ru", "vamprivet.ru"}


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "data", "club_partners_raw.csv"), encoding="utf-8-sig")))
    out = []
    for r in rows:
        doms = {d.strip() for d in r["partner_domains"].split("|") if d.strip()}
        if r["league"] == "КХЛ":
            doms -= KHL_LEAGUE
        own = r["site"].split("//")[-1].split("/")[0].replace("www.", "").split(".")[0]
        ext = {d for d in doms if own not in d}
        names = r["partner_names"].lower()
        # Зенит и Оренбург: на сайте ссылки ведут в основном на свои сервисы, партнеров не разобрать
        if len(ext) <= 1 or (r["league"] == "РПЛ" and r["club"] in ("Зенит", "Оренбург")):
            row = {"league": r["league"], "club": r["club"], "status": "партнеров на сайте не удалось прочитать",
                   **{c: "" for c in CAT}, "empty": "", "source": r["site"], "checked": r["checked"]}
            if (r["league"], r["club"]) in BETTING_SBC:
                row["беттинг"] = BETTING_SBC[(r["league"], r["club"])] + " (СБК)"
            for c, v in SBC_EXTRA.get((r["league"], r["club"]), {}).items():
                row[c] = v
            out.append(row)
            continue
        row = {"league": r["league"], "club": r["club"],
               "status": "по сайту клуба" + (" (партнеров на сайте мало, ≤3)" if len(ext) <= 3 else "")}
        empty = []
        for c, keys in CAT.items():
            hit = sorted({d for d in ext for k in keys if k in d})
            if r["league"] != "КХЛ":  # у КХЛ в подписях логотипов есть общий блок партнеров лиги
                hit += sorted({h for h in NAME_HINTS.get(c, []) if h in names and not any(h in x for x in hit)})
            extra = SBC_EXTRA.get((r["league"], r["club"]), {}).get(c)
            if extra and not hit:
                hit = [extra]
            if c == "беттинг" and (r["league"], r["club"]) in BETTING_SBC:
                hit = [BETTING_SBC[(r["league"], r["club"])] + " (СБК)"]
            row[c] = ", ".join(hit) if hit else "пусто"
            if not hit or hit[0].startswith("пусто"):
                empty.append(c)
                if hit:
                    row[c] = hit[0]
        row["empty"] = ", ".join(empty)
        row["source"] = r["status"].split(";")[-1].split("=")[0]
        row["checked"] = r["checked"]
        out.append(row)
    path = os.path.join(HERE, "data", "v2", "sponsor_categories.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["league", "club", "status", *CAT.keys(), "empty", "source", "checked"])
        w.writeheader()
        w.writerows(out)
    print("→", path, len(out))
    for o in out:
        if o["status"].startswith("по сайту"):
            print(o["league"], o["club"], "| пусто:", o["empty"])


if __name__ == "__main__":
    main()
