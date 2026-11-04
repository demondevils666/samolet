# -*- coding: utf-8 -*-
"""Собирает ../v2/sport_people_v2.xlsx из data/v2/*.csv.

Листы: Люди, Связь с РЭШ и ВШЭ, Спонсорские сделки (+ матрица категорий по клубам),
Спецпроекты БК, Стартапы, Консалтинг, СБК спикеры.
Запуск: python build_xlsx_v2.py   (после startups_sk.py, sponsor_categories.py)
"""
import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data", "v2")
OUT = os.path.join(os.path.dirname(HERE), "v2", "sport_people_v2.xlsx")
HEAD_FILL, HEAD_FONT = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF")
CONF = {"высокая": "A9D08E", "средняя": "FFEB84", "низкая": "F8CBAD"}
LINK = {"РЭШ": "63BE7B", "ВШЭ": "A9D08E"}


def rd(name):
    with open(os.path.join(D, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def table(ws, headers, rows, widths, link_cols=(), start_row=None, fills=None):
    r0 = start_row or (ws.max_row + 1 if ws.max_row > 1 else 1)
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=r0, column=j, value=h)
        c.fill, c.font = HEAD_FILL, HEAD_FONT
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(rows, r0 + 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if j in link_cols and isinstance(v, str) and v.startswith("http"):
                c.hyperlink, c.font = v, Font(color="0563C1", underline="single")
            if fills and j in fills and v in fills[j]:
                c.fill = PatternFill("solid", fgColor=fills[j][v])
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    return r0


def note(ws, text, row=None):
    r = row or ws.max_row + 2
    ws.cell(row=r, column=1, value=text).font = Font(italic=True, color="595959")


def build():
    wb = Workbook()
    edu = {(e["name"], e["org"]): e for e in rd("edu_links.csv")}

    # 1. Люди
    ws = wb.active
    ws.title = "Люди"
    ppl = rd("people_v2.csv")
    rows = []
    for p in ppl:
        e = edu.get((p["name"], p["org"]))
        link = f"{e['link']}: {e['what'][:90]}" if e and e["link"] != "нет данных" else "нет данных"
        rows.append([p["org"], p["org_type"], p["name"], p["role"], p["url"], p["source_date"], p["confidence"],
                     p["public_channels"], p["said_2025_26"], p["said_source"], p["offer"], link, p["note"]])
    table(ws, ["Организация", "Тип", "ФИО", "Роль", "Ссылка", "Дата источника", "Уверенность", "Публичные каналы",
               "Что публично говорил в 2025–2026 (задачи и боли)", "Источник цитаты", "Что я мог бы предложить",
               "Связь с РЭШ / ВШЭ", "Комментарий"], rows,
          [20, 10, 20, 30, 34, 16, 11, 26, 60, 22, 50, 34, 30], link_cols=(5,), start_row=1,
          fills={7: CONF})
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:M{len(rows) + 1}"
    note(ws, "Уверенность: высокая — официальный сайт, два источника или свежее интервью (≤3 мес.); средняя — один "
             "источник (рейтинг СБК «Топ-100 – 2026», Transfermarkt, страница выпускников ВШЭ); низкая — косвенно или "
             "место работы могло смениться. «Что предложить» — мои гипотезы, не факты.")

    # 2. Связь с РЭШ и ВШЭ
    ws = wb.create_sheet("Связь с РЭШ и ВШЭ")
    ed = rd("edu_links.csv")
    table(ws, ["Откуда человек", "Организация", "ФИО", "Роль", "Связь", "Что именно", "Ссылка", "Дата"],
          [[e["sheet"], e["org"], e["name"], e["role"], e["link"], e["what"], e["url"], e["source_date"]] for e in ed],
          [14, 26, 24, 32, 10, 70, 36, 18], link_cols=(7,), start_row=1, fills={5: LINK})
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:H{len(ed) + 1}"
    note(ws, "Как проверял: все ФИО из листа «Люди» (этот файл) и из «Люди» прошлого прогона сверены скриптом "
             "scripts/match_alumni.py со списками выпускников 2020–2025 и преподавателей магистратуры ВШЭ "
             "«Международный спортивный менеджмент, маркетинг и право», спикерами ДПО ВШЭ, а также с найденными "
             "материалами РЭШ (news.nes.ru) и ВШЭ. «Нет данных» значит, что в этих источниках совпадений нет; "
             "биографий с образованием у большинства людей в открытом доступе нет. Поиск по сайту РЭШ из контейнера "
             "не работает (404), выпускников РЭШ в спорте нашел двоих.")

    # 3. Спонсорские сделки
    ws = wb.create_sheet("Спонсорские сделки")
    sp = rd("sponsorship.csv")
    table(ws, ["Лига", "Правообладатель", "Спонсор", "Уровень / статус", "Категория", "Срок", "Сумма (если публична)",
               "Ссылка", "Дата", "Комментарий"],
          [[s["league"], s["rights_holder"], s["sponsor"], s["level"], s["sponsor_category"], s["term"], s["amount"],
            s["url"], s["source_date"], s["note"]] for s in sp],
          [12, 28, 26, 30, 14, 22, 36, 34, 11, 40], link_cols=(8,), start_row=1)
    ws.freeze_panes = "C2"
    r = ws.max_row + 3
    ws.cell(row=r - 1, column=1, value="Категории спонсоров по клубам (по сайтам клубов 04.11.2026 + сделки из новостей СБК)").font = Font(bold=True)
    cats = rd("sponsor_categories.csv")
    cat_cols = [k for k in cats[0].keys() if k not in ("league", "club", "status", "empty", "source", "checked")]
    table(ws, ["Лига", "Клуб", "Как получено", *cat_cols, "Пустые категории", "Источник"],
          [[c["league"], c["club"], c["status"], *[c[k] for k in cat_cols], c["empty"], c["source"]] for c in cats],
          [12, 18, 22] + [16] * len(cat_cols) + [40, 34], link_cols=(len(cat_cols) + 5,), start_row=r)
    for row in ws.iter_rows(min_row=r + 1, max_row=ws.max_row, min_col=4, max_col=3 + len(cat_cols)):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("пусто"):
                cell.fill = PatternFill("solid", fgColor="F8CBAD")
    note(ws, "«Пусто» = на сайте клуба 04.11.2026 партнера этой категории не видно (сайт может показывать не всех). "
             "Для клубов КХЛ вычтен общий блок партнеров лиги (Фонбет, Т-Банк, Лада, S7, Согаз, Haier, Gislaved, "
             "Кинопоиск, Ростелеком, «Мир»); беттинг взят из списка СБК на 2026/27. Сайты Спартака, Краснодара, "
             "Зенита, Локомотива, Крыльев, Оренбурга и большинства клубов КХЛ и ВТБ не прочитались: там стоят только "
             "сделки из новостей. Суммы почти везде — оценки СМИ, а не официальные цифры.")

    # 4. Спецпроекты БК
    ws = wb.create_sheet("Спецпроекты БК")
    bp = rd("betting_projects.csv")
    table(ws, ["Букмекер", "Проект", "С кем", "Механика", "Что писали о результатах", "Ссылка", "Дата", "Комментарий"],
          [[b["bookmaker"], b["project"], b["partner"], b["mechanics"], b["results"], b["url"], b["source_date"],
            b["note"]] for b in bp], [14, 36, 26, 50, 50, 34, 11, 30], link_cols=(6,), start_row=1)
    ws.freeze_panes = "C2"
    note(ws, "Часть материалов СБК о букмекерах помечена как реклама (erid): это отмечено в комментарии. "
             "Контекст рынка: с 01.01.2026 налог 7% с GGR, налог на прибыль 25%, отчисления на спорт 2,25%; "
             "ЕРАИ ожидал снижения маркетинговых расходов на 70–75% (Inc., 22.06.2026).")

    # 5. Стартапы
    ws = wb.create_sheet("Стартапы")
    st = rd("startups_sk.csv")
    order = {"победитель": 0, "финалист": 1, "участник": 2}
    st.sort(key=lambda x: (order.get(x["status"], 9), x["cohort"], x["track"]))
    rows = [[x["source"], x["cohort"], x["status"], x["track"], x["name"], x["what"], x["stage"], x["team"], x["site"],
             x["one_pager"], x["catalog"], x["help"]] for x in st]
    ld = [x for x in rd("leaders_2026.csv") if x["nomination"] in ("Инновация года", "") or x["track"].startswith("Студ")]
    rows += [[x["source"], "номинант 2026", x["nomination"] or ("студенческий стартап" if x["track"].startswith("Студ") else "номинант трека"),
              x["track"], x["name"], x["what"], ("Вуз: " + x["university"]) if x["university"] else "нет данных",
              "Номинировал: " + x["nominated_by"] if x["nominated_by"] else "", x["site"], "", x["page"],
              "Рынок, конкуренты, юнит-экономика под задачи номинанта"] for x in ld]
    table(ws, ["Источник", "Поток / год", "Статус", "Трек", "Проект", "Что делают", "Стадия", "Команда (публично)",
               "Сайт", "One-pager", "Страница в каталоге", "Чем я мог бы помочь (гипотеза)"], rows,
          [16, 18, 12, 18, 28, 60, 34, 24, 30, 30, 30, 46], link_cols=(9, 10, 11), start_row=1)
    ws.freeze_panes = "F2"
    ws.auto_filter.ref = f"A1:L{len(rows) + 1}"
    note(ws, "Каталог СпортТех Сколково взят из публичного JS-бандла сайта awards.sporttech.sk.ru (scripts/startups_sk.py). "
             "Личные Telegram и почты основателей из каталога сознательно не переносил: контакт через страницу каталога "
             "или сайт проекта. «Стадия» — это запрос проекта из каталога, если он указан.")

    # 6. Консалтинг
    ws = wb.create_sheet("Консалтинг")
    cs = rd("consulting.csv")
    table(ws, ["Организация", "Тип", "Услуги", "Проекты / клиенты", "Команда", "Ссылка", "Дата", "Уверенность",
               "Комментарий"], [[c["org"], c["kind"], c["services"], c["projects_clients"], c["team"], c["url"],
                                 c["source_date"], c["confidence"], c["note"]] for c in cs],
          [26, 20, 40, 60, 40, 34, 20, 11, 50], link_cols=(6,), start_row=1, fills={8: CONF})
    ws.freeze_panes = "B2"

    # 7. СБК спикеры
    ws = wb.create_sheet("СБК спикеры")
    sk = rd("sbk_speakers.csv")
    table(ws, ["Тип", "Имя / сессия", "Должность", "Про коммерцию / спонсорство / медиа?", "Есть в листе «Люди»",
               "Сессия / время / комментарий", "Ссылка", "Дата"],
          [[s["kind"], s["name"], s["role"], s["relevant"], s["in_people"], s["session"], s["url"], s["source_date"]]
           for s in sk], [18, 40, 46, 26, 16, 60, 34, 18], link_cols=(7,), start_row=1)
    note(ws, "На сайте конгресса опубликовано 20 имен спикеров без привязки к сессиям; кнопка «полный список» "
             "подгружается скриптом и из контейнера не раскрылась. Сессии взяты из проекта программы от 26.10.2026. "
             "Файл «Архитектура ДП» (Яндекс Диск, ссылка с сайта, версия от 29.06.2026) содержит только типы спикеров.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("→", OUT)


if __name__ == "__main__":
    build()
