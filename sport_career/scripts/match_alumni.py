# -*- coding: utf-8 -*-
"""Сверка списка имен (например, выпускников РЭШ или ВШЭ) с листами людей.

Вход: один или несколько файлов со списком имен:
  * CSV/TSV: колонка name / ФИО / fio / full_name (иначе первая колонка); остальные колонки
    (год, программа, место работы) переносятся в результат как есть;
  * TXT: одно имя в строке;
  * HTML (сохраненные страницы): имена ищутся регулярными выражениями: «Фамилия Имя Отчество»,
    «Имя Фамилия», латиница «Name Surname».
С чем сверяем (по умолчанию): лист «Люди» из ../sport_career.xlsx и ../v2/sport_people_v2.xlsx,
плюс data/people.csv и data/v2/people_v2.csv, если есть. Можно передать свои через --people.

Учитываем разное написание: регистр, ё/е, порядок «Имя Фамилия» / «Фамилия Имя», отчество
(отбрасывается), дефисы, латиница (транслитерация в кириллицу и обратно), опечатки
(похожесть фамилии ≥ 0.88 при совпадении имени или инициала).

Запуск:
  python match_alumni.py alumni.csv
  python match_alumni.py page1.html page2.html --out out/alumni_matches.csv
  python match_alumni.py alumni.csv --people ../v2/sport_people_v2.xlsx --min-score 90
Результат: CSV со столбцами input_name, input_extra, matched_name, org, role, sheet, score, match_type.
"""
import argparse
import csv
import difflib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LAT2CYR = [("shch", "щ"), ("sch", "щ"), ("yev", "ьев"), ("yov", "ьев"), ("ia", "я"), ("iu", "ю"), ("yo", "е"), ("zh", "ж"), ("kh", "х"), ("ts", "ц"), ("ch", "ч"),
           ("sh", "ш"), ("yu", "ю"), ("ya", "я"), ("ye", "е"), ("iy", "ий"), ("yy", "ый"), ("a", "а"),
           ("b", "б"), ("v", "в"), ("g", "г"), ("d", "д"), ("e", "е"), ("z", "з"), ("i", "и"), ("y", "й"),
           ("k", "к"), ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"), ("r", "р"), ("s", "с"),
           ("t", "т"), ("u", "у"), ("f", "ф"), ("h", "х"), ("c", "к"), ("w", "в"), ("x", "кс"), ("q", "к"),
           ("j", "дж")]
CYR2LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
           "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
           "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y",
           "ь": "", "э": "e", "ю": "yu", "я": "ya"}
PATRONYMIC = re.compile(r"(ович|евич|ьич|овна|евна|ична|инична|оглы|кызы)$")
STOP = {"и", "в", "на", "по", "с", "для", "от", "при", "клуб", "фк", "хк", "бк", "ооо", "ао", "пао"}


def translit_lat(s):
    s = s.lower()
    out, i = "", 0
    while i < len(s):
        for a, b in LAT2CYR:
            if s.startswith(a, i):
                out += b
                i += len(a)
                break
        else:
            out += s[i]
            i += 1
    return out


def to_lat(s):
    return "".join(CYR2LAT.get(ch, ch) for ch in s.lower())


def tokens(name):
    n = name.lower().replace("ё", "е")
    n = re.sub(r"[«»\"'().,;:]", " ", n)
    if re.search(r"[a-z]", n) and not re.search(r"[а-я]", n):
        n = translit_lat(n)
    toks = [t for t in re.split(r"[\s]+", n) if t and t not in STOP]
    # отчество отбрасываем, только если слов три и оно не первое ("Гордосевич" — фамилия, а не отчество)
    if len(toks) >= 3:
        for i in (len(toks) - 1, 1):
            if PATRONYMIC.search(toks[i]):
                toks = toks[:i] + toks[i + 1:]
                break
    return toks[:3]


def key_variants(name):
    """Все пары (фамилия, имя), которые можно получить из имени при разном порядке."""
    t = tokens(name)
    if len(t) < 2:
        return []
    pairs = {(t[0], t[1]), (t[1], t[0])}
    if len(t) == 3:
        pairs |= {(t[0], t[2]), (t[2], t[0]), (t[1], t[2]), (t[2], t[1])}
    return list(pairs)


