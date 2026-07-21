"""
Turns a real Phase 1 flat-file extract (Blueprint section 11: "sales by
SKU, store and date... current stock on hand and stock-age; historical
OTB and sales budgets; and... the till currency-mix ratios") into the
exact same internal shape `data_gen.generate_all()` produces, so every
downstream engine (forecast, diagnostic, OTB, markdown, assortment)
runs unchanged on real data instead of the synthetic demo.

Only a handful of fields are strictly required — the rest of the
blueprint's requested extract (stock-age, OTB budgets) either isn't
needed by the engines as implemented, or is optional enrichment.
"""
import io

import numpy as np
import pandas as pd

from src import config, data_gen

REQUIRED_FIELDS = ["date", "store_id", "category", "units_sold", "unit_cost", "unit_price", "stock_on_hand"]
OPTIONAL_FIELDS = ["usd_till_share", "store_profile", "otb_budget_usd"]

ALIASES = {
    "date": ["date", "week", "week_start", "transaction_date", "sale_date", "period"],
    "store_id": ["store_id", "store", "branch", "branch_id", "store_code", "storeid"],
    "category": ["category", "dept", "department", "product_category", "category_name"],
    "units_sold": ["units_sold", "units", "qty_sold", "quantity_sold", "sales_units", "unitssold"],
    "unit_cost": ["unit_cost", "cost", "cost_price", "unitcost"],
    "unit_price": ["unit_price", "price", "retail_price", "selling_price", "unitprice"],
    "stock_on_hand": ["stock_on_hand", "stock", "soh", "closing_stock", "stock_on_hand_units", "stockonhand"],
    "usd_till_share": ["usd_till_share", "usd_share", "till_currency_mix", "usd_pct", "usd_ratio", "usdtillshare"],
    "store_profile": ["store_profile", "profile", "segment", "store_segment", "region"],
    "otb_budget_usd": ["otb_budget_usd", "otb_budget", "budget_usd", "budget"],
}


class IngestError(Exception):
    """Raised on a validation failure, with a user-facing message."""


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_columns(raw_columns) -> dict:
    normalised = {_normalise(c): c for c in raw_columns}
    resolved = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                resolved[canonical] = normalised[alias]
                break
    return resolved


def parse_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if file_name.lower().endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(file_bytes))
    try:
        return pd.read_csv(io.BytesIO(file_bytes))
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")


