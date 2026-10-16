#!/usr/bin/env python3
"""Кейс «Поворот к северному сиянию»: P&L-дельта между вселенной A (тот же рейс без круга)
и вселенной B (круг 360°) для конкретного рейса easyJet EZY1806 KEF→MAN, 27.02.2023.

Параметры трёх видов:
  F — факт на дату рейса (узкий допуск),
  E — инженерная/отраслевая оценка (узкий допуск),
  U — принципиально непредсказуемое (только эти уходят в Монте-Карло).
Операционный блок считается детерминированно (база + допуск), Монте-Карло — только для U."""
import json
import pathlib

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
CH = OUT / "charts"
CH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- константы рейса
EURUSD_2023 = 1.06     # курс 27.02.2023
BBL_PER_T = 7.88       # баррелей Jet A-1 в метрической тонне
CO2_PER_KG = 3.16      # кг CO2 на кг керосина (ICAO)
COMP_261 = 400         # € на пассажира, EU261, 1 500–3 500 км (KEF–MAN ≈ 1 660 км)
CLAIM_RATE = 0.5       # доля пассажиров, подающих претензию
ANNOY_LOSS = 0.05      # потерянных поездок на «недовольного» пассажира
CPM = 8.0              # € за 1000 показов (справочно, для EMV)
SEATS = 186            # A320neo easyJet (A320ceo — 180)

eur_t = lambda usd_bbl, fx=EURUSD_2023: usd_bbl * BBL_PER_T / fx  # $/bbl -> €/т

# ключ: (low, base, high, ед., название, источник/логика, тип c|b, вид F|E|U)
P = {
    "t_turn":   (7.0, 8.0, 9.0, "мин", "Чистая добавка времени полёта от круга",
                 "Воспроизведение FR24: точка пересечения трека пройдена в 20:37 и 20:45 UTC → 8 мин "
                 "(7–9: минуты без секунд); геометрия Ø ≈ 31 км → ≈ 7 мин", "c", "F"),
    "ff":       (2150, 2300, 2450, "кг/ч", "Расход топлива A320 на FL370",
                 "A320neo ≈ 2,15 т/ч … A320ceo ≈ 2,45 т/ч (бортовой номер на 27.02 не подтверждён)", "c", "E"),
    "bank":     (1.03, 1.05, 1.07, "×", "Надбавка расхода в крене ≈ 19°",
                 "n = 1/cos 19° = 1,06; индуктивное сопр. ∝ n² → ≈ +5% расхода", "c", "E"),
    "fuel_px":  (round(eur_t(102)), round(eur_t(105)), round(eur_t(105) * 1.10), "€/т", "Цена Jet A-1, февраль 2023",
                 "IATA/Platts: $2,55/gal (нед. до 17.02) ≈ $107/bbl; $2,43/gal (сер. марта); макс. — +10% into-plane KEF", "c", "F"),
    "ets":      (93, 96, 100, "€/т CO₂", "Квота EU ETS, конец февраля 2023",
                 "EUA Dec-23: €98,3 (20.02.2023), рекорд €99,99; рейс ЕЭЗ→UK в EU ETS", "c", "F"),
    "mx":       (500, 700, 900, "€/лётн. ч", "Техобслуживание (двигатели PBH + планер)", "Отраслевая оценка для A320", "c", "E"),
    "crew":     (0, 200, 400, "€/лётн. ч", "Переменная оплата экипажа (2 + 4)",
                 "Оплата в основном оклад + посекторные доплаты → +10 мин почти бесплатны", "c", "E"),
    "ground":   (0, 30, 100, "€", "Наземные расходы позднего прилёта", "Прилёт ≈ 22:30; смена хендлинга и так на месте", "c", "E"),
    "pax_soft": (0, 50, 200, "€", "Пропущенный транспорт, жалобы", "Последние поезда из MAN ходят до ≈ полуночи", "c", "E"),
    "p261":     (0.0, 0.0, 0.0005, "вер.", "Вероятность пересечь порог 3 ч (EU/UK261)",
                 "Ex post: задержки ≥ 3 ч не было → 0; ex ante — до 0,05%", "c", "F"),
    "safety":   (0, 10, 100, "€", "Ожид. потери: безопасность и регуляторика",
                 "Ex post: инцидентов нет; ex ante: вероятность × ущерб, разрешение УВД получено", "c", "E"),
    "pax":      (158, 164, 168, "чел.", "Пассажиров на борту",
                 "Загрузка easyJet янв–мар 2023 = 88% × 186 (neo) / 180 (ceo) кресел", "b", "F"),
    "trip_rev": (180, 200, 220, "€", "Выручка с поездки туда-обратно", "≈ €100 на пассажиро-сегмент с допуслугами (easyJet FY23–24)", "b", "E"),
    "delighted": (0.60, 0.85, 0.95, "доля", "Доля «восхищённых» пассажиров", "Отзывы и посты пассажиров; без опроса", "b", "U"),
    "uplift":   (0.03, 0.10, 0.25, "поездок/чел.", "Доп. поездки на восхищённого (24 мес.)",
                 "Эффект «пик–конец», рост NPS; прямых данных нет", "b", "U"),
    "annoyed":  (0.02, 0.07, 0.15, "доля", "Доля недовольных (спали, аэрофобия, транспорт)", "Оценка", "c", "U"),
    "cm":       (0.25, 0.35, 0.45, "доля", "Маржинальность доп. пассажира", "За вычетом сборов, дистрибуции, вытеснения", "b", "U"),
    "reach":    (3e6, 15e6, 50e6, "чел.", "Эффективный охват истории",
                 "Синдикация PA, Sky News, ITV, LBC, Yahoo, соцсети, СМИ NZ/US/LatAm", "b", "U"),
    "core":     (0.50, 0.70, 0.80, "доля", "Доля охвата на рынках easyJet (UK/ЕС)", "Оценка по географии СМИ", "b", "U"),
    "attr":     (0.60, 0.85, 1.00, "доля", "Доля медиаэффекта, созданная именно кругом",
                 "Во вселенной A левый борт всё равно видел сияние", "b", "U"),
    "conv":     (0.00002, 0.00008, 0.00025, "доля", "Конверсия охвата в доп. поездку (12–24 мес.)",
                 "Калибровка: окупаемость как у платного медиа, ≈ 2× при CPM €8", "b", "U"),
    "sent":     (0.80, 0.92, 1.00, "×", "Поправка на негатив (ESG-критика, «трюк»)", "Оценка по тону публикаций", "b", "U"),
}

