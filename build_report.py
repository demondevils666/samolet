#!/usr/bin/env python3
"""Собирает HTML-отчёт из результатов model.py и печатает его в PDF через headless Chromium."""
import pathlib
import subprocess

import model as m

ROOT = pathlib.Path(__file__).resolve().parent
HTML = ROOT / "out" / "report.html"
PDF = ROOT / "Aurora_turn_PnL_delta.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

b, s, mc, bv = m.base, m.scen, m.mc_stats, m.bv
ru = m.ru
c = b["costs"]
h = bv["t_turn"] / 60


def eur(x, plus=False):
    a = abs(x)
    sign = "−" if x < 0 else ("+" if plus and x > 0 else "")
    if a >= 1e6:
        return f"{sign}€{ru(a / 1e6, 2)} млн"
    if a >= 1e4:
        return f"{sign}€{ru(a / 1e3, 0)} тыс."
    return f"{sign}€{ru(a, 0)}"


def fmt_param(k, x):
    unit = m.P[k][3]
    if k == "reach":
        return f"{ru(x / 1e6, 0)} млн"
    if k == "conv":
        return f"{ru(x * 100, 3)}%"
    if k == "p261":
        return f"{ru(x * 100, 2)}%"
    if unit == "доля":
        return f"{ru(x * 100, 0)}%"
    if unit == "×":
        return ru(x, 2)
    return ru(x, 1 if x != int(x) else 0)


KIND = {"F": "<span class='tag f'>факт</span>", "E": "<span class='tag e'>оценка</span>",
        "U": "<span class='tag u'>МК</span>"}

# ---------------------------------------------------------------- таблицы
cost_rows = [
    ("Топливо", f"{ru(bv['ff'])} кг/ч × {ru(h, 3)} ч × {ru(bv['bank'], 2)} (крен) = <b>{ru(b['fuel_t'] * 1000)} кг</b> × €{ru(bv['fuel_px'])}/т"),
    ("CO₂ (EU ETS)", f"{ru(b['fuel_t'] * 1000)} кг × 3,16 = <b>{ru(b['co2_t'], 2)} т</b> × €{bv['ets']}/т. Рейс ЕЭЗ → UK входит в EU ETS; "
                     "бесплатные квоты фиксированы и предельную стоимость не меняют"),
    ("Техобслуживание", f"€{bv['mx']}/лётн. ч × {ru(h, 3)} ч: PBH двигателей и планера начисляются за лётные часы"),
    ("Экипаж", f"€{bv['crew']}/ч × {ru(h, 3)} ч: оплата в основном оклад + посекторные доплаты"),
    ("Наземные расходы", "Прилёт ≈ 22:30; смена хендлинга и так на месте"),
    ("Пассажиры: транспорт, жалобы", "Пропущенные поздние поезда и такси, обработка жалоб"),
    ("Риск EU/UK261", "Ex post: задержки ≥ 3 ч не было → €0"),
    ("Безопасность и регуляторика (EV)", "Ex post инцидентов не было; ex ante — вероятность × ущерб. Разрешение УВД было"),
]
cost_tbl = "".join(f"<tr><td>{k}</td><td>{d}</td><td class='num'>{eur(-c[k])}</td></tr>" for k, d in cost_rows)
cost_tbl += ("<tr><td>Аэронавигационные сборы</td><td>Сбор считается по ортодромии между точками входа и выхода из зоны, "
             "круг его не меняет</td><td class='num'>€0</td></tr>"
             "<tr><td>Лизинг, каскад задержек</td><td>Лизинг — фиксированный платёж. Самолёт ночует в MAN, следующий вылет утром</td>"
             "<td class='num'>€0</td></tr>")
cost_tbl += (f"<tr class='tot'><td>Итого издержки</td><td>Допуск {eur(m.ops_lo)} … {eur(m.ops_hi)}; ≈ "
             f"{ru(b['C'] / m.flight_rev * 100, 1)}% выручки рейса (≈ {eur(m.flight_rev)})</td><td class='num'>{eur(-b['C'])}</td></tr>")

assump_tbl = "".join(
    f"<tr><td>{p[4]}</td><td>{KIND[p[7]]}</td><td>{p[3]}</td><td class='num'>{fmt_param(k, p[0])}</td>"
    f"<td class='num b'>{fmt_param(k, p[1])}</td><td class='num'>{fmt_param(k, p[2])}</td><td>{p[5]}</td></tr>"
    for k, p in m.P.items())

scen_rows = [("Издержки манёвра", "C", -1), ("Лояльность пассажиров на борту", "onboard", 1),
             ("Медиа → новые бронирования", "media", 1), ("Чистый эффект Δ (B − A)", "net", 1)]
scen_tbl = "".join(
    f"<tr{' class=tot' if key == 'net' else ''}><td>{lab}</td>" + "".join(
        f"<td class='num'>{eur(sg * s[k][key])}</td>" for k in ("pess", "base", "opt")) + "</tr>"
    for lab, key, sg in scen_rows)

