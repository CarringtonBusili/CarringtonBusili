"""
Synthetic data generator standing in for Edgars' real D365 LS Central
extract (sales, stock, OTB budgets, till currency-mix).

No real Edgars data exists for this demo, so we simulate 27 stores across
five local-economy profiles, 8 apparel categories, and 104 weeks of
history, deliberately baking in the two failure modes the blueprint
describes under the *current* (capital-agnostic, macro-blind) buying
process:

  1. Flat, affinity-blind allocation -> dead/slow stock in low-affinity
     store-category pairs, and stock-outs in high-affinity ones.
  2. A macro-blind demand baseline -> sales look noisy/random unless you
     condition on the Zimbabwe Macro Signal Layer (till currency-mix,
     parallel-rate pressure, school terms, tobacco season).

Everything is derived from a fixed RANDOM_SEED so the app is reproducible
run to run, and cached by Streamlit so all pages see the same "history".
"""
import numpy as np
import pandas as pd

from src import config


def _rng():
    return np.random.default_rng(config.RANDOM_SEED)


# Branches whose static profile label has gone stale: their *actual*
# economics now resemble a different profile, exactly the drift JAM's
# static rules can't track (Blueprint 5.3). The label is left unchanged;
# only the underlying behaviour is swapped, so the dynamic clustering
# engine has something real to catch.
DRIFTED_STORES = {
    "S10": "border_town",           # civil_servant_suburb store now behaving like a border/informal-trade hub
    "S21": "civil_servant_suburb",  # urban_mall store now behaving like a cash-strapped suburb
}


def build_stores() -> pd.DataFrame:
    rows = []
    sid = 1
    for profile, spec in config.STORE_PROFILES.items():
        for i in range(spec["n_stores"]):
            rows.append({
                "store_id": f"S{sid:02d}",
                "store_name": f"{profile.replace('_', ' ').title()} #{i + 1}",
                "profile": profile,
                "usd_till_share_base": spec["usd_till_share_base"],
                "price_sensitivity": spec["price_sensitivity"],
                "volatility": spec["volatility"],
            })
            sid += 1

    df = pd.DataFrame(rows)
    for store_id, actual_profile in DRIFTED_STORES.items():
        actual_spec = config.STORE_PROFILES[actual_profile]
        mask = df["store_id"] == store_id
        df.loc[mask, "usd_till_share_base"] = actual_spec["usd_till_share_base"]
        df.loc[mask, "price_sensitivity"] = actual_spec["price_sensitivity"]
        df.loc[mask, "volatility"] = actual_spec["volatility"]
    return df


def build_categories() -> pd.DataFrame:
    rows = []
    for cat, spec in config.CATEGORIES.items():
        row = {"category": cat}
        row.update(spec)
        rows.append(row)
    return pd.DataFrame(rows)


# Affinity: how well a category actually sells in a given store profile,
# relative to the flat "1.0" assumption the current capital-agnostic
# buying process implicitly makes. <1 => over-bought/slow, >1 => under-bought/stock-outs.
AFFINITY = {
    ("mining_town", "Menswear"): 1.3, ("mining_town", "Womenswear"): 0.8,
    ("mining_town", "Kidswear"): 0.9, ("mining_town", "Footwear"): 1.4,
    ("mining_town", "School Uniforms"): 0.9, ("mining_town", "Sportswear"): 1.3,
    ("mining_town", "Home & Textiles"): 0.8, ("mining_town", "Accessories"): 1.0,

    ("civil_servant_suburb", "Menswear"): 0.8, ("civil_servant_suburb", "Womenswear"): 0.9,
    ("civil_servant_suburb", "Kidswear"): 1.3, ("civil_servant_suburb", "Footwear"): 0.7,
    ("civil_servant_suburb", "School Uniforms"): 1.5, ("civil_servant_suburb", "Sportswear"): 0.6,
    ("civil_servant_suburb", "Home & Textiles"): 1.1, ("civil_servant_suburb", "Accessories"): 0.9,

    ("border_town", "Menswear"): 1.2, ("border_town", "Womenswear"): 1.3,
    ("border_town", "Kidswear"): 1.0, ("border_town", "Footwear"): 1.3,
    ("border_town", "School Uniforms"): 0.8, ("border_town", "Sportswear"): 1.1,
    ("border_town", "Home & Textiles"): 0.9, ("border_town", "Accessories"): 1.4,

    ("urban_mall", "Menswear"): 1.1, ("urban_mall", "Womenswear"): 1.3,
    ("urban_mall", "Kidswear"): 1.0, ("urban_mall", "Footwear"): 1.2,
    ("urban_mall", "School Uniforms"): 0.9, ("urban_mall", "Sportswear"): 1.2,
    ("urban_mall", "Home & Textiles"): 1.0, ("urban_mall", "Accessories"): 1.2,

    ("rural_growth_point", "Menswear"): 0.9, ("rural_growth_point", "Womenswear"): 0.7,
    ("rural_growth_point", "Kidswear"): 1.1, ("rural_growth_point", "Footwear"): 0.6,
    ("rural_growth_point", "School Uniforms"): 1.3, ("rural_growth_point", "Sportswear"): 0.5,
    ("rural_growth_point", "Home & Textiles"): 1.2, ("rural_growth_point", "Accessories"): 0.8,
}