# ----------------------------------------------------------------------------- ввод
NAME_CYR = re.compile(r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+([А-ЯЁ][а-яё]+)(?:\s+([А-ЯЁ][а-яё]+(?:вич|вна|ична|оглы)))?\b")
NAME_LAT = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\b")


def read_names(path):
    ext = os.path.splitext(path)[1].lower()
    rows = []
    if ext in (".csv", ".tsv"):
        with open(path, encoding="utf-8-sig") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            r = csv.DictReader(f, dialect=dialect)
            col = next((c for c in r.fieldnames or [] if c.strip().lower() in
                        ("name", "фио", "fio", "full_name", "имя", "выпускник")), (r.fieldnames or [None])[0])
            for row in r:
                extra = "; ".join(f"{k}={v}" for k, v in row.items() if k != col and v)
                rows.append((row.get(col, "").strip(), extra))
    elif ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = BeautifulSoup(f.read(), "lxml").get_text(" ", strip=True)
        seen = set()
        for m in NAME_CYR.finditer(text):
            n = " ".join(x for x in m.groups() if x)
            if n not in seen:
                seen.add(n)
                rows.append((n, f"html={os.path.basename(path)}"))
        for m in NAME_LAT.finditer(text):
            n = " ".join(m.groups())
            if n not in seen:
                seen.add(n)
                rows.append((n, f"html={os.path.basename(path)}"))
    else:
        with open(path, encoding="utf-8-sig") as f:
            rows = [(line.strip(), "") for line in f if line.strip()]
    return [r for r in rows if r[0]]


def read_people(paths):
    people = []
    for p in paths:
        if not os.path.exists(p):
            continue
        if p.endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(p, read_only=True, data_only=True)
            for ws in wb.worksheets:
                it = ws.iter_rows(values_only=True)
                head = [str(h or "").strip() for h in next(it, [])]
                ci = next((i for i, h in enumerate(head) if h in ("ФИО", "Имя", "name")), None)
                if ci is None:
                    continue
                oi = next((i for i, h in enumerate(head) if h.startswith("Организац")), None)
                ri = next((i for i, h in enumerate(head) if h.startswith("Роль")), None)
                for row in it:
                    if row and row[ci] and str(row[ci]).strip() not in ("—", "-"):
                        people.append({"name": str(row[ci]), "org": str(row[oi] or "") if oi is not None else "",
                                       "role": str(row[ri] or "") if ri is not None else "",
                                       "sheet": f"{os.path.basename(p)}:{ws.title}"})
        elif p.endswith(".csv"):
            with open(p, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    n = row.get("name") or row.get("ФИО") or ""
                    if n and n.strip() not in ("—", "-"):
                        people.append({"name": n, "org": row.get("org", ""), "role": row.get("role", ""),
                                       "sheet": os.path.basename(p)})
                    if row.get("name_in_source"):
                        people.append({"name": row["name_in_source"], "org": row.get("org", ""),
                                       "role": row.get("role", ""), "sheet": os.path.basename(p) + " (лат.)"})
    return people


# ----------------------------------------------------------------------------- сверка
def score(a_pairs, b_pairs):
    best, kind = 0, ""
    for (s1, f1) in a_pairs:
        for (s2, f2) in b_pairs:
            if s1 == s2 and f1 == f2:
                return 100, "точное (фамилия+имя)"
            if s1 == s2 and f1[:1] == f2[:1] and (len(f1) <= 2 or len(f2) <= 2):
                best, kind = max((best, kind), (92, "фамилия + инициал"))
            rs = difflib.SequenceMatcher(None, s1, s2).ratio()
            rf = difflib.SequenceMatcher(None, f1, f2).ratio()
            if f1 == f2 and rs >= 0.8:  # имя совпало, фамилия с опечаткой или в другой транслитерации
                sc = int(60 + 40 * rs)
                if sc > best:
                    best, kind = sc, "имя совпало, фамилия похожа"
            elif rs >= 0.88 and rf >= 0.85:
                sc = int(55 + 40 * (rs + rf) / 2)
                if sc > best:
                    best, kind = sc, "похожее написание"
            else:  # сравнение в латинице ловит разные системы транслитерации
                ls = difflib.SequenceMatcher(None, to_lat(s1), to_lat(s2)).ratio()
                lf = difflib.SequenceMatcher(None, to_lat(f1), to_lat(f2)).ratio()
                if ls >= 0.85 and lf >= 0.85:
                    sc = int(50 + 40 * (ls + lf) / 2)
                    if sc > best:
                        best, kind = sc, "транслитерация"
    return best, kind


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="CSV/TXT/HTML со списком имен")
    ap.add_argument("--people", nargs="*", default=[
        os.path.join(ROOT, "sport_career.xlsx"), os.path.join(ROOT, "v2", "sport_people_v2.xlsx"),
        os.path.join(HERE, "data", "people.csv"), os.path.join(HERE, "data", "v2", "people_v2.csv")])
    ap.add_argument("--min-score", type=int, default=80)
    ap.add_argument("--out", default=os.path.join(HERE, "out", "alumni_matches.csv"))
    a = ap.parse_args()

    names = [n for p in a.inputs for n in read_names(p)]
    people = read_people(a.people)
    pk = [(p, key_variants(p["name"])) for p in people]
    print(f"имен на входе: {len(names)}, людей в листах: {len(people)}", file=sys.stderr)
    res, seen = [], set()
    for name, extra in names:
        kv = key_variants(name)
        if not kv:
            continue
        for p, pv in pk:
            sc, kind = score(kv, pv)
            if sc >= a.min_score:
                k = (name, p["name"], p["org"])
                if k in seen:
                    continue
                seen.add(k)
                res.append({"input_name": name, "input_extra": extra, "matched_name": p["name"],
                            "org": p["org"], "role": p["role"], "sheet": p["sheet"], "score": sc,
                            "match_type": kind})
    res.sort(key=lambda r: -r["score"])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["input_name", "input_extra", "matched_name", "org", "role", "sheet",
                                          "score", "match_type"])
        w.writeheader()
        w.writerows(res)
    print(f"совпадений: {len(res)} → {a.out}")
    for r in res[:30]:
        print(f"  {r['score']:>3} {r['input_name']} ↔ {r['matched_name']} ({r['org']}, {r['sheet']})")


if __name__ == "__main__":
    main()
