"""
Phase 1 — Historical Diagnostic: the Margin Leakage & Trapped Capital
report. This is the "zero integration, flat-file only" deliverable the
blueprint scopes in section 7 — it runs entirely on the historic
extract and costs the gap on Edgars' own figures before any write-back
is built.
"""
import pandas as pd

from src import config

SLOW_COVER_WEEKS = 18     # weeks of cover beyond which stock is "slow"
DEAD_COVER_WEEKS = 28     # weeks of cover beyond which stock is "dead"
RECENT_WINDOW_WEEKS = 12  # trailing window used to estimate current velocity

SLOW_MARKDOWN_DEPTH = 0.20   # assumed eventual discount depth on slow stock
DEAD_MARKDOWN_DEPTH = 0.45   # assumed eventual discount depth on dead stock


def _latest_with_trailing_velocity(panel: pd.DataFrame) -> pd.DataFrame:
    max_week = panel["week_num"].max()
    recent = panel[panel["week_num"] > max_week - RECENT_WINDOW_WEEKS]
    trailing = (
        recent.groupby(["store_id", "category"], observed=True)["units_sold"]
        .mean()
        .rename("avg_weekly_velocity")
        .reset_index()
    )
    latest = panel[panel["week_num"] == max_week].copy()
    latest = latest.merge(trailing, on=["store_id", "category"], how="left")
    latest["avg_weekly_velocity"] = latest["avg_weekly_velocity"].fillna(0.0)
    return latest


def classify_inventory_health(panel: pd.DataFrame) -> pd.DataFrame:
    latest = _latest_with_trailing_velocity(panel)
    latest["weeks_of_cover"] = latest["stock_on_hand_units"] / latest["avg_weekly_velocity"].replace(0, pd.NA)
    latest["weeks_of_cover"] = latest["weeks_of_cover"].fillna(latest["stock_on_hand_units"].clip(lower=0) * 0 + 999)

    def classify(w):
        if w >= DEAD_COVER_WEEKS:
            return "dead"
        if w >= SLOW_COVER_WEEKS:
            return "slow"
        return "healthy"

    latest["health"] = latest["weeks_of_cover"].apply(classify)
    latest["stock_value_usd"] = latest["stock_on_hand_units"] * latest["unit_cost"]
    latest["markdown_depth_assumed"] = latest["health"].map(
        {"dead": DEAD_MARKDOWN_DEPTH, "slow": SLOW_MARKDOWN_DEPTH, "healthy": 0.0}
    )
    latest["margin_at_risk_usd"] = (
        latest["stock_on_hand_units"] * latest["unit_price"] * latest["markdown_depth_assumed"]
    )
    return latest


def trapped_capital_summary(classified: pd.DataFrame) -> dict:
    total_value = classified["stock_value_usd"].sum()
    trapped = classified[classified["health"].isin(["slow", "dead"])]
    trapped_value = trapped["stock_value_usd"].sum()
    dead_value = classified.loc[classified["health"] == "dead", "stock_value_usd"].sum()
    slow_value = classified.loc[classified["health"] == "slow", "stock_value_usd"].sum()

    annual_carrying_cost = trapped_value * config.COST_OF_CAPITAL_ANNUAL
    margin_at_risk = trapped["margin_at_risk_usd"].sum()

    return {
        "total_stock_value_usd": total_value,
        "trapped_capital_usd": trapped_value,
        "trapped_capital_pct": (trapped_value / total_value * 100) if total_value else 0.0,
        "dead_stock_usd": dead_value,
        "slow_stock_usd": slow_value,
        "annual_carrying_cost_usd": annual_carrying_cost,
        "margin_at_risk_usd": margin_at_risk,
    }


def carrying_cost_saved_by_clearing_earlier(trapped_value: float, months_earlier: float = 3.0) -> float:
    """$ saved by liberating `trapped_value` of capital `months_earlier`
    months sooner, at the prevailing cost of capital — the ~$87,500-per-$1m
    figure cited in Blueprint section 2, generalised to the actual number."""
    annual_rate = config.COST_OF_CAPITAL_ANNUAL
    return trapped_value * annual_rate * (months_earlier / 12.0)


def stockout_lost_sales(panel: pd.DataFrame) -> pd.DataFrame:
    """Where demand outstripped stock (censored sales) — the flip side of
    dead stock: winners starved of capital under today's flat allocation."""
    df = panel.copy()
    df["unfilled_units"] = (df["demand"] - df["units_sold"]).clip(lower=0)
    df["lost_revenue_usd"] = df["unfilled_units"] * df["unit_price"]
    df["lost_margin_usd"] = df["unfilled_units"] * (df["unit_price"] - df["unit_cost"])

    by_cat = (
        df.groupby(["profile", "category"], observed=True)[["unfilled_units", "lost_revenue_usd", "lost_margin_usd"]]
        .sum()
        .reset_index()
        .sort_values("lost_margin_usd", ascending=False)
    )
    return by_cat


def build_diagnostic_report(data: dict) -> dict:
    classified = classify_inventory_health(data["panel"])
    summary = trapped_capital_summary(classified)
    summary["carrying_cost_saved_3mo_earlier_usd"] = carrying_cost_saved_by_clearing_earlier(
        summary["trapped_capital_usd"]
    )
    lost_sales = stockout_lost_sales(data["panel"])
    summary["total_lost_margin_from_stockouts_usd"] = lost_sales["lost_margin_usd"].sum()

    by_category = (
        classified.groupby("category", observed=True)
        .agg(
            trapped_capital_usd=("stock_value_usd", lambda s: s[classified.loc[s.index, "health"].isin(["slow", "dead"])].sum()),
            margin_at_risk_usd=("margin_at_risk_usd", "sum"),
            n_slow=("health", lambda s: (s == "slow").sum()),
            n_dead=("health", lambda s: (s == "dead").sum()),
        )
        .reset_index()
        .sort_values("trapped_capital_usd", ascending=False)
    )

    return {
        "classified": classified,
        "summary": summary,
        "lost_sales_by_category": lost_sales,
        "trapped_capital_by_category": by_category,
    }
