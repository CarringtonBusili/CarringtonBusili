"""
Synthetic data generator for the merchandise planning & buying tool.

Simulates a small apparel retailer's product master plus a 2-year weekly
sell-through / inventory history per SKU, including seasonality, promo
lifts, markdowns, receipts and occasional stockouts, so that downstream
KPI math and the forecasting model have something realistic to chew on.

Deterministic (fixed seed) so the API returns stable demo data across
restarts, and so the forecast model's backtest numbers don't jitter.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

SEED = 42
WEEKS_OF_HISTORY = 104  # 2 years

CATEGORIES = {
    "Outerwear": {"peak_week": 48, "width": 10, "base_price": 180, "margin": 0.58},
    "Knitwear": {"peak_week": 44, "width": 12, "base_price": 65, "margin": 0.55},
    "Denim": {"peak_week": 36, "width": 20, "base_price": 90, "margin": 0.52},
    "Footwear": {"peak_week": 20, "width": 16, "base_price": 110, "margin": 0.50},
    "Activewear": {"peak_week": 22, "width": 14, "base_price": 55, "margin": 0.48},
    "Accessories": {"peak_week": 50, "width": 6, "base_price": 35, "margin": 0.62},
}

PRODUCT_NAMES = {
    "Outerwear": ["Sherpa Parka", "Quilted Bomber", "Wool Peacoat", "Rain Shell"],
    "Knitwear": ["Cable Sweater", "Merino Crew", "Chunky Cardigan"],
    "Denim": ["Slim Fit Jean", "Relaxed Jean", "Denim Jacket"],
    "Footwear": ["Trail Runner", "Canvas Sneaker", "Leather Boot"],
    "Activewear": ["Performance Tee", "Compression Legging", "Training Short"],
    "Accessories": ["Wool Beanie", "Leather Belt", "Crossbody Bag"],
}


def _seasonal_curve(week_of_year: np.ndarray, peak_week: int, width: int) -> np.ndarray:
    """Wrapped-gaussian seasonal demand multiplier peaking at `peak_week`."""
    dist = np.minimum(
        np.abs(week_of_year - peak_week),
        52 - np.abs(week_of_year - peak_week),
    )
    return 0.55 + 1.6 * np.exp(-(dist ** 2) / (2 * width ** 2))


def _build_products() -> pd.DataFrame:
    rows = []
    pid = 1
    for category, meta in CATEGORIES.items():
        for name in PRODUCT_NAMES[category]:
            price = round(meta["base_price"] * np.random.uniform(0.85, 1.2), 2)
            cost = round(price * (1 - meta["margin"]) * np.random.uniform(0.95, 1.05), 2)
            rows.append(
                {
                    "product_id": f"SKU-{pid:04d}",
                    "name": name,
                    "category": category,
                    "retail_price": price,
                    "unit_cost": cost,
                    "lead_time_weeks": int(np.random.choice([4, 6, 8])),
                    "target_wos": round(np.random.uniform(6, 10), 1),
                    "reorder_cycle_weeks": int(np.random.choice([4, 6, 8])),
                }
            )
            pid += 1
    return pd.DataFrame(rows)


def _simulate_history(products: pd.DataFrame, start_week_offset: int = 0) -> pd.DataFrame:
    all_rows = []
    today_week_index = WEEKS_OF_HISTORY - 1

    for _, prod in products.iterrows():
        meta = CATEGORIES[prod["category"]]
        # np's built-in hash() is randomized per-process (PYTHONHASHSEED),
        # which would make the "fixed seed" reproducibility claim false;
        # hashlib gives a stable digest across runs/restarts.
        digest = hashlib.sha256(prod["product_id"].encode()).hexdigest()
        rng = np.random.default_rng(int(digest, 16) % (2 ** 32))

        base_units = rng.uniform(18, 55)
        trend = rng.uniform(-0.0015, 0.003)  # slow secular growth/decline per week

        week_idx = np.arange(WEEKS_OF_HISTORY)
        week_of_year = (week_idx % 52) + 1
        seasonal = _seasonal_curve(week_of_year, meta["peak_week"], meta["width"])
        trend_mult = (1 + trend) ** week_idx

        promo_flag = (rng.random(WEEKS_OF_HISTORY) < 0.08).astype(float)
        promo_lift = 1 + promo_flag * rng.uniform(0.35, 0.9, WEEKS_OF_HISTORY)

        noise = rng.normal(1.0, 0.14, WEEKS_OF_HISTORY).clip(0.55, 1.6)

        demand = np.maximum(0, base_units * seasonal * trend_mult * promo_lift * noise)
        demand = np.round(demand).astype(int)

        plan = np.round(base_units * seasonal * trend_mult * rng.normal(1.0, 0.05, WEEKS_OF_HISTORY)).astype(int)
        plan = np.maximum(plan, 1)

        markdown_flag = np.zeros(WEEKS_OF_HISTORY)
        clearance_start = int(rng.integers(WEEKS_OF_HISTORY - 10, WEEKS_OF_HISTORY - 2))
        markdown_flag[clearance_start:] = 1
        markdown_pct = markdown_flag * rng.uniform(0.2, 0.4)

        # --- inventory simulation with periodic receipts ---
        inventory = base_units * prod["target_wos"] * rng.uniform(0.9, 1.3)
        on_order_units = 0
        cycle = int(prod["reorder_cycle_weeks"])
        lead_time = int(prod["lead_time_weeks"])
        pending_receipts: dict[int, float] = {}

        for w in range(WEEKS_OF_HISTORY):
            receipt_today = pending_receipts.pop(w, 0)
            inventory += receipt_today

            beginning_inventory = inventory
            sellable_demand = demand[w]
            units_sold = min(sellable_demand, inventory)
            stockout = 1 if sellable_demand > inventory else 0
            inventory -= units_sold

            # place a reorder every `cycle` weeks, sized to cover the next cycle+lead_time at recent run-rate
            if w % cycle == 0 and w > 0:
                lookback = demand[max(0, w - 8): w].mean() if w >= 8 else base_units
                target_units = lookback * (cycle + lead_time) / 7 * 7  # weeks * weekly rate
                order_qty = max(0, target_units - inventory)
                arrival_week = w + lead_time
                if arrival_week < WEEKS_OF_HISTORY:
                    pending_receipts[arrival_week] = pending_receipts.get(arrival_week, 0) + order_qty

            unit_price = prod["retail_price"] * (1 - markdown_pct[w])
            revenue = units_sold * unit_price
            cogs = units_sold * prod["unit_cost"]

            all_rows.append(
                {
                    "product_id": prod["product_id"],
                    "category": prod["category"],
                    "week_index": w,
                    "weeks_ago": today_week_index - w,
                    "week_of_year": int(week_of_year[w]),
                    "units_sold": int(units_sold),
                    "units_demanded": int(sellable_demand),
                    "stockout": stockout,
                    "planned_units": int(plan[w]),
                    "beginning_inventory": round(beginning_inventory, 1),
                    "ending_inventory": round(inventory, 1),
                    "receipts": round(receipt_today, 1),
                    "unit_price": round(unit_price, 2),
                    "revenue": round(revenue, 2),
                    "cogs": round(cogs, 2),
                    "gross_margin": round(revenue - cogs, 2),
                    "promo_flag": int(promo_flag[w]),
                    "markdown_flag": int(markdown_flag[w]),
                }
            )

    return pd.DataFrame(all_rows)


def generate_dataset(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    np.random.seed(seed)
    products = _build_products()
    history = _simulate_history(products)
    return products, history


if __name__ == "__main__":
    products_df, history_df = generate_dataset()
    products_df.to_csv("data/products.csv", index=False)
    history_df.to_csv("data/history.csv", index=False)
    print(f"Generated {len(products_df)} products, {len(history_df)} history rows")
