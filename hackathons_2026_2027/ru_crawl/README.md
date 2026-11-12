# Сборщик анонсов для российского сервера

Нужен потому, что облачный контейнер Claude ходит в интернет из-за рубежа. Многие площадки ему не отвечают, например Leader-ID (403), hacks-ai.ru (504), Фонд содействия инновациям (403), Astana Hub (403), grand-challenge, Unstop и Kaggle. Кроме того, у контейнера нет нормального поиска по рунету.

## Запуск (Python 3.8+, без зависимостей)

```bash
git clone https://github.com/demondevils666/samolet.git && cd samolet && git checkout claude/laughing-hypatia-z752nr
cd hackathons_2026_2027/ru_crawl
python3 crawl.py
```

- **Время работы.** Примерно 30–60 минут в бесплатном режиме: поиск через DuckDuckGo, пауза 2,5 с на запрос, около 450 запросов. С ключом Яндекса — около 10 минут.
- **Результат.** Архив `out/crawl_<дата>.tar.gz`, обычно несколько мегабайт. **Пришлите его в чат.**

### Опционально, но заметно улучшает результат

**1. Рендер JS-страниц** (Leader-ID, «Молодёжь России», календари агрегаторов):

```bash
pip install playwright && python3 -m playwright install --with-deps chromium
python3 crawl.py --render
```

**2. Yandex Search API.** Даёт настоящую выдачу по рунету вместо DuckDuckGo.

Как получить ключ:
1. Зайдите на console.yandex.cloud и создайте платёжный аккаунт; новым аккаунтам обычно дают стартовый грант, проверьте актуальный тариф Search API.
2. Создайте сервисный аккаунт с ролью `search-api.webSearch.user`. В старых версиях консоли эта роль называется `search-api.executor`.
3. В этом аккаунте создайте API-ключ.
4. Скопируйте ID каталога (folder id) из консоли.

Запуск:

```bash
export YANDEX_SEARCH_API_KEY=... YANDEX_FOLDER_ID=...
python3 crawl.py --render
```

**3. Kaggle.** Даёт полный список соревнований, включая аналитические.

Как получить токен: kaggle.com → Settings → API → Create New Token. Скачается файл `kaggle.json`, в нём `username` и `key`.

```bash
export KAGGLE_USERNAME=... KAGGLE_KEY=...
```

Ключи читаются только из переменных окружения на вашем сервере и никуда, кроме Яндекса и Kaggle, не отправляются. В чат их присылать не нужно.

## Что внутри архива

- `index.jsonl` — все скачанные страницы: URL, статус, файл с текстом.
- `pages/*.txt` — текст страниц без скриптов, до 60 тыс. символов каждая.
- `search.jsonl` — выдача по каждому запросу: формулировка × тема × год, около 450 запросов.
- `kaggle.json` — соревнования Kaggle, если задан токен.
- `errors.jsonl` — что не открылось и почему.