media_gross = b["media"] / bv["sent"]
unit = bv["trip_rev"] * bv["cm"]
annoy_loss = bv["pax"] * bv["annoyed"] * m.ANNOY_LOSS * unit
# полный перечень эффектов: (категория, эффект, знак, как учтён, значение)
EFFECTS = [
    ("Операционные", "Дополнительное топливо", "−", f"{ru(b['fuel_t'] * 1000)} кг × €{bv['fuel_px']}/т (цена 02.2023)", eur(-c["Топливо"])),
    ("Операционные", "Квоты CO₂ (EU ETS)", "−", f"{ru(b['co2_t'], 2)} т × €{bv['ets']}/т", eur(-c["CO₂ (EU ETS)"])),
    ("Операционные", "Техобслуживание (PBH)", "−", "Начисляется за лётные часы", eur(-c["Техобслуживание"])),
    ("Операционные", "Оплата экипажа", "−", f"Переменная часть, +{ru(bv['t_turn'], 1)} мин", eur(-c["Экипаж"])),
    ("Операционные", "Аэронавигационные сборы", "0", "Сбор считается по ортодромии, круг его не меняет", "€0"),
    ("Операционные", "Аэропортовые сборы MAN", "0", "Зависят от MTOW и числа пассажиров; прилёт до ночного периода", "€0"),
    ("Операционные", "Лизинг / владение ВС", "0", "Фиксированный платёж", "€0"),
    ("Операционные", "Каскадные задержки следующих рейсов", "0", "Последний рейс дня, ночёвка в MAN", "€0"),
    ("Операционные", "Рабочее время экипажа (FTL)", "0", "+10 мин к смене ≈ 5 ч; лимиты не задеты", "€0"),
    ("Операционные", "Наземное обслуживание", "−", "Сверхурочные хендлинга", eur(-c["Наземные расходы"])),
    ("Операционные", "Продажи на борту", "±", "Пауза в сервисе против +10 мин полёта, нетто ≈ 0", "≈ €0"),
    ("Пассажиры", "Компенсации EU/UK261", "0", "Ex post задержки ≥ 3 ч не было", "€0"),
    ("Пассажиры", "Пропущенный транспорт, жалобы", "−", "Поздний прилёт ≈ 22:30", eur(-c["Пассажиры: транспорт, жалобы"])),
    ("Пассажиры", "Недовольные: спали, аэрофобия, укачивание", "−", "7% × 0,05 потерянной поездки", eur(-annoy_loss)),
    ("Пассажиры", "Лояльность восхищённых: повторные покупки", "+", "85% × 0,10 доп. поездки × €70 маржи", eur(b["onboard"] + annoy_loss)),
    ("Бренд", "Публикации в СМИ → новые бронирования", "+", "Охват × конверсия × маржа (МК)", eur(media_gross)),
    ("Бренд", "Сарафанное радио, посты пассажиров", "+", "Входит в охват истории", "в медиа"),
    ("Бренд", "Спрос на Исландию, пакеты easyJet holidays", "+", "Входит в конверсию", "в медиа"),
    ("Бренд", "Бренд работодателя: гордость экипажей, найм", "+", "Не монетизируем", "качеств."),
    ("Бренд", "Контент для маркетинга (фото и видео пассажиров)", "+", "Не монетизируем", "качеств."),
    ("Риски", "ESG-критика, «трюк ради лайков»", "−", "Поправка 0,92 к медиаэффекту", eur(b["media"] - media_gross)),
    ("Риски", "Безопасность: крен, пассажиры встают к окнам", "−", "Ex ante EV; ex post — €0", eur(-c["Безопасность и регуляторика (EV)"])),
    ("Риски", "Расход резерва топлива → риск ухода на запасной", "−", "Входит в EV; манёвр больше 5% резерва", "в EV"),
    ("Риски", "Регулятор / УВД", "0", "Манёвр согласован, «controlled manoeuvre»", "€0"),
    ("Риски", "Прецедент: пилоты начнут «катать» без правил", "−", "Вне дельты одного рейса, см. раздел 7", "раздел 7"),
    ("Риски", "Конкуренты копируют, новизна падает", "−", "Затухание медиаэффекта, раздел 7", "раздел 7"),
    ("Вне P&amp;L", "Климат сверх цены ETS + ночные инверсионные следы", "−", f"{ru(b['co2_t'], 2)} т × (€200 соц. цена − €{bv['ets']})", eur(-m.co2_social)),
    ("Вне P&amp;L", "Ценность впечатления для пассажиров", "+", "Готовность платить за полёты к сиянию, €20–40 на человека", "€3–7 тыс."),
    ("Стратегия", "Опцион: продукт «рейсы за сиянием»", "+", "£229–280 × 180 кресел за рейс ≈ 3 блок-часа", "£40–50 тыс./рейс"),
]
eff_tbl = "".join(
    f"<tr><td>{cat}</td><td>{eff}</td><td class='sign {'p' if sg == '+' else ('n' if sg == '−' else 'z')}'>{sg}</td>"
    f"<td>{how}</td><td class='num'>{val}</td></tr>" for cat, eff, sg, how, val in EFFECTS)

rep = m.rep_base

