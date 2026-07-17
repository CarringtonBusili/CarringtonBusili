"""
AI forecasting + buy-recommendation engine.

For each SKU we train a gradient-boosted regressor on engineered time
series features (calendar seasonality, trend, lag/rolling sales) and
blend it with a seasonal-naive baseline for robustness on short
per-SKU histories. The blended model is:

  1. Backtested on the most recent `HOLDOUT_WEEKS` to produce a MAPE
     accuracy score and a residual std used for forecast confidence
     bands.
  2. Retrained on the full history and rolled forward recursively to
     produce an N-week demand forecast.
  3. Converted into an open-to-buy style purchase recommendation using
     the SKU's lead time, reorder cycle, on-hand inventory and target
     weeks-of-supply.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

HOLDOUT_WEEKS = 8
FORECAST_HORIZON = 12
MIN_LAG = 8
Z_90 = 1.2816


def _calendar_features(week_of_year: np.ndarray) -> pd.DataFrame:
    radians = 2 * np.pi * week_of_year / 52
    return pd.DataFrame({
        "woy_sin": np.sin(radians),
        "woy_cos": np.cos(radians),
    })


def _seasonal_naive_lookup(units: np.ndarray, week_of_year: np.ndarray) -> dict[int, float]:
    lookup = {}
    for woy in range(1, 53):
        dist = np.minimum(np.abs(week_of_year - woy), 52 - np.abs(week_of_year - woy))
        mask = dist <= 2
        lookup[woy] = float(units[mask].mean()) if mask.any() else float(units.mean())
    return lookup


def _build_feature_frame(hist: pd.DataFrame) -> pd.DataFrame:
    hist = hist.sort_values("week_index").reset_index(drop=True)
    units = hist["units_sold"].to_numpy(dtype=float)

    feats = _calendar_features(hist["week_of_year"].to_numpy())
    feats["trend"] = hist["week_index"].to_numpy()
    feats["promo_flag"] = hist["promo_flag"].to_numpy()
    feats["markdown_flag"] = hist["markdown_flag"].to_numpy()
    feats["lag_1"] = pd.Series(units).shift(1)
    feats["lag_2"] = pd.Series(units).shift(2)
    feats["lag_4"] = pd.Series(units).shift(4)
    feats["lag_8"] = pd.Series(units).shift(8)
    feats["roll_mean_4"] = pd.Series(units).shift(1).rolling(4).mean()
    feats["roll_mean_8"] = pd.Series(units).shift(1).rolling(8).mean()
    feats["target"] = units
    feats["week_index"] = hist["week_index"].to_numpy()
    feats["week_of_year"] = hist["week_of_year"].to_numpy()
    return feats.dropna().reset_index(drop=True)


FEATURE_COLS = [
    "woy_sin", "woy_cos", "trend", "promo_flag", "markdown_flag",
    "lag_1", "lag_2", "lag_4", "lag_8", "roll_mean_4", "roll_mean_8",
]


@dataclass
class ProductForecast:
    product_id: str
    wape: float
    residual_std: float
    forecast: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


def _make_model() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=140, max_depth=2, learning_rate=0.07,
        subsample=0.85, random_state=7,
    )


def train_and_forecast(product_id: str, hist: pd.DataFrame) -> ProductForecast:
    hist = hist.sort_values("week_index").reset_index(drop=True)
    feat_df = _build_feature_frame(hist)

    naive_lookup = _seasonal_naive_lookup(
        hist["units_sold"].to_numpy(dtype=float), hist["week_of_year"].to_numpy()
    )

    # --- backtest for accuracy + residual std ---
    train_df = feat_df.iloc[:-HOLDOUT_WEEKS]
    test_df = feat_df.iloc[-HOLDOUT_WEEKS:]

    model = _make_model()
    model.fit(train_df[FEATURE_COLS], train_df["target"])
    model_pred = model.predict(test_df[FEATURE_COLS])
    naive_pred = np.array([naive_lookup[w] for w in test_df["week_of_year"]])
    blended_pred = np.clip(0.7 * model_pred + 0.3 * naive_pred, 0, None)

    actual = test_df["target"].to_numpy()
    # WAPE (weighted/aggregate MAPE) rather than per-week MAPE: per-week
    # percentage error blows up on near-zero-sales weeks, which are common
    # at SKU level. Summing before dividing keeps the metric stable.
    total_actual = actual.sum()
    wape = float(np.sum(np.abs(actual - blended_pred)) / total_actual) if total_actual > 0 else 0.0
    residual_std = float(np.std(actual - blended_pred))

    # --- retrain on full history for production forecast ---
    full_model = _make_model()
    full_model.fit(feat_df[FEATURE_COLS], feat_df["target"])

    units_history = hist["units_sold"].to_numpy(dtype=float).tolist()
    last_week_index = int(hist["week_index"].iloc[-1])
    last_week_of_year = int(hist["week_of_year"].iloc[-1])

    forecasts = []
    rolling_units = units_history.copy()
    for step in range(1, FORECAST_HORIZON + 1):
        week_index = last_week_index + step
        week_of_year = ((last_week_of_year - 1 + step) % 52) + 1
        radians = 2 * np.pi * week_of_year / 52

        row = {
            "woy_sin": np.sin(radians),
            "woy_cos": np.cos(radians),
            "trend": week_index,
            "promo_flag": 0,
            "markdown_flag": 0,
            "lag_1": rolling_units[-1],
            "lag_2": rolling_units[-2],
            "lag_4": rolling_units[-4],
            "lag_8": rolling_units[-8],
            "roll_mean_4": np.mean(rolling_units[-4:]),
            "roll_mean_8": np.mean(rolling_units[-8:]),
        }
        X = pd.DataFrame([row])[FEATURE_COLS]
        model_pred_step = full_model.predict(X)[0]
        naive_pred_step = naive_lookup[week_of_year]
        blended = max(0.0, 0.7 * model_pred_step + 0.3 * naive_pred_step)

        band = Z_90 * residual_std * np.sqrt(step)
        forecasts.append({
            "week_index": int(week_index),
            "week_of_year": int(week_of_year),
            "weeks_ahead": step,
            "forecast_units": round(float(blended), 1),
            "low_90": round(max(0.0, blended - band), 1),
            "high_90": round(float(blended + band), 1),
        })
        rolling_units.append(blended)

    return ProductForecast(
        product_id=product_id,
        wape=round(min(wape, 1.0), 4),
        residual_std=round(residual_std, 2),
        forecast=forecasts,
        history=hist[["week_index", "week_of_year", "units_sold", "weeks_ago"]].to_dict(orient="records"),
    )


class ForecastStore:
    """Trains once per product at startup and caches results in memory."""

    def __init__(self, history: pd.DataFrame):
        self._cache: dict[str, ProductForecast] = {}
        for pid, g in history.groupby("product_id"):
            self._cache[pid] = train_and_forecast(pid, g)

    def get(self, product_id: str) -> ProductForecast | None:
        return self._cache.get(product_id)

    def all(self) -> dict[str, ProductForecast]:
        return self._cache


def build_recommendation(product: pd.Series, fc: ProductForecast, current_inventory: float) -> dict:
    """Open-to-buy style recommendation for one SKU.

    recommended_qty = demand over (lead time + reorder cycle) + safety stock
                       - current on-hand inventory
    """
    lead_time = int(product["lead_time_weeks"])
    review_period = int(product["reorder_cycle_weeks"])
    target_wos = float(product["target_wos"])
    coverage_weeks = lead_time + review_period

    covered = fc.forecast[:coverage_weeks]
    demand_over_coverage = sum(f["forecast_units"] for f in covered)
    safety_stock = Z_90 * fc.residual_std * np.sqrt(max(lead_time, 1))

    recommended_qty = max(0.0, demand_over_coverage + safety_stock - current_inventory)

    avg_weekly_forecast = np.mean([f["forecast_units"] for f in fc.forecast[:4]]) or 0.01
    current_wos = current_inventory / avg_weekly_forecast

    if current_wos < target_wos * 0.5:
        action, reason = "Urgent Buy", "Projected stockout before next receipt at lead time"
    elif current_wos < target_wos * 0.9:
        action, reason = "Buy", "Below target weeks of supply"
    elif current_wos > target_wos * 1.75:
        action, reason = "Hold / Markdown", "Overstock risk relative to forecasted demand"
    else:
        action, reason = "On Track", "Inventory aligned with target weeks of supply"

    recent_avg = np.mean([h["units_sold"] for h in fc.history[-8:]])
    forecast_avg = np.mean([f["forecast_units"] for f in fc.forecast[:8]])
    # WAPE-style ratio (denominator = sum of both sides) instead of raw
    # percent change: a low-volume SKU with recent_avg near zero would
    # otherwise blow up to a meaningless four-digit "momentum" swing.
    momentum_pct = (forecast_avg - recent_avg) / max(recent_avg + forecast_avg, 1.0) * 2

    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "category": product["category"],
        "lead_time_weeks": lead_time,
        "review_period_weeks": review_period,
        "current_inventory_units": round(float(current_inventory), 1),
        "current_weeks_of_supply": round(float(current_wos), 1),
        "target_weeks_of_supply": target_wos,
        "forecast_demand_units": round(demand_over_coverage, 1),
        "safety_stock_units": round(float(safety_stock), 1),
        "recommended_order_units": round(recommended_qty, 0),
        "recommended_order_cost": round(recommended_qty * float(product["unit_cost"]), 2),
        "recommended_order_retail_value": round(recommended_qty * float(product["retail_price"]), 2),
        "momentum_pct": round(float(momentum_pct), 4),
        "action": action,
        "reason": reason,
        "forecast_wape": fc.wape,
    }
