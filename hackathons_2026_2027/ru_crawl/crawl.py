#!/usr/bin/env python3
"""
Сборщик анонсов хакатонов и конкурсов для запуска с российского сервера.

Что делает:
  1. Скачивает «сид-страницы»: российские площадки, которые не открываются
     из-за рубежа (Leader-ID, hacks-ai, rsv.ru, Хабр, сайты организаторов),
     публичные превью Telegram-каналов с пагинацией, агрегаторы СНГ.
  2. Прогоняет поиск по матрице «формулировка × тема»:
       - через Yandex Search API, если заданы YANDEX_SEARCH_API_KEY и YANDEX_FOLDER_ID;
       - иначе через HTML-версию DuckDuckGo (без ключей, медленнее и беднее).
  3. Скачивает страницы из найденных результатов (с дедупликацией).
  4. Складывает всё в один архив out/crawl_<время>.tar.gz: текст страниц (без
     скриптов), результаты поиска и журнал ошибок. Архив нужно передать в чат.

Зависимости: только стандартная библиотека Python 3.8+.
Если установлен Playwright (pip install playwright && playwright install chromium),
JS-страницы (Leader-ID и т.п.) дополнительно рендерятся в браузере: флаг --render.

Запуск:
  python3 crawl.py                    # всё по умолчанию
  python3 crawl.py --render           # плюс рендер JS-страниц через Playwright
  python3 crawl.py --max-pages 600    # сколько страниц из поиска докачать (по умолчанию 400)
  YANDEX_SEARCH_API_KEY=... YANDEX_FOLDER_ID=... python3 crawl.py

Скрипт ничего не отправляет наружу, кроме обычных GET-запросов к сайтам и
запросов к поиску. Ключи читаются только из переменных окружения.
"""
import argparse, base64, concurrent.futures as cf, datetime as dt, gzip, hashlib, html, io, json, os, re, sys, tarfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TIMEOUT = 30

# ---------------------------------------------------------------- сиды
SEEDS = [
    # российские площадки, недоступные из-за рубежа
    "https://leader-id.ru/events?q=%D1%85%D0%B0%D0%BA%D0%B0%D1%82%D0%BE%D0%BD",
    "https://leader-id.ru/events?q=%D1%87%D0%B5%D0%BC%D0%BF%D0%B8%D0%BE%D0%BD%D0%B0%D1%82",
    "https://leader-id.ru/events?q=%D0%BA%D0%BE%D0%BD%D0%BA%D1%83%D1%80%D1%81",
    "https://hacks-ai.ru/", "https://hacks-ai.ru/hackathons", "https://hacks-ai.ru/championships",
    "https://rsv.ru/competitions/", "https://myrosmol.ru/events",
    "https://i.moscow/challenges", "https://ict2go.ru/types/hakaton/",
    "https://www.xn--80aa3anexr8c.xn--p1acf/", "https://hackathons.pro/", "https://russianhackers.org/",
    "https://habr.com/ru/users/hackathons/articles/", "https://habr.com/ru/news/1094372/",
    "https://habr.com/ru/search/?q=%D1%85%D0%B0%D0%BA%D0%B0%D1%82%D0%BE%D0%BD&target_type=posts&order=date",
    "https://architechhack.vtb.ru/", "https://nornickel-hackathon.ru/", "https://gigachat-challenge.tech/",
    "https://fintech.tinkoff.ru/activities/", "https://creative-generation.ru/hack",
    "https://changellenge.com/championships/", "https://case-in.ru/", "https://lab-career.ru/knowledge-base/keys-chempionaty-2026-polnyy-spisok",
    "https://olymp.hse.ru/", "https://www.hse.ru/news/announcements/", "https://www.nes.ru/events",
    "https://sechenov.ru/news/", "https://mosgorzdrav.ru/", "https://www.cbr.ru/press/event/",
    "https://data-fusion.ru/", "https://truetecharena.ru/", "https://e-cup-ozon.ru/",
    "https://education.vk.company/", "https://yandex.ru/yaintern/", "https://fasie.ru/", "https://upgreat.one/",
    # СНГ
    "https://astanahub.com/ru/event/", "https://it-park.uz/ru/events", "https://www.park.by/news/", "https://devby.io/news",
    "https://hackathon.alem.ai/", "https://fci.eabr.org/",
    *[f"https://www.stavleak.com/ru/hackathons?page={i}" for i in range(1, 20)],
    "https://www.it-park.uz/ru/events", "https://hackathon.by/",
    "https://www.park.by/press/news/priem_zayavok_na_realizatsiyu_pilotnykh_proektov_v_sfere_tsifrovykh_tekhnologiy_nov%202/",
    # РСВ: конкретные конкурсы
    "https://rsv.ru/competitions/project/1/f3e316f5-4151-443b-9efc-2bd3d7e7cafe/",
    "https://rsv.ru/competitions/project/1/de5c2e41-5dd7-4831-bc18-dedd30efbb0d/",
    "https://rsv.ru/competitions/project/1/b9826fd2-5120-4301-ba39-3462bb007881/",
    "https://rsv.ru/competitions/project/1/7502fbb8-5815-43ac-9e7b-5321778a071d/",
    "https://upgreat.one/contests?status=active", "https://ntcontest.ru/",
    # международные площадки, которые отказали моему контейнеру
    "https://grand-challenge.org/challenges/?status=open", "https://grand-challenge.org/api/v1/challenges/?status=open",
    "https://solafune.com/", "https://www.herox.com/crowdsourcing-projects", "https://www.aicrowd.com/challenges?status=active",
    "https://starfieldlabs.ai/", "https://lablab.ai/event", "https://www.usa.gov/challenges",
    "https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&page=1&per_page=50&oppstatus=open",
    "https://unstop.com/api/public/opportunity/search-result?opportunity=competitions&page=1&per_page=50&oppstatus=open",
    "https://www.res.org.uk/resources-page/young-economists-essay-competition.html",
    "https://www.economist.com/essay-competition", "https://www.cfainstitute.org/societies/challenge",
    # VK (мобильная версия иногда отдаётся без логина)
    "https://m.vk.com/hackathonsrus", "https://m.vk.com/hacklist", "https://m.vk.com/changellenge",
]
TELEGRAM = ["hackathons", "hackathonsrus", "Hackathonlist", "codenrock", "changellenge", "hacklist",
            "it_events_ru", "studentcases", "case_club", "ods_ai", "datafusion_contest", "leaderid"]
