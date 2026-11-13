"""Unit economics of a men's steel jewelry set on Wildberries (FBO).

Every input is either sourced (see SOURCES) or an explicit ASSUMPTION.
Change the assumptions at the top and re-run:  python3 unit_economics.py
Writes data/unit_economics_wb.csv
"""
import csv
import itertools
from pathlib import Path

OUT = Path(__file__).parent / "data" / "unit_economics_wb.csv"

# --- sourced ---------------------------------------------------------------
COMMISSION_FBO = 0.375  # "Комплекты украшений"/"Цепочки"/"Браслеты"/"Кольца", FBO,
                        # iseller.pro/komissii-wb/bizhuteriya, срез WB 01.08.2026
LOGISTICS_BASE = 32     # ₽, верх «лесенки» 23–32 ₽ для товара до 1 л (iseller.pro/calculator/logistics, тарифы 29.07.2026)

# --- assumptions (NOT market data) -----------------------------------------
WAREHOUSE_COEF = 1.25       # коэффициент склада; Москва ×1, регионы 1.15–2.8 (там же)
ACCEPTANCE = 10             # ₽/ед, усреднённая приёмка (пример iseller)
STORAGE = 3                 # ₽ на проданную единицу, допущение
ACQUIRING = 0.025           # 2.5 %: в источниках 0.4–5 %, точной ставки нет
TAX = 0.06                  # УСН «доходы» 6 %, без НДС — проверить свой режим на 2026
PRICES = [1500, 2500]       # цена продавца (до СПП)
BUYOUT = [0.85, 0.70]       # доля выкупа: данных по категории нет, сценарии
DRR = [0.10, 0.20]          # доля рекламных расходов: данных по нише нет, сценарии
LANDED_COST = [250, 400, 600]  # ₽ себестоимость сета с доставкой до склада, упаковкой — сценарии


def row(price, buyout, drr, cogs):
    fwd = LOGISTICS_BASE * WAREHOUSE_COEF + ACCEPTANCE
    back = LOGISTICS_BASE * WAREHOUSE_COEF
    logistics = fwd / buyout + back * (1 - buyout) / buyout  # на выкупленную единицу
    commission = price * COMMISSION_FBO
    acquiring = price * ACQUIRING
    ads = price * drr
    tax = price * TAX
    profit = price - commission - acquiring - logistics - STORAGE - ads - tax - cogs
    return {
        "price_rub": price, "buyout": buyout, "drr": drr, "landed_cost_rub": cogs,
        "commission_rub": round(commission), "acquiring_rub": round(acquiring),
        "logistics_per_sold_rub": round(logistics), "storage_rub": STORAGE,
        "ads_rub": round(ads), "tax_rub": round(tax),
        "profit_per_sold_rub": round(profit),
        "margin_pct_of_price": round(100 * profit / price, 1),
        "roi_on_cogs_pct": round(100 * profit / cogs),
    }


rows = [row(*c) for c in itertools.product(PRICES, BUYOUT, DRR, LANDED_COST)]
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r)
