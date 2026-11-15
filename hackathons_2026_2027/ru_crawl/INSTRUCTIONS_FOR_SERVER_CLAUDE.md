# Задание для Claude Code на сервере

Нужно запустить сборщик анонсов хакатонов и конкурсов на этом сервере (Ubuntu, Россия) и вернуть пользователю результат. Скрипт делает только GET-запросы к публичным сайтам и поисковым API, ничего не устанавливает в систему, кроме python-venv и браузера Chromium для Playwright.

## 1. Установка

```bash
apt-get update && apt-get install -y python3-venv curl
mkdir -p ~/hk && cd ~/hk
curl -fsSLO https://raw.githubusercontent.com/demondevils666/samolet/claude/laughing-hypatia-z752nr/hackathons_2026_2027/ru_crawl/crawl.py
python3 -m venv venv && venv/bin/pip install -q playwright
venv/bin/python -m playwright install --with-deps chromium
```

Если установка Chromium не удалась, продолжайте без него: на шаге 3 уберите флаг `--render`.

## 2. Ключи и проверка

Пользователь пришлёт три значения: секретный ключ Yandex Search API, ID каталога Yandex Cloud (`b1g…`) и токен Kaggle. Задайте их только как переменные окружения процесса. **Не записывайте их в файлы, в лог и в ответы.**

```bash
export YANDEX_SEARCH_API_KEY='…' YANDEX_FOLDER_ID='…' KAGGLE_API_TOKEN='…'
cd ~/hk && venv/bin/python crawl.py --check
```

Ожидаемый результат:
- `Яндекс: OK, N результатов`;
- `Kaggle: OK, N соревнований`;
- коды ответов четырёх сайтов.

Если Kaggle отвечает ошибкой 401, возможно, это старый формат токена. Тогда задайте `KAGGLE_USERNAME` и `KAGGLE_KEY` вместо `KAGGLE_API_TOKEN` и повторите проверку. Покажите пользователю вывод `--check`, ключи в нём не печатаются.

## 3. Полный запуск (20–40 минут)

```bash
cd ~/hk && nohup venv/bin/python crawl.py --render > crawl.log 2>&1 &
```

Следите за `~/hk/crawl.log`, пока не появится строка `готово … Архив: …tar.gz`. Если процесс упал, покажите пользователю последние 30 строк лога.

## 4. Вернуть результат пользователю (в порядке предпочтения)

1. **Архив целиком.** Файл `~/hk/out/crawl_*.tar.gz` весит несколько МБ. Передайте его пользователю как файл, если ваш интерфейс это умеет.
2. **Только выжимка.** Если файл не передаётся, отдайте `~/hk/out/crawl_*/digest.md`. Это компактная выжимка: строки с упоминанием конкурса и дат 2026–2027. Если выжимка слишком большая для одного сообщения, разбейте её на части примерно по 40 КБ и отправляйте по очереди с пометкой «часть i из N».
3. **Статистика.** В любом случае пришлите короткий отчёт:
   - число строк в `index.jsonl`, `errors.jsonl`, `search.jsonl`;
   - размер `kaggle.json`;
   - 20 самых частых доменов в `index.jsonl`.

После этого удалите переменные с ключами: `unset YANDEX_SEARCH_API_KEY YANDEX_FOLDER_ID KAGGLE_API_TOKEN`.