TG_PAGES = 6  # страниц пагинации назад на канал (≈20 постов на страницу)

# ---------------------------------------------------------------- поисковая матрица
FORMS = ["хакатон", "дататон", "датафон", "кейс-чемпионат", "чемпионат по анализу данных", "конкурс решений",
         "челлендж", "конкурс проектов", "грантовый конкурс студентов", "конкурс ИИ", "олимпиада студентов",
         "акселератор студентов", "конкурс эссе экономика", "конкурс исследовательских работ студентов"]
TOPICS = ["", "финтех", "банк", "спорт", "экономика", "медицина", "здравоохранение", "география", "геоданные",
          "экология", "урбанистика", "транспорт", "энергетика", "агро", "образование", "право", "госуправление",
          "культура", "туризм", "ритейл", "маркетинг", "открытые данные", "ИИ-агенты", "LLM", "безопасность",
          "космос", "Беларусь", "Казахстан", "Узбекистан"]
TIME_HINTS = ["регистрация 2026", "2027"]
EXTRA_QUERIES = [
    "хакатон регистрация до декабря 2026", "хакатон регистрация январь 2027", "хакатон февраль 2027 регистрация",
    "хакатон март 2027", "кейс-чемпионат весна 2027 регистрация", "онлайн хакатон можно участвовать одному 2026",
    "промпт-хакатон 2026", "вайбкодинг хакатон", "хакатон MCP агенты", "конкурс аналитики данных студенты 2026 призовой фонд",
    "site:codenrock.com/contests 2027", "site:leader-id.ru хакатон 2026", "site:t.me хакатон регистрация ноябрь 2026",
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(url, data=None, headers=None, tries=3):
    h = {"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.6", "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                ct = r.headers.get("Content-Type", "")
                enc = re.search(r"charset=([\w-]+)", ct)
                return r.status, r.geturl(), ct, raw.decode(enc.group(1) if enc else "utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (401, 403, 404, 410):
                break
        except Exception as e:  # сеть, таймаут, TLS
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * (i + 1))
    return None, url, "", last


def to_text(s):
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def links(s, base):
    out = []
    for m in re.finditer(r'href="([^"#]+)"', s):
        u = urllib.parse.urljoin(base, html.unescape(m.group(1)))
        if u.startswith("http"):
            out.append(u)
    return out


class Store:
    def __init__(self, root):
        self.root = root
        os.makedirs(os.path.join(root, "pages"), exist_ok=True)
        self.index = open(os.path.join(root, "index.jsonl"), "a", encoding="utf-8")
        self.errors = open(os.path.join(root, "errors.jsonl"), "a", encoding="utf-8")
        self.seen = set()

    def save(self, kind, url, status, final, ct, body, extra=None):
        key = hashlib.sha1(url.encode()).hexdigest()[:16]
        if status is None:
            self.errors.write(json.dumps({"kind": kind, "url": url, "error": body}, ensure_ascii=False) + "\n")
            return None
        text = body if "json" in ct else to_text(body)
        with open(os.path.join(self.root, "pages", key + ".txt"), "w", encoding="utf-8") as f:
            f.write(f"URL: {url}\nFINAL: {final}\nSTATUS: {status}\nCT: {ct}\n\n{text[:60000]}")
        rec = {"kind": kind, "url": url, "final": final, "status": status, "file": f"pages/{key}.txt", "chars": len(text)}
        if extra:
            rec.update(extra)
        self.index.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return text


def crawl_seeds(st):
    log(f"сиды: {len(SEEDS)}")
    with cf.ThreadPoolExecutor(8) as ex:
        for url, res in zip(SEEDS, ex.map(fetch, SEEDS)):
            status, final, ct, body = res
            st.save("seed", url, status, final, ct, body)
            log("seed", status, url)


def crawl_telegram(st):
    for ch in TELEGRAM:
        before = None
        for _ in range(TG_PAGES):
            url = f"https://t.me/s/{ch}" + (f"?before={before}" if before else "")
            status, final, ct, body = fetch(url)
            if status is None:
                st.save("telegram", url, None, final, ct, body)
                break
            # сохраняем сам HTML-текст постов вместе с датами
            posts = re.findall(r'data-post="[^/]+/(\d+)"', body)
            dates = re.findall(r'<time[^>]*datetime="([^"]+)"', body)
            st.save("telegram", url, status, final, ct, body, {"channel": ch, "posts": len(posts), "date_min": min(dates) if dates else None})
            log("tg", ch, before, len(posts), dates[:1])
            if not posts:
                break
            before = min(int(p) for p in posts)
            if dates and min(dates) < "2026-08-15":
                break


def yandex_search(q, key, folder):
    body = json.dumps({"query": {"searchType": "SEARCH_TYPE_RU", "queryText": q, "familyMode": "FAMILY_MODE_NONE"},
                       "groupSpec": {"groupMode": "GROUP_MODE_DEEP", "groupsOnPage": 50, "docsInGroup": 1},
                       "folderId": folder, "responseFormat": "FORMAT_XML", "l10N": "LOCALIZATION_RU"}).encode()
    status, _, _, txt = fetch("https://searchapi.api.cloud.yandex.net/v2/web/search", data=body,
                              headers={"Authorization": f"Api-Key {key}", "Content-Type": "application/json"})
    if status is None:
        return None, txt
    raw = base64.b64decode(json.loads(txt)["rawData"]).decode("utf-8", errors="replace")
    res = []
    for doc in ET.fromstring(raw).iter("doc"):
        u = doc.findtext("url")
        t = "".join(doc.find("title").itertext()) if doc.find("title") is not None else ""
        p = " ".join("".join(x.itertext()) for x in doc.iter("passage"))
        res.append({"url": u, "title": t, "snippet": p})
    return res, None


def ddg_search(q):
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q, "kl": "ru-ru"})
    status, _, _, body = fetch(url)
    if status is None:
        return None, body
    res = []
    for m in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', body, re.S):
        u = html.unescape(m.group(1))
        if "uddg=" in u:
            u = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("uddg", [u])[0])
        res.append({"url": u, "title": to_text(m.group(2)), "snippet": to_text(m.group(3))})
    return res, None


