"""
The Zimbabwe Macro Signal Layer.

This module assembles the per-store, per-week feature table described in
Blueprint section 6: till currency-mix (internal, real-time), spend
velocity (internal, derived), the parallel-rate/wholesale premium
(constructed proxy), and the school-term / tobacco-season calendars
(public, directly Edgars-relevant). Nothing here is presented as a live
feed where the blueprint says it should be a labelled proxy.
"""
import pandas as pd


SIGNAL_CATALOGUE = pd.DataFrame([
    {"signal": "Till currency-mix (ZiG : USD share)", "tells_us": "Real-time liquidity stress at the point of sale",
     "source_class": "Internal: Edgars has this"},
    {"signal": "Spend-velocity (rate ZiG converts to goods)", "tells_us": "Inflation expectation; buy-now surges vs holding",
     "source_class": "Internal (from till data)"},
    {"signal": "Parallel-rate & wholesale premium", "tells_us": "Real confidence and the gap that shifts formal-retail demand",
     "source_class": "Constructed proxy (USDT-P2P & FMCG indices)"},
    {"signal": "School-term & fees cycles", "tells_us": "Uniform and apparel surges; disposable-income drains",
     "source_class": "Public calendar: directly Edgars-relevant"},
    {"signal": "Tobacco selling season (Feb-Jul)", "tells_us": "USD injection into farming regions, lifting regional demand",
     "source_class": "Public calendar"},
])


def build_feature_table(data: dict) -> pd.DataFrame:
    """Join macro calendar/FX signals onto the per-store till-mix series to
    produce one row per store-week: the feature table the forecast engine
    (and any planner wanting to see 'why this number') actually reads."""
    macro = data["macro"]
    till_mix = data["till_mix"]

    feat = till_mix.merge(
        macro[["week_start", "week_num", "parallel_rate_premium",
               "liquidity_pressure_index", "spend_velocity_index",
               "school_term_window", "tobacco_season", "jump_week"]],
        on="week_start", how="left",
    )
    return feat


def store_profile_liquidity_summary(data: dict) -> pd.DataFrame:
    """Average USD till-share and volatility by store profile — the view
    that shows why a single global forecast can't work across 27 stores."""
    till_mix = data["till_mix"].merge(data["stores"][["store_id", "profile"]], on="store_id")
    summary = (
        till_mix.groupby("profile")["usd_till_share"]
        .agg(["mean", "std", "min", "max"])
        .rename(columns={"mean": "avg_usd_share", "std": "volatility",
                          "min": "worst_week", "max": "best_week"})
        .reset_index()
        .sort_values("avg_usd_share", ascending=False)
    )
    return summary


def demand_sensitivity_to_pressure(data: dict) -> pd.DataFrame:
    """Correlation between the liquidity pressure index and category-level
    sell-through, by store profile — quantifies 'blind to the parallel-rate
    gap' from Figure 3 instead of just asserting it."""
    panel = data["panel"]
    macro = data["macro"][["week_num", "liquidity_pressure_index"]]
    merged = panel.merge(macro, on="week_num", how="left")

    out = (
        merged.groupby(["profile", "category"])
        .apply(lambda g: g["units_sold"].corr(g["liquidity_pressure_index"]))
        .rename("corr_with_liquidity_pressure")
        .reset_index()
    )
    return out