COST_LABELS = ["Топливо", "CO₂ (EU ETS)", "Техобслуживание", "Экипаж", "Наземные расходы",
               "Пассажиры: транспорт, жалобы", "Риск EU/UK261", "Безопасность и регуляторика (EV)"]


def model(v):
    h = v["t_turn"] / 60
    fuel_t = v["ff"] * h * v["bank"] / 1000
    unit = v["trip_rev"] * v["cm"]
    c = dict(zip(COST_LABELS, [
        fuel_t * v["fuel_px"],
        fuel_t * CO2_PER_KG * v["ets"],
        v["mx"] * h,
        v["crew"] * h,
        v["ground"],
        v["pax_soft"],
        v["p261"] * v["pax"] * COMP_261 * CLAIM_RATE,
        v["safety"],
    ]))
    onboard = (v["pax"] * v["delighted"] * v["uplift"] * unit
               - v["pax"] * v["annoyed"] * ANNOY_LOSS * unit)
    media = v["reach"] * v["core"] * v["attr"] * v["conv"] * unit * v["sent"]
    C = sum(c.values())
    return dict(costs=c, onboard=onboard, media=media, C=C, B=onboard + media,
                net=onboard + media - C, net_op=onboard - C, fuel_t=fuel_t, co2_t=fuel_t * CO2_PER_KG)


def vals(which):
    idx = {"low": 0, "base": 1, "high": 2}[which]
    return {k: p[idx] for k, p in P.items()}


