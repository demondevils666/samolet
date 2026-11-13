"""Unit economics of a men's steel jewelry set (chain + bracelet + ring) on Wildberries (FBO).

Every input is either SOURCED (see data/other_cost_inputs.csv, data/wb_commissions.csv)
or an explicit ASSUMPTION. Change the numbers at the top and re-run:
    python3 unit_economics.py
Writes data/landed_cost.csv and data/unit_economics_wb.csv
"""
import csv
import itertools
from pathlib import Path

DATA = Path(__file__).parent / "data"

# ---------------- landed cost of one set -----------------------------------
CNY_RUB = 12.4009   # ЦБ РФ на 13.11.2026 (cbr.ru/scripts/XML_daily.asp)
USD_RUB = 82.9803   # ЦБ РФ на 13.11.2026
# Закупка, юани. Цены «от» с публичных страниц 1688 (data/sourcing_1688_market.csv,
# 259 мужских позиций из стали/титана); «от» обычно = самый короткий/тонкий вариант.
GOODS = {
    #            chain bracelet ring  box/pouch
    "дешёвый (медианы цен «от»)":       (2.0, 5.2, 3.0, 1.25),
    "реалистичный (p75 цен «от»)":      (3.5, 8.0, 11.8, 2.15),
    "качество+ (выше p75, плотный бокс)": (8.0, 15.0, 12.0, 5.0),
}
AGENT_FEE = 0.05        # ДОПУЩЕНИЕ: байер/посредник 3–7 %
CN_DOMESTIC_CNY = 0.5   # ДОПУЩЕНИЕ: доставка по Китаю до склада карго, на сет
SET_WEIGHT_KG = 0.15    # ДОПУЩЕНИЕ: цепь 30–60 г + браслет 20–40 г + кольцо 5–10 г + коробка
CARGO_USD_KG = 5.0      # «белая» доставка $3–10/кг (agb-global.com, 2026); «карго» $1.1–2.5/кг
RU_PREP_RUB = 40        # ДОПУЩЕНИЕ: штрихкод, пакет, сборка поставки на WB
DEFECT = 0.05           # ДОПУЩЕНИЕ: брак/пересорт, доля от закупки

# ---------------- WB ------------------------------------------------------
COMMISSION_FBO = 0.375  # «Комплекты украшений», FBO, справочник WB на 01.08.2026 (iseller.pro)
LOGISTICS_BASE = 32     # ₽, верх «лесенки» 23–32 ₽ для товара до 1 л (тарифы 29.07.2026)
WAREHOUSE_COEF = 1.25   # ДОПУЩЕНИЕ: Москва ×1, регионы 1.15–2.8
ACCEPTANCE = 10         # ДОПУЩЕНИЕ: усреднённая приёмка, ₽/ед
STORAGE = 3             # ДОПУЩЕНИЕ: ₽ на проданную единицу
ACQUIRING = 0.025       # ДОПУЩЕНИЕ: в источниках 0.4–5 %
TAX = 0.06              # УСН «доходы» 6 % без НДС — проверить режим/лимиты 2026
PRICES = [1500, 2500]
BUYOUT = [0.85, 0.70]   # нет данных по категории: сценарии
DRR = [0.10, 0.20]      # нет данных по нише: сценарии


def landed(chain, bracelet, ring, box):
    goods = chain + bracelet + ring + box
    cny = goods * (1 + AGENT_FEE) + CN_DOMESTIC_CNY
    goods_rub = cny * CNY_RUB
    cargo = SET_WEIGHT_KG * CARGO_USD_KG * USD_RUB
    defect = (chain + bracelet + ring) * CNY_RUB * DEFECT
    total = goods_rub + cargo + RU_PREP_RUB + defect
    return {"goods_cny": round(goods, 2), "goods_rub_incl_agent": round(goods_rub),
            "cargo_rub": round(cargo), "ru_prep_rub": RU_PREP_RUB,
            "defect_reserve_rub": round(defect), "landed_cost_rub": round(total)}


def unit(price, buyout, drr, cogs):
    fwd = LOGISTICS_BASE * WAREHOUSE_COEF + ACCEPTANCE
    back = LOGISTICS_BASE * WAREHOUSE_COEF
    logistics = fwd / buyout + back * (1 - buyout) / buyout  # на выкупленную единицу
    parts = {"commission_rub": price * COMMISSION_FBO, "acquiring_rub": price * ACQUIRING,
             "logistics_per_sold_rub": logistics, "storage_rub": STORAGE,
             "ads_rub": price * drr, "tax_rub": price * TAX}
    profit = price - sum(parts.values()) - cogs
    return {"price_rub": price, "buyout": buyout, "drr": drr, "landed_cost_rub": cogs,
            **{k: round(v) for k, v in parts.items()},
            "profit_per_sold_rub": round(profit),
            "margin_pct_of_price": round(100 * profit / price, 1),
            "roi_on_cogs_pct": round(100 * profit / cogs)}


def dump(name, rows):
    with (DATA / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


lc = [{"scenario": k, **landed(*v)} for k, v in GOODS.items()]
dump("landed_cost.csv", lc)
rows = [{"cost_scenario": s["scenario"], **unit(p, b, d, s["landed_cost_rub"])}
        for s, p, b, d in itertools.product(lc, PRICES, BUYOUT, DRR)]
dump("unit_economics_wb.csv", rows)
for r in lc:
    print(r)
for r in rows:
    print(r["cost_scenario"][:12], r["price_rub"], r["buyout"], r["drr"],
          "->", r["profit_per_sold_rub"], "₽", r["margin_pct_of_price"], "%")