def validate_and_map(raw_df: pd.DataFrame) -> pd.DataFrame:
    resolved = _resolve_columns(raw_df.columns)
    missing = [f for f in REQUIRED_FIELDS if f not in resolved]
    if missing:
        raise IngestError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(raw_df.columns.astype(str))}. "
            "Download the template below for the exact expected format."
        )

    present = {**{f: resolved[f] for f in REQUIRED_FIELDS}, **{f: resolved[f] for f in OPTIONAL_FIELDS if f in resolved}}
    df = raw_df.rename(columns={v: k for k, v in present.items()})[list(present.keys())].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["units_sold", "unit_cost", "unit_price", "stock_on_hand"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "usd_till_share" in df.columns:
        df["usd_till_share"] = pd.to_numeric(df["usd_till_share"], errors="coerce")
        if df["usd_till_share"].max(skipna=True) is not None and df["usd_till_share"].max(skipna=True) > 1.5:
            df["usd_till_share"] = df["usd_till_share"] / 100.0

    before = len(df)
    df = df.dropna(subset=["date", "store_id", "category", "units_sold", "unit_cost", "unit_price", "stock_on_hand"])
    dropped = before - len(df)
    if df.empty:
        raise IngestError(
            "No usable rows after parsing — check that date, store_id, category, units_sold, "
            "unit_cost, unit_price and stock_on_hand all contain valid values."
        )
    df.attrs["rows_dropped"] = dropped
    df.attrs["rows_used"] = len(df)
    return df


def _week_start(dates: pd.Series) -> pd.Series:
    return (dates - pd.to_timedelta(dates.dt.dayofweek, unit="D")).dt.normalize()


def build_dataset_from_upload(file_bytes: bytes, file_name: str) -> dict:
    raw_df = parse_file(file_bytes, file_name)
    df = validate_and_map(raw_df)
    rows_used, rows_dropped = df.attrs.get("rows_used"), df.attrs.get("rows_dropped", 0)
    df["week_start"] = _week_start(df["date"])
    df["store_id"] = df["store_id"].astype(str)
    df["category"] = df["category"].astype(str)

    has_till = "usd_till_share" in df.columns
    has_profile = "store_profile" in df.columns

    # Till currency-mix is a store-level (point-of-sale) signal, not
    # category-specific — average it per store-week, then broadcast.
    if has_till:
        store_week_till = df.groupby(["store_id", "week_start"])["usd_till_share"].mean().rename("_store_week_till")
        df = df.join(store_week_till, on=["store_id", "week_start"])
        df["usd_till_share"] = df["_store_week_till"]
        df = df.drop(columns=["_store_week_till"])
    else:
        df["usd_till_share"] = 0.5

    agg = {
        "units_sold": "sum",
        "unit_cost": "mean",
        "unit_price": "mean",
        "stock_on_hand": "last",
        "usd_till_share": "mean",
    }
    panel = (
        df.sort_values("date")
        .groupby(["store_id", "category", "week_start"], as_index=False)
        .agg(agg)
    )
    if has_profile:
        profile_map = df.groupby("store_id")["store_profile"].agg(lambda s: s.mode().iat[0] if not s.mode().empty else "unclassified")
        panel["profile"] = panel["store_id"].map(profile_map)
    else:
        panel["profile"] = "unclassified"

    weeks = sorted(panel["week_start"].unique())
    week_num_map = {w: i for i, w in enumerate(weeks)}
    panel["week_num"] = panel["week_start"].map(week_num_map)

    panel["revenue_usd"] = panel["units_sold"] * panel["unit_price"]
    panel["stock_on_hand_units"] = panel["stock_on_hand"]
    panel["demand"] = panel["units_sold"]  # no unconstrained-demand signal available from sales alone
    panel["stock_age_weeks"] = 0  # not required by any engine; weeks-of-cover is derived fresh from velocity
    panel["affinity"] = 1.0       # synthetic-only bookkeeping field, unused downstream
    panel = panel.drop(columns=["stock_on_hand"])

    calendar = data_gen.calendar_from_weeks(pd.DatetimeIndex(weeks))

    stores = _build_stores(panel)
    categories = _build_categories(panel)
    till_mix = panel[["store_id", "week_start", "usd_till_share"]].drop_duplicates(subset=["store_id", "week_start"])
    macro = _build_macro(calendar, till_mix)

    meta = {
        "source": "upload", "file_name": file_name,
        "rows_used": rows_used, "rows_dropped": rows_dropped,
        "has_till_data": has_till, "has_profile_data": has_profile,
        "n_weeks": len(weeks), "n_stores": panel["store_id"].nunique(), "n_categories": panel["category"].nunique(),
    }

    return {
        "stores": stores, "categories": categories, "calendar": calendar,
        "macro": macro, "till_mix": till_mix, "panel": panel, "meta": meta,
    }


def _build_stores(panel: pd.DataFrame) -> pd.DataFrame:
    weekly_units = panel.groupby(["store_id", "week_start"], observed=True)["units_sold"].sum().reset_index()
    vol = weekly_units.groupby("store_id")["units_sold"].agg(lambda s: s.std() / s.mean() if s.mean() else 0.0)
    till = panel.groupby("store_id")["usd_till_share"].mean()
    profile = panel.groupby("store_id")["profile"].first()

    stores = pd.DataFrame({
        "store_id": profile.index,
        "store_name": profile.index,
        "profile": profile.values,
        "usd_till_share_base": till.reindex(profile.index).fillna(0.5).values,
        "price_sensitivity": 1.0,
        "volatility": vol.reindex(profile.index).fillna(0.15).clip(0.02, 0.6).values,
    }).reset_index(drop=True)
    return stores


def _build_categories(panel: pd.DataFrame) -> pd.DataFrame:
    n_weeks = panel["week_num"].nunique() or 1
    n_stores = panel["store_id"].nunique() or 1
    grouped = panel.groupby("category", observed=True).agg(
        unit_cost=("unit_cost", "mean"),
        unit_price=("unit_price", "mean"),
        total_units=("units_sold", "sum"),
    ).reset_index()
    grouped["base_weekly_units_per_store"] = (grouped["total_units"] / n_weeks / n_stores).clip(lower=0.5)
    grouped["moq"] = (grouped["base_weekly_units_per_store"] * config.IMPORT_LEAD_TIME_WEEKS).round(-1).clip(lower=50).astype(int)
    grouped["pack_size"] = 12
    return grouped[["category", "unit_cost", "unit_price", "moq", "pack_size", "base_weekly_units_per_store"]]


def _build_macro(calendar: pd.DataFrame, till_mix: pd.DataFrame) -> pd.DataFrame:
    weekly_till = till_mix.groupby("week_start")["usd_till_share"].mean().reindex(calendar["week_start"])
    weekly_till = weekly_till.ffill().bfill().fillna(0.5)

    pressure_raw = 1 - weekly_till
    span = pressure_raw.max() - pressure_raw.min()
    pressure = (pressure_raw - pressure_raw.min()) / span if span > 1e-9 else pressure_raw * 0 + 0.5

    spend_velocity = (-pressure.diff().fillna(0)).clip(-0.5, 0.5)
    jump_week = pressure.diff().abs() > (pressure.diff().abs().std() * 1.5 if pressure.diff().std() > 0 else 1.0)

    macro = calendar.copy()
    macro["parallel_rate_premium"] = pressure.values  # best-effort internal proxy — see meta['has_till_data']
    macro["liquidity_pressure_index"] = pressure.values
    macro["spend_velocity_index"] = spend_velocity.values
    macro["jump_week"] = jump_week.fillna(False).values
    return macro
