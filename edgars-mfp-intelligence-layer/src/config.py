"""
Shared constants for the Edgars MFP Intelligence Layer demo.

All figures here are illustrative / synthetic. They exist to give the
decision engines something realistic to reason about; they are not
Edgars' actual financials.
"""
from datetime import date

# ---------------------------------------------------------------------------
# Economics
# ---------------------------------------------------------------------------
COST_OF_CAPITAL_ANNUAL = 0.35          # 35%+ borrowing rate cited in the blueprint
WEEKLY_BORROW_RATE = COST_OF_CAPITAL_ANNUAL / 52

# ---------------------------------------------------------------------------
# Time horizon: 104 weeks (24 months) of history, as Phase 1 requests
# ---------------------------------------------------------------------------
HISTORY_START = date(2024, 7, 1)
N_WEEKS = 104

# ---------------------------------------------------------------------------
# Store network: 27 branches across distinct local-economy profiles.
# Each profile has a different USD:ZiG till mix and price sensitivity,
# which is exactly the variation the Macro Signal Layer / Dynamic
# Assortment engine needs to pick up on.
# ---------------------------------------------------------------------------
STORE_PROFILES = {
    "mining_town": {
        "n_stores": 5,
        "usd_till_share_base": 0.78,
        "price_sensitivity": 0.7,
        "volatility": 0.06,
    },
    "civil_servant_suburb": {
        "n_stores": 8,
        "usd_till_share_base": 0.35,
        "price_sensitivity": 1.3,
        "volatility": 0.10,
    },
    "border_town": {
        "n_stores": 4,
        "usd_till_share_base": 0.85,
        "price_sensitivity": 0.6,
        "volatility": 0.05,
    },
    "urban_mall": {
        "n_stores": 7,
        "usd_till_share_base": 0.55,
        "price_sensitivity": 1.0,
        "volatility": 0.08,
    },
    "rural_growth_point": {
        "n_stores": 3,
        "usd_till_share_base": 0.45,
        "price_sensitivity": 1.1,
        "volatility": 0.12,
    },
}
TOTAL_STORES = sum(p["n_stores"] for p in STORE_PROFILES.values())  # 27

# ---------------------------------------------------------------------------
# Merchandise categories (apparel-led, matching Edgars' core business)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Menswear":        {"unit_cost": 12.0, "unit_price": 26.0, "moq": 200, "pack_size": 12, "base_weekly_units_per_store": 22},
    "Womenswear":      {"unit_cost": 11.0, "unit_price": 28.0, "moq": 200, "pack_size": 12, "base_weekly_units_per_store": 26},
    "Kidswear":        {"unit_cost": 7.0,  "unit_price": 16.0, "moq": 300, "pack_size": 24, "base_weekly_units_per_store": 30},
    "Footwear":        {"unit_cost": 15.0, "unit_price": 34.0, "moq": 150, "pack_size": 6,  "base_weekly_units_per_store": 14},
    "School Uniforms": {"unit_cost": 9.0,  "unit_price": 20.0, "moq": 400, "pack_size": 24, "base_weekly_units_per_store": 18},
    "Sportswear":      {"unit_cost": 13.0, "unit_price": 30.0, "moq": 150, "pack_size": 12, "base_weekly_units_per_store": 12},
    "Home & Textiles": {"unit_cost": 8.0,  "unit_price": 19.0, "moq": 250, "pack_size": 12, "base_weekly_units_per_store": 10},
    "Accessories":     {"unit_cost": 4.0,  "unit_price": 10.0, "moq": 300, "pack_size": 24, "base_weekly_units_per_store": 16},
}

# ---------------------------------------------------------------------------
# Calendar signals (Zimbabwe-specific)
# ---------------------------------------------------------------------------
SCHOOL_TERM_STARTS_MMDD = ["01-13", "05-06", "09-09"]   # approx Zim school term starts
TOBACCO_SEASON_MONTHS = {2, 3, 4, 5, 6, 7}               # Feb-Jul selling season

# ---------------------------------------------------------------------------
# Cross-border lead time (weeks) — used by the OTB engine's holding-period math
# ---------------------------------------------------------------------------
IMPORT_LEAD_TIME_WEEKS = 8

RANDOM_SEED = 42