def scenario(kind, kinds=("F", "E", "U")):
    """pess: издержки на max, выгоды на min; opt — наоборот (только для указанных видов параметров)."""
    out = vals("base")
    for k, p in P.items():
        if p[7] not in kinds:
            continue
        bad = p[2] if p[6] == "c" else p[0]
        good = p[0] if p[6] == "c" else p[2]
        out[k] = bad if kind == "pess" else good
    return out


bv = vals("base")
base = model(bv)
scen = {"pess": model(scenario("pess")), "base": base, "opt": model(scenario("opt"))}
# допуск операционного блока: только F/E-параметры
ops_lo = model(scenario("opt", ("F", "E")))["C"]
ops_hi = model(scenario("pess", ("F", "E")))["C"]
# «если бы сегодня»: керосин 2026 ≈ $152/bbl, EUA ≈ €80, EUR/USD 1,15
today = model(dict(bv, fuel_px=eur_t(152, 1.15), ets=80))

# ---------------------------------------------------------------- Монте-Карло: только U
N = 200_000
rng = np.random.default_rng(42)
mc_v = {k: (rng.triangular(p[0], p[1], p[2], N) if p[7] == "U" else np.full(N, float(p[1])))
        for k, p in P.items()}
mc = model(mc_v)
net = mc["net"]
q = np.percentile(net, [5, 25, 50, 75, 95])
mc_stats = dict(p_pos=float((net > 0).mean()), p5=q[0], p25=q[1], p50=q[2], p75=q[3], p95=q[4],
                mean=float(net.mean()), p_pos_op=float((mc["net_op"] > 0).mean()),
                op_p5=float(np.percentile(mc["net_op"], 5)), op_p50=float(np.percentile(mc["net_op"], 50)),
                op_p95=float(np.percentile(mc["net_op"], 95)),
                media_p5=float(np.percentile(mc["media"], 5)), media_p95=float(np.percentile(mc["media"], 95)),
                onb_p5=float(np.percentile(mc["onboard"], 5)), onb_p95=float(np.percentile(mc["onboard"], 95)))

# ---------------------------------------------------------------- торнадо
tornado = []
for k, p in P.items():
    a = model(dict(bv, **{k: p[0]}))["net"]
    b_ = model(dict(bv, **{k: p[2]}))["net"]
    tornado.append((p[4] + (" *" if p[7] != "U" else ""), a, b_, abs(b_ - a)))
tornado.sort(key=lambda t: t[3], reverse=True)

# ---------------------------------------------------------------- безубыточность и повторения
unit = bv["trip_rev"] * bv["cm"]
per_viewer = bv["core"] * bv["attr"] * bv["conv"] * unit * bv["sent"]
reach_be = base["C"] / per_viewer
uplift_be = (base["C"] + bv["pax"] * bv["annoyed"] * ANNOY_LOSS * unit) / (bv["pax"] * bv["delighted"] * unit)
trips_be = base["C"] / unit
DECAY = 0.35
reps = np.arange(1, 9)
rep_base = base["onboard"] - base["C"] + base["media"] * DECAY ** (reps - 1)
mcons = model(dict(bv, uplift=P["uplift"][0]))
rep_cons = mcons["onboard"] - mcons["C"] + mcons["media"] * DECAY ** (reps - 1)

emv = bv["reach"] * CPM / 1000
flight_rev = bv["pax"] * bv["trip_rev"] / 2
trip_fuel_t = 2.3 * 2.4             # KEF–MAN ≈ 2 ч 25 мин в воздухе
contingency_t = 0.05 * trip_fuel_t
eurocontrol_check = 82.95 * bv["t_turn"]
V = 447 * 0.5144                    # TAS при M0,78 на FL370 ≈ 447 уз, м/с
R = 31_000 / 2                      # радиус по треку FR24: Ø ≈ 31 км (масштаб по Фарерам, 0,30 км/px)
R_km = R / 1000
bank_deg = float(np.degrees(np.arctan(V ** 2 / (9.81 * R))))
t360 = 2 * np.pi * R / V / 60
media_trips = bv["reach"] * bv["core"] * bv["attr"] * bv["conv"]
co2_social = base["co2_t"] * (200 - bv["ets"])  # справочно: соц. цена углерода ≈ €200/т сверх ETS