def run_search(st, root):
    key, folder = os.environ.get("YANDEX_SEARCH_API_KEY"), os.environ.get("YANDEX_FOLDER_ID")
    engine = "yandex" if key and folder else "duckduckgo"
    queries = [f"{f} {t} {h}".strip().replace("  ", " ") for f in FORMS for t in TOPICS for h in TIME_HINTS[:1]]
    queries += [f"{f} {TIME_HINTS[1]}" for f in FORMS] + EXTRA_QUERIES
    log(f"поиск: {engine}, запросов {len(queries)}")
    allres, out = {}, open(os.path.join(root, "search.jsonl"), "a", encoding="utf-8")
    for i, q in enumerate(queries):
        res, err = yandex_search(q, key, folder) if engine == "yandex" else ddg_search(q)
        out.write(json.dumps({"q": q, "engine": engine, "error": err, "results": res}, ensure_ascii=False) + "\n")
        for r in res or []:
            allres.setdefault(r["url"], r)
        if i % 20 == 0:
            log(f"  {i}/{len(queries)} уникальных ссылок: {len(allres)}")
        time.sleep(0.4 if engine == "yandex" else 2.5)  # DDG банит частые запросы
    return allres


JUNK = re.compile(r"(youtube\.com|wikipedia\.org|hh\.ru/vacancy|avito\.ru/|ozon\.ru/product|vk\.com/video|dzen\.ru/video|\.pdf$)", re.I)