def _is_school_term_window(d) -> bool:
    for mmdd in config.SCHOOL_TERM_STARTS_MMDD:
        month, day = (int(x) for x in mmdd.split("-"))
        term_start = pd.Timestamp(year=d.year, month=month, day=day)
        if -14 <= (d - term_start).days <= 7:
            return True
    return False


def calendar_from_weeks(weeks: pd.DatetimeIndex) -> pd.DataFrame:
    """Build the school-term / tobacco-season calendar for an arbitrary
    sequence of week-start dates — shared by the synthetic generator and
    the real-data ingest path, since both are Zimbabwe-specific facts
    about the calendar, not about the data source."""
    df = pd.DataFrame({"week_start": weeks, "week_num": range(len(weeks))})
    df["school_term_window"] = df["week_start"].apply(_is_school_term_window)
    df["tobacco_season"] = df["week_start"].dt.month.isin(config.TOBACCO_SEASON_MONTHS)
    return df


def build_calendar() -> pd.DataFrame:
    weeks = pd.date_range(config.HISTORY_START, periods=config.N_WEEKS, freq="W-MON")
    return calendar_from_weeks(weeks)


def build_macro_series(calendar: pd.DataFrame) -> pd.DataFrame:
    """The constructed macro proxies: parallel-rate premium, the liquidity
    pressure index derived from it, and a spend-velocity ("buy-now surge")
    index that spikes right after a pressure jump then dips below baseline."""
    rng = _rng()
    n = len(calendar)

    premium = np.zeros(n)
    premium[0] = 0.15
    jump_weeks = set(rng.choice(n, size=max(3, n // 18), replace=False))
    for t in range(1, n):
        drift = rng.normal(0.002, 0.01)
        jump = rng.uniform(0.08, 0.22) if t in jump_weeks else 0.0
        premium[t] = max(0.0, premium[t - 1] + drift + jump - 0.01 * premium[t - 1])

    pressure = premium / (premium.max() + 1e-9)

    spend_velocity = np.zeros(n)
    for t in range(n):
        recent_jump = any((t - jw) in (0, 1, 2) for jw in jump_weeks if t >= jw)
        if recent_jump:
            spend_velocity[t] = rng.uniform(0.25, 0.45)
        elif any((t - jw) in (3, 4, 5) for jw in jump_weeks if t >= jw):
            spend_velocity[t] = -rng.uniform(0.1, 0.25)
        else:
            spend_velocity[t] = rng.normal(0, 0.03)

    out = calendar.copy()
    out["parallel_rate_premium"] = premium
    out["liquidity_pressure_index"] = pressure
    out["spend_velocity_index"] = spend_velocity
    out["jump_week"] = out["week_num"].isin(jump_weeks)
    return out


def build_till_currency_mix(stores: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """Weekly USD-share of till currency-mix per store, the one signal the
    blueprint flags as real-time and already owned by Edgars."""
    rng = _rng()
    rows = []
    for _, s in stores.iterrows():
        sensitivity = 1.6 if s["profile"] == "civil_servant_suburb" else \
                      0.9 if s["profile"] == "rural_growth_point" else 0.4
        noise = rng.normal(0, 0.02, size=len(macro))
        usd_share = s["usd_till_share_base"] - sensitivity * 0.25 * macro["liquidity_pressure_index"].values + noise
        usd_share = np.clip(usd_share, 0.05, 0.97)
        for wk, val in zip(macro["week_start"], usd_share):
            rows.append({"store_id": s["store_id"], "week_start": wk, "usd_till_share": val})
    return pd.DataFrame(rows)


def build_sales_and_stock(stores, categories, calendar, macro, till_mix) -> pd.DataFrame:
    """The core panel: store x category x week sales, stock-on-hand,
    stock-age, and the receipt schedule the *current* flat/naive buying
    process would generate (used as the 'as-is' baseline the diagnostic
    and OTB engines measure against)."""
    rng = _rng()
    macro_idx = macro.set_index("week_num")
    till_idx = till_mix.set_index(["store_id", "week_start"])["usd_till_share"]

    records = []
    for _, cat in categories.iterrows():
        cat_name = cat["category"]
        receipt_cycle = config.IMPORT_LEAD_TIME_WEEKS
        # Flat per-store receipt size: current process splits the group buy
        # evenly across all 27 stores, sized off the category-average
        # historic rate, blind to local affinity.
        flat_receipt_units = int(cat["base_weekly_units_per_store"] * receipt_cycle * 0.95)

        for _, s in stores.iterrows():
            # Demand behaves per the store's *actual* current profile, even
            # for the handful of drifted stores still labelled/ranged under
            # their old (JAM-assumed) profile.
            actual_profile = DRIFTED_STORES.get(s["store_id"], s["profile"])
            affinity = AFFINITY.get((actual_profile, cat_name), 1.0)
            stock_on_hand = flat_receipt_units  # opening stock
            weeks_since_receipt = 0

            for _, wk in calendar.iterrows():
                w = wk["week_num"]
                m = macro_idx.loc[w]
                usd_share = till_idx.get((s["store_id"], wk["week_start"]), s["usd_till_share_base"])

                # Receipt arrives every `receipt_cycle` weeks, flat quantity,
                # unless the OTB tracker's basic reorder point already shows
                # well over a cycle of cover on hand (LS Central does track
                # budgets — it just isn't locally/capitally optimised).
                due = w % receipt_cycle == 0 and w > 0
                overstocked = stock_on_hand > flat_receipt_units * 1.4
                arrival = flat_receipt_units if (due and not overstocked) else 0
                if arrival:
                    weeks_since_receipt = 0
                stock_on_hand += arrival

                # Demand: base rate x affinity x seasonal x macro x noise.
                seasonal = 1.0
                if cat_name in ("Kidswear", "School Uniforms") and wk["school_term_window"]:
                    seasonal *= 1.45
                if actual_profile in ("mining_town", "rural_growth_point") and wk["tobacco_season"]:
                    seasonal *= 1.18

                # Liquidity stress dampens discretionary spend more in
                # ZiG-heavy, price-sensitive stores; the spend-velocity
                # index adds a temporary buy-now surge or post-surge lull.
                macro_effect = (1 - 0.18 * m["liquidity_pressure_index"] * s["price_sensitivity"] / 1.3)
                macro_effect *= (1 + m["spend_velocity_index"])
                macro_effect = max(0.15, macro_effect)

                noise = rng.normal(1.0, s["volatility"])
                demand = max(0.0, cat["base_weekly_units_per_store"] * affinity * seasonal * macro_effect * noise)

                units_sold = min(demand, stock_on_hand)
                stock_on_hand -= units_sold
                weeks_since_receipt += 1

                records.append({
                    "week_start": wk["week_start"], "week_num": w,
                    "store_id": s["store_id"], "profile": s["profile"],
                    "category": cat_name, "usd_till_share": usd_share,
                    "units_sold": units_sold, "demand": demand,
                    "unit_cost": cat["unit_cost"], "unit_price": cat["unit_price"],
                    "revenue_usd": units_sold * cat["unit_price"],
                    "stock_on_hand_units": stock_on_hand,
                    "stock_age_weeks": weeks_since_receipt,
                    "affinity": affinity,
                })

    return pd.DataFrame(records)


def generate_all():
    stores = build_stores()
    categories = build_categories()
    calendar = build_calendar()
    macro = build_macro_series(calendar)
    till_mix = build_till_currency_mix(stores, macro)
    panel = build_sales_and_stock(stores, categories, calendar, macro, till_mix)
    return {
        "stores": stores,
        "categories": categories,
        "calendar": calendar,
        "macro": macro,
        "till_mix": till_mix,
        "panel": panel,
    }