# ---------------------------------------------------------------- графики
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#9AA3B2", "axes.labelcolor": "#1F2A44",
                     "xtick.color": "#1F2A44", "ytick.color": "#1F2A44", "svg.fonttype": "path"})
RED, TEAL, VIOLET, NAVY, GREY = "#D1495B", "#1A9E8F", "#6C4FD8", "#0B3C5D", "#8A94A6"


def ru(x, d=0):
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def waterfall(ax, labels, values, colors, total_label, fmt, pad):
    run = 0
    for i, (val, col) in enumerate(zip(values, colors)):
        bottom = run if val >= 0 else run + val
        ax.bar(i, abs(val), bottom=bottom, color=col, width=0.62)
        ax.text(i, max(run, run + val) + pad, fmt(val, True), ha="center", va="bottom", fontsize=8)
        ax.plot([i + 0.31, i + 0.69], [run + val] * 2, color=GREY, lw=0.6)
        run += val
    i = len(labels)
    ax.bar(i, run, color=NAVY, width=0.62)
    ax.text(i, max(run, 0) + pad, fmt(run, False), ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(range(len(labels) + 1))
    ax.set_xticklabels(labels + [total_label], fontsize=8)
    ax.axhline(0, color="#1F2A44", lw=0.8)


if __name__ == "__main__" or True:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"width_ratios": [1.35, 1]})
    c = base["costs"]
    op_labels = ["Топливо\n+ CO₂", "ТО +\nэкипаж", "Задержка,\nпассажиры", "Риски\n(ex ante)", "Лояльность\nна борту"]
    op_vals = [-(c["Топливо"] + c["CO₂ (EU ETS)"]), -(c["Техобслуживание"] + c["Экипаж"]),
               -(c["Наземные расходы"] + c["Пассажиры: транспорт, жалобы"]),
               -(c["Риск EU/UK261"] + c["Безопасность и регуляторика (EV)"]), base["onboard"]]
    waterfall(axes[0], op_labels, op_vals, [RED] * 4 + [TEAL], "Итого\nбез медиа",
              lambda v, s: ("+" if v > 0 and s else "−" if v < 0 else "") + "€" + ru(abs(v)), 20)
    axes[0].set_title("Операционный уровень, €", fontsize=10, loc="left", color=NAVY, fontweight="bold")
    cs = np.cumsum(op_vals)
    axes[0].set_ylim(min(0, cs.min()) - 120, max(cs.max(), 0) + 240)
    full_vals = [-base["C"] / 1000, base["onboard"] / 1000, base["media"] / 1000]
    waterfall(axes[1], ["Издержки", "Лояльность\nна борту", "Медиа →\nбронирования"], full_vals,
              [RED, TEAL, VIOLET], "Итого\nΔ (B − A)",
              lambda v, s: ("+" if v > 0 and s else "−" if v < 0 else "") + "€" + ru(abs(v), 1) + "k", 1.0)
    axes[1].set_title("Полный эффект, € тыс.", fontsize=10, loc="left", color=NAVY, fontweight="bold")
    axes[1].set_ylim(-5, base["net"] / 1000 * 1.18)
    fig.tight_layout()
    fig.savefig(CH / "waterfall.svg")
    plt.close(fig)

    top = tornado[:10][::-1]
    fig, ax = plt.subplots(figsize=(10, 3.9))
    bn = base["net"] / 1000
    for i, (lab, a, b_, _) in enumerate(top):
        a, b_ = a / 1000, b_ / 1000
        ax.barh(i, a - bn, left=bn, color=RED if a < bn else TEAL, height=0.6)
        ax.barh(i, b_ - bn, left=bn, color=TEAL if b_ > bn else RED, height=0.6)
        ax.text(min(a, b_) - 1.5, i, "€" + ru(min(a, b_), 0) + "k", va="center", ha="right", fontsize=7.5)
        ax.text(max(a, b_) + 1.5, i, "€" + ru(max(a, b_), 0) + "k", va="center", ha="left", fontsize=7.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([t[0] for t in top], fontsize=8)
    ax.axvline(bn, color=NAVY, lw=1)
    ax.set_xlabel("Чистый эффект Δ (B − A), € тыс.  (параметр: минимум ↔ максимум, остальные — база; * — факт/оценка)")
    lo_all = min(min(t[1], t[2]) for t in top) / 1000
    hi_all = max(max(t[1], t[2]) for t in top) / 1000
    ax.set_xlim(lo_all - 25, hi_all + 25)
    fig.tight_layout()
    fig.savefig(CH / "tornado.svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.1))
    clip = np.percentile(net, 99) / 1000
    ax.hist(net[net / 1000 <= clip] / 1000, bins=120, color=VIOLET, alpha=0.85)
    ymax = ax.get_ylim()[1]
    for val, lab in [(q[0], "P5"), (q[2], "P50"), (q[4], "P95")]:
        ax.axvline(val / 1000, color=NAVY, lw=1, ls="--")
        ax.text(val / 1000, ymax * 0.93, f" {lab}: €{ru(val / 1000, 0)}k", fontsize=8, color=NAVY)
    ax.axvline(0, color=RED, lw=1.2)
    ax.set_xlabel("Чистый эффект Δ (B − A), € тыс.  (200 000 симуляций только по непредсказуемым параметрам U; хвост > P99 не показан)")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    fig.savefig(CH / "mc.svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.0))
    w = 0.38
    ax.bar(reps - w / 2, rep_base / 1000, width=w, color=TEAL, label="База")
    ax.bar(reps + w / 2, rep_cons / 1000, width=w, color=GREY,
           label=f"Консервативная лояльность (+{P['uplift'][0]:.2f} поездки)")
    ax.axhline(0, color="#1F2A44", lw=0.8)
    ax.set_yscale("symlog", linthresh=1)
    ax.set_xticks(reps)
    ax.set_xticklabels([f"{k}-й" for k in reps])
    ax.set_xlabel(f"Номер аналогичного манёвра (новизна истории затухает: каждый следующий × {DECAY})")
    ax.set_ylabel("Δ на манёвр, € тыс. (symlog)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(CH / "repeat.svg")
    plt.close(fig)


def jsonable(o):
    if isinstance(o, dict):
        return {k: jsonable(x) for k, x in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(x) for x in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    return o


res = dict(params={k: dict(zip(["low", "base", "high", "unit", "label", "source", "type", "kind"], p))
                   for k, p in P.items()},
           base=base, scen=scen, ops_range=[ops_lo, ops_hi], today=today, mc=mc_stats, tornado=tornado,
           reach_be=reach_be, uplift_be=uplift_be, trips_be=trips_be, rep_base=rep_base, rep_cons=rep_cons,
           emv=emv, contingency_t=contingency_t, eurocontrol_check=eurocontrol_check, R_km=R_km, t360=t360)
(OUT / "results.json").write_text(json.dumps(jsonable(res), ensure_ascii=False, indent=1))

if __name__ == "__main__":
    print(f"Издержки база: €{base['C']:.0f} (допуск €{ops_lo:.0f}…€{ops_hi:.0f}); топливо {base['fuel_t'] * 1000:.0f} кг, "
          f"CO2 {base['co2_t']:.2f} т; сегодня: €{today['C']:.0f}")
    for k, v in base["costs"].items():
        print(f"   {k}: €{v:.0f}")
    for k, s in scen.items():
        print(f"{k}: C={s['C']:.0f} onboard={s['onboard']:.0f} media={s['media']:.0f} net={s['net']:.0f}")
    print("MC:", {k: round(float(v), 3) for k, v in mc_stats.items()})
    print(f"reach_be={reach_be:,.0f} uplift_be={uplift_be:.3f} trips_be={trips_be:.1f} emv={emv:,.0f} "
          f"EC=€{eurocontrol_check:.0f} R={R_km:.1f} t360={t360:.1f} cont={contingency_t:.2f}t co2_social=€{co2_social:.0f}")
    print("rep_base", [round(x) for x in rep_base], "rep_cons", [round(x) for x in rep_cons])
