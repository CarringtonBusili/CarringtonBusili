"""
Merchandise financial planning KPI calculations.

Formulas follow standard retail math (MFP/OTB terminology):

- Sell-Through %      = units sold / units available (beginning inv + receipts)
- Gross Margin %      = gross margin $ / revenue $
- GMROI               = gross margin $ (annualized) / average inventory at cost
- Inventory Turnover  = COGS (annualized) / average inventory at cost
- Weeks of Supply     = ending inventory units / trailing avg weekly unit sales
- Markdown %          = (full-price revenue potential - actual revenue) / full-price revenue potential
- Sales Plan Variance = (actual units - planned units) / planned units
- Stockout Rate       = weeks with demand > available inventory / total weeks
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WEEKS_PER_YEAR = 52


def _period_slice(history: pd.DataFrame, period_weeks: int) -> pd.DataFrame:
    return history[history["weeks_ago"] < period_weeks]


def _with_cost(history: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    return history.merge(products[["product_id", "unit_cost", "retail_price"]], on="product_id", how="left")


def summary_kpis(history: pd.DataFrame, products: pd.DataFrame, period_weeks: int = 13) -> dict:
    df = _with_cost(_period_slice(history, period_weeks), products)
    annualize = WEEKS_PER_YEAR / period_weeks

    revenue = df["revenue"].sum()
    cogs = df["cogs"].sum()
    gross_margin = df["gross_margin"].sum()
    units_sold = df["units_sold"].sum()
    planned_units = df["planned_units"].sum()
    receipts = df["receipts"].sum()
    beginning_inv_units = df.groupby("product_id")["beginning_inventory"].first().sum()

    avg_inventory_cost = (df["ending_inventory"] * df["unit_cost"]).groupby(df["product_id"]).mean().sum()
    full_price_potential = (df["units_sold"] * df["retail_price"]).sum()

    sell_through = units_sold / (beginning_inv_units + receipts) if (beginning_inv_units + receipts) > 0 else 0
    gmroi = (gross_margin * annualize) / avg_inventory_cost if avg_inventory_cost else 0
    turnover = (cogs * annualize) / avg_inventory_cost if avg_inventory_cost else 0
    markdown_pct = (full_price_potential - revenue) / full_price_potential if full_price_potential else 0
    plan_variance = (units_sold - planned_units) / planned_units if planned_units else 0

    trailing4 = history[history["weeks_ago"] < 4]
    avg_weekly_units = trailing4.groupby("product_id")["units_sold"].mean().sum()
    ending_inv_units = history[history["weeks_ago"] == 0].groupby("product_id")["ending_inventory"].sum().sum()
    weeks_of_supply = ending_inv_units / avg_weekly_units if avg_weekly_units else 0

    total_weeks_rows = len(df)
    stockout_rate = df["stockout"].sum() / total_weeks_rows if total_weeks_rows else 0

    return {
        "period_weeks": period_weeks,
        "revenue": round(revenue, 2),
        "gross_margin": round(gross_margin, 2),
        "gross_margin_pct": round(gross_margin / revenue, 4) if revenue else 0,
        "units_sold": int(units_sold),
        "sell_through_pct": round(sell_through, 4),
        "gmroi": round(gmroi, 2),
        "inventory_turnover": round(turnover, 2),
        "weeks_of_supply": round(weeks_of_supply, 1),
        "markdown_pct": round(markdown_pct, 4),
        "sales_plan_variance_pct": round(plan_variance, 4),
        "stockout_rate_pct": round(stockout_rate, 4),
        "ending_inventory_units": int(ending_inv_units),
        "ending_inventory_cost_value": round((history[history["weeks_ago"] == 0]
                                               .merge(products[["product_id", "unit_cost"]], on="product_id")
                                               .assign(v=lambda d: d["ending_inventory"] * d["unit_cost"])["v"]
                                               .sum()), 2),
    }


def category_breakdown(history: pd.DataFrame, products: pd.DataFrame, period_weeks: int = 13) -> list[dict]:
    out = []
    for category in sorted(products["category"].unique()):
        prod_ids = products[products["category"] == category]["product_id"]
        sub_hist = history[history["product_id"].isin(prod_ids)]
        k = summary_kpis(sub_hist, products, period_weeks)
        k["category"] = category
        out.append(k)
    return sorted(out, key=lambda x: x["revenue"], reverse=True)


def trend_series(history: pd.DataFrame, weeks: int = 26, category: str | None = None,
                  products: pd.DataFrame | None = None) -> list[dict]:
    df = history[history["weeks_ago"] < weeks]
    if category and products is not None:
        prod_ids = products[products["category"] == category]["product_id"]
        df = df[df["product_id"].isin(prod_ids)]

    grouped = df.groupby("week_index").agg(
        revenue=("revenue", "sum"),
        planned_units=("planned_units", "sum"),
        units_sold=("units_sold", "sum"),
        gross_margin=("gross_margin", "sum"),
        ending_inventory=("ending_inventory", "sum"),
        stockouts=("stockout", "sum"),
        week_of_year=("week_of_year", "first"),
    ).reset_index().sort_values("week_index")

    grouped["gross_margin_pct"] = (grouped["gross_margin"] / grouped["revenue"]).replace([np.inf, -np.inf], 0).fillna(0)
    return grouped.round(2).to_dict(orient="records")


def product_kpis(history: pd.DataFrame, products: pd.DataFrame, product_id: str, period_weeks: int = 13) -> dict:
    sub = history[history["product_id"] == product_id]
    return summary_kpis(sub, products[products["product_id"] == product_id], period_weeks)