def crawl_results(st, allres, limit):
    urls = [u for u in allres if not JUNK.search(u)]
    # приоритет: свежие и «событийные» домены
    pri = lambda u: (0 if re.search(r"hack|хакатон|champ|cup|contest|challenge|konkurs|конкурс|case|tpost|event", u, re.I) else 1)
    urls = sorted(urls, key=pri)[:limit]
    log(f"докачиваю страницы из выдачи: {len(urls)}")
    with cf.ThreadPoolExecutor(8) as ex:
        for url, res in zip(urls, ex.map(fetch, urls)):
            status, final, ct, body = res
            st.save("result", url, status, final, ct, body, {"title": allres[url].get("title"), "snippet": allres[url].get("snippet")})


def kaggle_list(st, root):
    """Полный список активных соревнований Kaggle, если заданы KAGGLE_USERNAME и KAGGLE_KEY."""
    user, key = os.environ.get("KAGGLE_USERNAME"), os.environ.get("KAGGLE_KEY")
    if not (user and key):
        log("Kaggle: ключа нет, пропуск")
        return
    auth = "Basic " + base64.b64encode(f"{user}:{key}".encode()).decode()
    allc = []
    for cat in ("featured", "research", "playground", "analytics", "community", "gettingStarted", "recruitment"):
        for page in range(1, 6):
            url = f"https://www.kaggle.com/api/v1/competitions/list?category={cat}&sortBy=latestDeadline&page={page}"
            status, _, ct, body = fetch(url, headers={"Authorization": auth})
            if status is None:
                st.save("kaggle", url, None, url, ct, body)
                break
            try:
                items = json.loads(body)
            except ValueError:
                break
            if not items:
                break
            allc += [dict(i, _category=cat) for i in items]
    with open(os.path.join(root, "kaggle.json"), "w", encoding="utf-8") as f:
        json.dump(allc, f, ensure_ascii=False)
    log(f"Kaggle: {len(allc)} соревнований")


def render_js(st, root):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("Playwright не установлен, рендер пропущен")
        return
    targets = [u for u in SEEDS if re.search(r"leader-id|hacks-ai|rsv\.ru/competitions/$|myrosmol|xn--80aa3anexr8c|hackathons\.pro|russianhackers|astanahub|grand-challenge\.org/challenges|solafune|herox|aicrowd|starfieldlabs|signate|it-park", u)]
    targets += ["https://www.kaggle.com/competitions?listOption=active", "https://service.signate.jp/competitions",
                "https://unstop.com/hackathons?oppstatus=open", "https://www.kaggle.com/competitions?hostSegmentIdFilter=8"]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(user_agent=UA, locale="ru-RU")
        for u in targets:
            try:
                pg.goto(u, timeout=45000, wait_until="networkidle")
                for _ in range(4):  # подгрузка бесконечных списков
                    pg.mouse.wheel(0, 20000); pg.wait_for_timeout(1200)
                body = pg.content()
                st.save("rendered", u, 200, pg.url, "text/html", body, {"links": [l for l in links(body, pg.url)][:400]})
                log("render ok", u)
            except Exception as e:
                st.save("rendered", u, None, u, "", f"{type(e).__name__}: {e}")
                log("render fail", u, e)
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="рендерить JS-страницы через Playwright")
    ap.add_argument("--max-pages", type=int, default=400)
    ap.add_argument("--skip-search", action="store_true")
    a = ap.parse_args()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", f"crawl_{stamp}")
    st = Store(root)
    t0 = time.time()
    crawl_seeds(st)
    crawl_telegram(st)
    kaggle_list(st, root)
    if a.render:
        render_js(st, root)
    if not a.skip_search:
        allres = run_search(st, root)
        crawl_results(st, allres, a.max_pages)
    st.index.close(); st.errors.close()
    tar = root + ".tar.gz"
    with tarfile.open(tar, "w:gz") as tf:
        tf.add(root, arcname=os.path.basename(root))
    log(f"готово за {int(time.time()-t0)} с. Архив: {tar} ({os.path.getsize(tar)//1024} КБ)")


if __name__ == "__main__":
    main()