TEMPLATE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Поворот к северному сиянию — P&L-дельта</title>
<style>
@page { size: A4; margin: 13mm 14mm 15mm; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }
body { font-family: 'Inter', 'DejaVu Sans', sans-serif; font-size: 9.3pt; color: #1F2A44; line-height: 1.42; margin: 0; }
.hero { background: linear-gradient(120deg, #0B1D3A 0%, #0B3C5D 55%, #1A9E8F 100%); color: #fff; border-radius: 8px; padding: 18px 22px 16px; }
.hero h1 { font-size: 21pt; margin: 0 0 4px; letter-spacing: -0.3px; }
.hero .sub { color: #CFE9E4; font-size: 10pt; }
.hero .meta { color: #9FC3D6; font-size: 8pt; margin-top: 8px; }
h2 { font-size: 13pt; color: #0B3C5D; border-bottom: 2px solid #1A9E8F; padding-bottom: 3px; margin: 16px 0 7px; break-after: avoid; }
h3 { font-size: 10.3pt; color: #0B3C5D; margin: 11px 0 4px; break-after: avoid; }
p { margin: 4px 0 6px; }
ul { margin: 4px 0 6px; padding-left: 18px; } li { margin: 2px 0; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0 8px; }
.kpi { border: 1px solid #DCE3EC; border-radius: 6px; padding: 8px 10px; background: #F6F8FB; }
.kpi .v { font-size: 15pt; font-weight: 700; color: #0B3C5D; line-height: 1.15; }
.kpi .l { font-size: 7.8pt; color: #5B667A; margin-top: 2px; }
.kpi.pos .v { color: #1A9E8F; } .kpi.neg .v { color: #D1495B; } .kpi.vio .v { color: #6C4FD8; }
table { width: 100%; border-collapse: collapse; font-size: 8.1pt; margin: 5px 0 9px; }
th { background: #0B3C5D; color: #fff; text-align: left; padding: 4px 6px; font-weight: 600; }
td { border-bottom: 1px solid #E3E8EF; padding: 3px 6px; vertical-align: top; }
td.num, th.num { text-align: right; white-space: nowrap; } td.b { font-weight: 700; }
td.sign { text-align: center; font-weight: 700; } td.sign.p { color: #1A9E8F; } td.sign.n { color: #D1495B; } td.sign.z { color: #8A94A6; }
tr { break-inside: avoid; } tr.tot td { font-weight: 700; background: #EEF3F8; border-top: 1.5px solid #0B3C5D; }
.tag { display: inline-block; font-size: 7pt; padding: 0 5px; border-radius: 8px; font-weight: 600; white-space: nowrap; }
.tag.f { background: #E3F4F1; color: #127A6E; } .tag.e { background: #EEF1F6; color: #3E4B63; } .tag.u { background: #EFEBFF; color: #5236C4; }
.callout { border-left: 4px solid #6C4FD8; background: #F4F1FF; padding: 7px 12px; margin: 9px 0; break-inside: avoid; }
.callout.green { border-color: #1A9E8F; background: #EEF8F6; } .callout.red { border-color: #D1495B; background: #FDF0F2; }
.callout.navy { border-color: #0B3C5D; background: #F1F5F9; }
img.chart { width: 100%; margin: 2px 0 4px; break-inside: avoid; }
img.track { width: 100%; border-radius: 6px; margin: 4px 0 2px; }
.pb { break-before: page; } .small { font-size: 7.8pt; color: #5B667A; }
.formula { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.9pt; background: #F6F8FB; border: 1px solid #E3E8EF; border-radius: 4px; padding: 5px 8px; margin: 4px 0 6px; }
.src li { font-size: 7.6pt; word-break: break-all; }
</style></head><body>

<div class="hero">
  <h1>Поворот к северному сиянию: P&amp;L-дельта двух вселенных</h1>
  <div class="sub">easyJet EZY1806 · Рейкьявик (KEF) → Манчестер (MAN) · 27.02.2023 · Airbus A320 · круг 360° на FL370</div>
  <div class="meta">Δ = B (фактический рейс с кругом) − A (тот же рейс в тот же вечер без круга) · цены на дату рейса · горизонт 24 мес. · EUR</div>
</div>

<div class="kpis">
  <div class="kpi pos"><div class="v">{{NET}}</div><div class="l">Δ P&amp;L, базовый сценарий</div></div>
  <div class="kpi neg"><div class="v">{{COST}}</div><div class="l">прямые издержки манёвра (допуск {{OPSLO}} … {{OPSHI}})</div></div>
  <div class="kpi vio"><div class="v">≈ {{REACHBE}}</div><div class="l">зрителей истории для безубыточности ({{REACHBEPCT}}% базового охвата)</div></div>
  <div class="kpi"><div class="v">{{PPOSOP}}%</div><div class="l">P(Δ &gt; 0) без медиаэффекта — только лояльность на борту</div></div>
</div>

<div class="callout green"><b>Вердикт: поворот экономически оправдан, это асимметричная ставка.</b>
Издержки известны почти точно: {{COST}} ({{FUELKG}} кг топлива, {{CO2}} т CO₂). Худший вариант, если все допущения разом
сыграют против, — {{PESS}}. Выигрыш — десятки и сотни тысяч евро: медиана симуляций <b>{{P50}}</b>, P5–P95 — <b>{{P5}} … {{P95}}</b>.
Почти всю выгоду дал медиаэффект новизны. Поэтому при повторениях выгода падает до {{OPP50}} на манёвр — остаётся только лояльность пассажиров на борту.</div>

<h3>Ключевые выводы</h3>
<ul>
<li><b>Издержки малы и посчитаны по факту.</b> Топливо {{C_FUEL}}, квоты CO₂ {{C_CO2}}, ТО {{C_MX}}, экипаж {{C_CREW}},
прочее {{C_REST}}. Это ≈ {{COSTPCT}}% выручки рейса. Сверка с EUROCONTROL: €82,95 за минуту удлинения крейсера × {{TTURN}} мин = {{EC}}.</li>
<li><b>Лояльность ≈ {{PAX}} пассажиров на борту ≈ {{ONBOARD}}</b> — одна она покрывает издержки.
Безубыточность наступает, если ≈ {{UB}}% восхищённых пассажиров совершат одну лишнюю поездку (≈ {{TRIPSBE}} поездок туда-обратно на весь борт).</li>
<li><b>Медиа ≈ {{MEDIA}} — 98% выгоды и главный источник неопределённости.</b> Для окупаемости историю должны увидеть
≈ {{REACHBE}} человек, в базе мы закладываем 15 млн.</li>
<li><b>Риски ex post не материализовались.</b> Ex ante ожидаемые потери — около €10. Главный операционный нюанс: круг сжигает
≈ {{FUELT}} т, больше 5% резерва на непредвиденное (≈ {{CONT}} т). Значит, делать манёвр можно только при запасе топлива сверх плана.</li>
<li><b>Рекомендация:</b> не наказывать и не запрещать, а оформить <b>«Aurora-протокол»</b> с условиями допуска и монетизировать тему.</li>
</ul>

<h2>1. Кейс и прецеденты</h2>
<p>Вечером 27.02.2023, во время сильной геомагнитной бури, капитан рейса EZY1806 приглушил свет в салоне. Сияние сначала видел
только левый борт. Через 2–3 минуты капитан сделал круг 360° к западу от Фарерских островов на высоте 37 000 ft (20:37–20:45 UTC по воспроизведению FR24). Манёвр занял «чуть меньше 10 минут» и виден на треке Flightradar24. easyJet назвал его
«контролируемым манёвром». Готового публичного расчёта P&amp;L по кейсу нет — дельту собираем сами.</p>
<table><tr><th>Дата</th><th>Кто</th><th>Маршрут</th><th>Что сделали</th><th>Для расчёта</th></tr>
<tr><td>27.02.2023</td><td>easyJet EZY1806, A320</td><td>KEF → MAN</td><td>Круг 360° на FL370, &lt; 10 мин</td><td>Базовый кейс</td></tr>
<tr><td>Та же неделя</td><td>Finnair</td><td>Куусамо → Хельсинки</td><td>Внеплановый круг 360°, чтобы сияние увидели оба борта</td><td>Практика повторяется</td></tr>
<tr><td>02.2023</td><td>easyJet × Aerobility</td><td>Благотворительный рейс</td><td>Плановый рейс за сиянием</td><td>Перевозчик сам использует тему</td></tr>
<tr><td>2018–2023</td><td>Omega Breaks</td><td>UK → Шетланды → UK, ≈ 3 ч</td><td>Чартеры за сиянием, £229–280 с человека</td><td>Готовность платить</td></tr>
</table>

<h2>2. Методология: дельта двух вселенных</h2>
<div class="callout navy"><b>Вселенная A</b> — тот же рейс EZY1806 в тот же вечер: тот же самолёт, загрузка, ветер, маршрут и цена топлива, но без круга.
<b>Вселенная B</b> — то, что произошло. Всё общее для обеих вселенных при вычитании сокращается. Остаётся только сам круг
и то, что из него последовало.</div>
<p><b>Почему контроль — тот же рейс, а не рейс за пару дней до этого.</b> У рейса другого дня свой ветер, маршрут и загрузка.
Время в воздухе на маршруте ≈ 2 ч 25 мин из-за этого гуляет на ±10–15 минут — столько же, сколько сам эффект, и прямое вычитание
утонуло бы в шуме. История рейса за соседние дни на FR24, FlightAware и Flightera закрыта (403), поэтому сверка с ними — следующий шаг.
Саму дельту меряем по треку этого рейса.</p>
<img class="track" src="fr24_track_annotated.png">
<p class="small">Трек FR24, U21806, 27.02.2023, кадр 20:27 UTC. Масштаб снят по Фарерским островам:
61,39–62,39° с.ш. ≈ 111 км ≈ 375 px, то есть 0,30 км/px.</p>
<img class="track" src="fr24_loop_frames.png">
<p class="small">Воспроизведение FR24: самолёт проходит точку пересечения трека дважды — в 20:37 (вход в петлю) и в 20:45 UTC (выход).</p>
<p><b>Прямой замер задержки.</b> Самолёт проходит точку самопересечения трека дважды: в <b>20:37</b> и в <b>20:45 UTC</b>.
Раз он вернулся в ту же точку над землёй, время между проходами и есть чистая задержка рейса, поправка на ветер не нужна.
FR24 показывает минуты без секунд, поэтому это <b>8 мин</b> с реальным диапазоном 7–9. Замер подтверждают ещё две независимые оценки:
геометрия петли (Ø ≈ 31 км, радиус ≈ {{R}} км, при M0,78 это крен ≈ {{BANK}}° и ≈ {{T360}} мин) и сообщение FR24
(«чуть меньше 10 минут» на весь манёвр со входом и выходом). База модели: <b>{{TTURN}} мин</b>.</p>
<p><b>Три вида вводных:</b> {{KF}} — факт на дату рейса (цена топлива и CO₂, загрузка, длительность манёвра, отсутствие задержки и инцидентов);
{{KE}} — инженерная или отраслевая оценка с узким допуском; {{KU}} — принципиально непредсказуемое (медиа, поведение пассажиров).
Операционный блок считается детерминированно, с допуском. <b>Монте-Карло — только для параметров вида МК.</b></p>
<table><tr><th>Что известно точно</th><th>Значение</th><th>Источник</th></tr>
<tr><td>Рейс, маршрут, время</td><td>EZY1806 (U21806), KEF → MAN, вылет ≈ 20:00 GMT, круг 20:37–20:45 UTC</td><td>PA Media, FR24</td></tr>
<tr><td>Самолёт</td><td>Airbus A320; бортовой номер не подтверждён, поэтому neo (186 кресел) и ceo (180) взяты в допуск</td><td>FR24</td></tr>
<tr><td>Манёвр</td><td>Круг 360°, FL370, к западу от Фарер, Ø ≈ 31 км, вход 20:37 и выход 20:45 UTC (8 мин)</td><td>Трек FR24, PA Media</td></tr>
<tr><td>Пассажиры</td><td>Загрузка easyJet в янв–мар 2023 = 88% → ≈ {{PAX}} человек</td><td>easyJet Q2 FY23 trading update</td></tr>
<tr><td>Цена керосина</td><td>≈ $105/bbl ≈ $827/т ≈ €{{FUELPX}}/т (EUR/USD 1,06)</td><td>IATA/Platts через Cargo Facts</td></tr>
<tr><td>Цена квоты EU ETS</td><td>≈ €96/т (€98,3 на 20.02.2023, рекорд €99,99)</td><td>GMK Center, ICE</td></tr>
<tr><td>Дистанция и EU261</td><td>KEF–MAN ≈ 1 660 км → категория €400; задержки ≥ 3 ч не было</td><td>Регламент 261/2004</td></tr>
</table>

<h2 class="pb">3. Полный перечень эффектов (база)</h2>
<table><tr><th>Блок</th><th>Эффект</th><th>Знак</th><th>Как учтён</th><th class="num">Δ</th></tr>{{EFFECTS}}</table>

<h2 class="pb">4. Вводные</h2>
<table><tr><th>Параметр</th><th>Вид</th><th>Ед.</th><th class="num">Мин</th><th class="num">База</th><th class="num">Макс</th><th>Источник / логика</th></tr>
{{ASSUMP}}</table>
<p class="small">Константы: 3,16 кг CO₂ на кг керосина (ICAO); компенсация EU261 — €400; претензию подают 50% пассажиров;
недовольный пассажир теряет 0,05 поездки; 7,88 bbl в тонне Jet A-1. Пессимистичный сценарий — все издержки на максимуме,
все выгоды на минимуме; оптимистичный — наоборот.</p>

<h2>5. Расчёт по блокам</h2>
<h3>5.1 Операционные издержки: детерминированно, по факту</h3>
<table><tr><th>Статья</th><th>Расчёт</th><th class="num">Δ</th></tr>{{COSTTBL}}</table>
<p class="small">Для сравнения: если бы такой круг случился сегодня (керосин 2026 ≈ $152/bbl, EUA ≈ €80), издержки составили бы ≈ {{TODAY}}.</p>

<h3>5.2 Лояльность пассажиров на борту</h3>
<div class="formula">{{PAX}} пасс. × 85% восхищённых × 0,10 доп. поездки × (€200 × 35% маржи) − {{PAX}} × 7% недовольных × 0,05 × €70 ≈ {{ONBOARD}}</div>
<p>Сверка с готовностью платить: за ≈ 3 часа поиска сияния в небе люди платят £229–280. Значит, гарантированные 10 минут сияния
стоят для пассажира порядка €20–40, а на весь рейс это «подарок» на €3–7 тыс. В P&amp;L мы засчитываем только ту часть (≈ 15–30%),
что вернётся повторными покупками.</p>

<h3>5.3 Медиа → новые бронирования</h3>
<div class="formula">15 млн охват × 70% на рынках easyJet × 85% эффекта именно от круга × 0,008% конверсия × €70 маржи × 0,92 ≈ {{MEDIA}}</div>
<p>Конверсия 1 к 12 500 откалибрована так, чтобы окупаемость совпадала с платной рекламой: CPM €8 и ROI ≈ 2×.
Справочно: «медийная стоимость» (охват × CPM) — {{EMV}}, AVE по аудитории изданий — порядка €1 млн. Эти показатели завышают эффект,
поэтому в P&amp;L идёт только маржа с дополнительных поездок.</p>

<h3>5.4 Риски</h3>
<table><tr><th>Риск</th><th>Механизм</th><th>Ex post</th><th>Как снизить</th></tr>
<tr><td>Безопасность в салоне</td><td>Пассажиры встают к окнам во время крена; турбулентность</td><td>Не было</td><td>Табло «пристегнуть ремни», крен ≤ 25°</td></tr>
<tr><td>Топливо</td><td>Круг ≈ {{FUELT}} т — больше 5% резерва на непредвиденное (≈ {{CONT}} т)</td><td>Не было</td><td>Только при запасе топлива сверх плана; финальный и запасной резервы не трогать</td></tr>
<tr><td>Регулятор / УВД</td><td>Нужно разрешение на эшелоне</td><td>Получено</td><td>Только с разрешения, в малозагруженном воздушном пространстве</td></tr>
<tr><td>Задержка / EU261</td><td>+10 мин могут перевести рейс через порог 3 ч или сломать стыковки</td><td>Не было</td><td>Не делать при задержке &gt; 60 мин</td></tr>
<tr><td>Репутация / ESG</td><td>+{{CO2}} т CO₂ ради «аттракциона»</td><td>Тон позитивный</td><td>Поправка 0,8–1,0 к медиаэффекту</td></tr>
<tr><td>Прецедент</td><td>Рутинный манёвр: издержки остаются, новизна исчезает</td><td>—</td><td>Регламент, раздел 7</td></tr>
</table>

<h2 class="pb">6. Результаты</h2>
<img class="chart" src="charts/waterfall.svg">
<table><tr><th>Блок P&amp;L</th><th class="num">Пессимистичный</th><th class="num">Базовый</th><th class="num">Оптимистичный</th></tr>{{SCEN}}</table>
<h3>Монте-Карло: только по непредсказуемым параметрам</h3>
<img class="chart" src="charts/mc.svg">
<p>Факты и оценки зафиксированы на базе, разыгрываются только 9 параметров вида МК (треугольные распределения).
P(Δ &gt; 0) ≈ 100%, медиана {{P50}}, среднее {{MEAN}}, P5–P95 = {{P5}} … {{P95}}.
<b>Без медиаэффекта</b> (только лояльность на борту): медиана {{OPP50}}, P5–P95 = {{OPP5}} … {{OPP95}}, P(Δ &gt; 0) = {{PPOSOP}}%.</p>
<div class="callout navy"><b>Как мы работаем с неопределённостью.</b>
(1) Всё, что можно измерить, взято по факту рейса: цены на 27.02.2023, загрузка, геометрия круга по треку. Это детерминированный блок
с допуском {{OPSLO}} … {{OPSHI}}.
(2) Непредсказуемое — охват, конверсию, поведение пассажиров — мы не угадываем, а проверяем порогом. Вывод «круг оправдан» верен,
если историю увидели хотя бы ≈ {{REACHBE}} человек, то есть ≈ {{REACHBEPCT}}% базового охвата. Даже если охват завышен в 30–50 раз, знак вывода не меняется.
(3) Монте-Карло показывает разброс величины эффекта, а не знака: P(Δ &gt; 0) ≈ 100%.</div>
<h3>Чувствительность (торнадо)</h3>
<img class="chart" src="charts/tornado.svg">
<p>Итог определяют медиапараметры. Факты по рейсу — топливо, CO₂, длительность круга — сдвигают его на сотни евро, а не на тысячи.</p>

<h2>7. Масштабирование и рекомендации</h2>
<img class="chart" src="charts/repeat.svg">
<p>Первый круг даёт {{R1}}, второй {{R2}}, пятый ≈ {{R5}}. Дальше выгода сходится к чистой операционке. Если лояльность
консервативная, манёвр уходит в минус уже с 6-го повторения. <b>Ценность создаёт новизна истории, а не сам манёвр.</b></p>
<div class="callout"><b>Aurora-протокол (условия допуска):</b>
<ul>
<li>разрешение УВД, малозагруженное воздушное пространство, ночь, крен ≤ 25°, не более одного круга (≤ 10 мин);</li>
<li>запас топлива сверх плана не меньше расхода на манёвр (≈ 0,3–0,4 т); финальный и запасной резервы не трогать;</li>
<li>задержка рейса ≤ 60 мин, последний рейс дня или ротация с запасом, нет ночных ограничений в аэропорту прилёта;</li>
<li>табло «пристегнуть ремни» включено, объявление в салоне, свет приглушён; КВС фиксирует манёвр в бортжурнале.</li>
</ul></div>
<div class="callout green"><b>Монетизация:</b> рейсы за сиянием по модели Omega Breaks (£229–280 × 180 кресел ≈ £40–50 тыс. выручки
за ≈ 3 блок-часа); сезонные пакеты easyJet holidays в Исландию с контентом пассажиров; публичная благодарность экипажу
без обещаний повторить.</div>

<h2 class="pb">8. За пределами авиакомпании: кто ещё выигрывает и теряет</h2>
<table><tr><th>Сторона</th><th>Эффект</th><th>Знак</th><th class="num">Оценка</th><th>Природа</th></tr>
<tr><td>Пассажиры на борту</td><td>Ценность впечатления: готовность платить €20–40 × {{PAX}}</td><td class="sign p">+</td><td class="num">€3–7 тыс.</td><td>реальная ценность</td></tr>
<tr><td>Пассажиры на борту</td><td>Потерянное время: {{PAX}} × {{TTURN}} мин × €20/ч</td><td class="sign n">−</td><td class="num">{{PAXTIME}}</td><td>реальная ценность</td></tr>
<tr><td>Общество, климат</td><td>{{CO2}} т CO₂ × €200/т (соц. цена углерода); EU ETS уже покрыл {{C_CO2}}</td><td class="sign n">−</td><td class="num">{{CO2FULL}}</td><td>реальная, внешний остаток {{CO2EXT}}</td></tr>
<tr><td>Общество, климат</td><td>Неуглеродные эффекты: ночные инверсионные следы</td><td class="sign n">−</td><td class="num">до ×1–2 к CO₂</td><td>реальная ценность</td></tr>
<tr><td>Бюджеты ЕС и ЕЭЗ</td><td>Доход от продажи квот EU ETS</td><td class="sign p">+</td><td class="num">{{C_CO2}}</td><td>перераспределение</td></tr>
<tr><td>Поставщик топлива, MRO</td><td>Выручка за топливо и лётные часы</td><td class="sign p">+</td><td class="num">{{FUELMX}}</td><td>перераспределение</td></tr>
<tr><td>СМИ и платформы</td><td>Трафик и реклама на истории (≈ €8 на 1000 просмотров × охват)</td><td class="sign p">+</td><td class="num">≈ {{EMV}}</td><td>реальная (внимание аудитории)</td></tr>
<tr><td>Flightradar24</td><td>Трафик и узнаваемость: трек с кругом — главный визуал истории</td><td class="sign p">+</td><td class="num">качеств.</td><td>—</td></tr>
<tr><td>Исландия, туризм</td><td>≈ 30% доп. поездок — в Исландию: ≈ {{ISTRIPS}} туристов × €1 500 расходов</td><td class="sign p">+</td><td class="num">≈ {{ISSPEND}}</td><td>частично перераспределение</td></tr>
<tr><td>Конкуренты (Icelandair, Jet2 и др.)</td><td>Часть доп. бронирований easyJet переключена от них</td><td class="sign n">−</td><td class="num">до 50% медиаэффекта</td><td>перераспределение</td></tr>
<tr><td>УВД (Isavia, NATS), аэропорт MAN</td><td>Кратковременная нагрузка на диспетчера, прилёт на ~8 мин позже</td><td class="sign z">0</td><td class="num">≈ €0</td><td>—</td></tr>
<tr><td>Пилот и экипаж</td><td>Признание и гордость; без регламента — риск разбирательства</td><td class="sign z">±</td><td class="num">качеств.</td><td>—</td></tr>
<tr><td>Отрасль и регуляторы</td><td>Прецедент, дискуссия о культуре безопасности</td><td class="sign z">±</td><td class="num">качеств.</td><td>—</td></tr>
</table>
<div class="callout green"><b>Общественный баланс тоже положителен.</b> Уберём перераспределения: квоты ETS, выручку поставщиков,
переток от конкурентов. Остаются реальные эффекты: ценность впечатления для пассажиров (€3–7 тыс.) против реальных издержек —
ресурсов на топливо, ТО и экипаж ({{RESOURCES}}), климата по полной социальной цене ({{CO2FULL}}) и времени пассажиров ({{PAXTIME}}).
Сверх этого — внимание миллионов читателей: СМИ монетизировали его примерно на {{EMV}}.</div>

<h2>9. Ограничения и как уточнить</h2>
<ul>
<li>Для финальной версии выгрузить ADS-B/FR24-историю EZY1806 за 20–27.02.2023: точная длительность круга, бортовой номер,
время в воздухе соседних дней для сверки.</li>
<li>Внутренние данные easyJet: фактическое число пассажиров, расход по FDM/QAR, опрос NPS этого рейса, атрибуция бронирований
(рост брендовых запросов «easyJet northern lights», бронирования на KEF в марте–апреле 2023).</li>
<li>Охват и конверсия медиа — экспертные оценки. Поэтому модель показывает порог: безубыточность наступает при ≈ {{REACHBE}} зрителей.</li>
<li>Не учтены дисконтирование (&lt; 5% за 24 мес.) и каннибализация бронирований. Внешние эффекты — климат и ценность впечатления —
приведены справочно, в P&amp;L не входят.</li>
</ul>

<h2>Источники</h2>
<ol class="src">
<li>PA Media via Yahoo News: uk.news.yahoo.com/pilot-makes-360-degree-turn-124652589.html</li>
<li>LBC: lbc.co.uk/article/pilot-turn-northern-lights-easyjet-DWzSkN_2/</li>
<li>Guernsey Press (PA): guernseypress.com/news/uk-news/2023/02/28/pilot-makes-360-degree-turn-at-37000ft-to-let-passengers-view-northern-lights</li>
<li>Express &amp; Star: expressandstar.com/news/uk-news/2023/02/28/newly-betrothed-see-northern-lights-on-flight-home-after-foiled-aurora-proposal</li>
<li>1News NZ (Finnair): 1news.co.nz/2023/03/01/european-flights-detour-to-give-passengers-view-of-northern-lights</li>
<li>Flightradar24 blog: flightradar24.com/blog/flight-tracking-news/just-for-fun/pilots-give-passengers-surprise-northern-lights-flights/</li>
<li>AirNav Radar: airnavradar.com/blog/easyjet-to-operate-charity-northern-lights-flight-in-2023</li>
<li>Omega Breaks: sellingtravel.co.uk/?p=33785 ; leedsbradfordairport.co.uk/the-latest/omega-breaks-northern-lights-20th</li>
<li>easyJet Q2 FY23 trading update (load factor 88%): lse.co.uk/rns/EZJ/trading-update-for-the-six-months-ended-31-march-2023-62itrvgkwln55al.html</li>
<li>Jet fuel, Feb 2023 (IATA/Platts): cargofacts.com/allposts/jet-fuel-rates-drop-globally-mom/</li>
<li>EUA, Feb 2023: gmk.center/en/news/the-price-of-carbon-emissions-in-the-eu-has-almost-reached-e100-per-ton/</li>
<li>EUROCONTROL Standard Inputs, cost of delay: ansperformance.eu/economics/cba/standard-inputs/chapters/cost_of_delay.html</li>
<li>IATA 2026 fuel outlook (сравнение «сегодня»): afm.aero/iata-reports-121percent-global-jet-fuel-price-shock-in-2026-with-india-and-japan-most-exposed</li>
<li>Регламент (ЕС) 261/2004 и UK261 — компенсации при задержке ≥ 3 ч</li>
</ol>
</body></html>"""

ctx = {
    "NET": eur(b["net"], True), "COST": eur(b["C"]), "OPSLO": eur(m.ops_lo), "OPSHI": eur(m.ops_hi),
    "COSTPCT": ru(b["C"] / m.flight_rev * 100, 0),
    "REACHBE": f"{ru(m.reach_be / 1e3, 0)} тыс.", "REACHBEPCT": ru(m.reach_be / bv["reach"] * 100, 1),
    "PPOSOP": ru(mc["p_pos_op"] * 100, 0), "PESS": eur(s["pess"]["net"], True),
    "P50": eur(mc["p50"], True), "P5": eur(mc["p5"], True), "P95": eur(mc["p95"], True), "MEAN": eur(mc["mean"], True),
    "OPP50": eur(mc["op_p50"], True), "OPP5": eur(mc["op_p5"], True), "OPP95": eur(mc["op_p95"], True),
    "TTURN": ru(bv["t_turn"], 1), "FUELKG": ru(b["fuel_t"] * 1000, 0), "FUELT": ru(b["fuel_t"], 2),
    "CO2": ru(b["co2_t"], 2), "C_FUEL": eur(c["Топливо"]), "C_CO2": eur(c["CO₂ (EU ETS)"]),
    "C_MX": eur(c["Техобслуживание"]), "C_CREW": eur(c["Экипаж"]),
    "C_REST": eur(c["Наземные расходы"] + c["Пассажиры: транспорт, жалобы"] + c["Риск EU/UK261"]
                  + c["Безопасность и регуляторика (EV)"]),
    "EC": eur(m.eurocontrol_check), "ONBOARD": eur(b["onboard"]), "MEDIA": eur(b["media"]),
    "UB": ru(m.uplift_be * 100, 0), "TRIPSBE": ru(m.trips_be, 0), "CONT": ru(m.contingency_t, 2), "EMV": eur(m.emv),
    "R": ru(m.R_km, 0), "T360": ru(m.t360, 1), "PAX": str(bv["pax"]), "FUELPX": ru(bv["fuel_px"]),
    "TODAY": eur(m.today["C"]), "R1": eur(rep[0], True), "R2": eur(rep[1], True), "R5": eur(rep[4], True),
    "KF": KIND["F"], "BANK": ru(m.bank_deg, 0),
    "PAXTIME": eur(-bv["pax"] * bv["t_turn"] / 60 * 20), "CO2FULL": eur(-b["co2_t"] * 200), "CO2EXT": eur(-m.co2_social),
    "FUELMX": eur(c["Топливо"] + c["Техобслуживание"]), "ISTRIPS": ru(m.media_trips * 0.3, 0),
    "ISSPEND": eur(m.media_trips * 0.3 * 1500), "RESOURCES": eur(-(c["Топливо"] + c["Техобслуживание"] + c["Экипаж"])), "KE": KIND["E"], "KU": KIND["U"],
    "ASSUMP": assump_tbl, "COSTTBL": cost_tbl, "SCEN": scen_tbl, "EFFECTS": eff_tbl,
}
html = TEMPLATE
for k, v in ctx.items():
    html = html.replace("{{" + k + "}}", v)
assert "{{" not in html, html[html.index("{{"):html.index("{{") + 40]
HTML.write_text(html, encoding="utf-8")

subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, capture_output=True)
print("PDF:", PDF)
