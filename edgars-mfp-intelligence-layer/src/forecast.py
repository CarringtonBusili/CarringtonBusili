"""
The localised demand-forecasting brain: a gradient-boosted model
(XGBoost) trained on lagged sell-through plus the Zimbabwe Macro Signal
Layer, per Blueprint section 3 ("Python, with gradient-boosted models
such as XGBoost driving the demand forecast").

We deliberately train two models — a naive baseline (recent-history only)
and the macro-informed model — so the dashboard can show, on held-out
weeks, how much of the "current state is blind to the parallel-rate gap"
claim actually holds on this data.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
import xgboost as xgb

LAG_FEATURES = ["lag1", "lag4", "roll4_mean", "roll8_mean"]
MACRO_FEATURES = ["parallel_rate_premium", "liquidity_pressure_index",
                  "spend_velocity_index", "usd_till_share"]
CALENDAR_FEATURES = ["school_term_window", "tobacco_season"]
CATEGORICAL_FEATURES = ["store_id", "category", "profile"]


def build_training_frame(data: dict) -> pd.DataFrame:
    panel = data["panel"].copy()
    macro = data["macro"][["week_num", "parallel_rate_premium",
                            "liquidity_pressure_index", "spend_velocity_index",
                            "school_term_window", "tobacco_season"]]
    panel = panel.merge(macro, on="week_num", how="left")

    panel = panel.sort_values(["store_id", "category", "week_num"])
    grp = panel.groupby(["store_id", "category"])["units_sold"]
    panel["lag1"] = grp.shift(1)
    panel["lag4"] = grp.shift(4)
    panel["roll4_mean"] = grp.transform(lambda s: s.shift(1).rolling(4, min_periods=1).mean())
    panel["roll8_mean"] = grp.transform(lambda s: s.shift(1).rolling(8, min_periods=1).mean())

    panel = panel.dropna(subset=LAG_FEATURES)
    for col in CATEGORICAL_FEATURES:
        panel[col] = panel[col].astype("category")
    panel["school_term_window"] = panel["school_term_window"].astype(int)
    panel["tobacco_season"] = panel["tobacco_season"].astype(int)
    return panel


def _fit(df, feature_cols):
    X, y = df[feature_cols], df["units_sold"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    model = xgb.XGBRegressor(
        n_estimators=250, max_depth=5, learning_rate=0.06,
        subsample=0.85, colsample_bytree=0.85,
        enable_categorical=True, tree_method="hist",
        random_state=42,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, preds),
        "r2": r2_score(y_test, preds),
        "n_test": len(y_test),
    }
    return model, metrics


def train_models(data: dict):
    """Returns (macro_model, macro_metrics, baseline_model, baseline_metrics, training_frame)."""
    df = build_training_frame(data)

    macro_cols = CATEGORICAL_FEATURES + LAG_FEATURES + MACRO_FEATURES + CALENDAR_FEATURES
    macro_model, macro_metrics = _fit(df, macro_cols)

    baseline_cols = CATEGORICAL_FEATURES + LAG_FEATURES
    baseline_model, baseline_metrics = _fit(df, baseline_cols)

    return {
        "macro_model": macro_model, "macro_metrics": macro_metrics, "macro_cols": macro_cols,
        "baseline_model": baseline_model, "baseline_metrics": baseline_metrics, "baseline_cols": baseline_cols,
        "training_frame": df,
    }


def latest_velocity_forecast(model_bundle: dict) -> pd.DataFrame:
    """Predicted weekly sell-through velocity (Vest) per store-category,
    using each series' most recent feature row — this is the number that
    feeds the OTB and Markdown engines."""
    df = model_bundle["training_frame"]
    latest = df.sort_values("week_num").groupby(["store_id", "category"], observed=True).tail(1).copy()

    latest["predicted_velocity"] = model_bundle["macro_model"].predict(latest[model_bundle["macro_cols"]])
    latest["baseline_velocity"] = model_bundle["baseline_model"].predict(latest[model_bundle["baseline_cols"]])
    latest["predicted_velocity"] = latest["predicted_velocity"].clip(lower=0)
    latest["baseline_velocity"] = latest["baseline_velocity"].clip(lower=0)

    keep = ["store_id", "profile", "category", "week_num", "units_sold",
            "predicted_velocity", "baseline_velocity", "stock_on_hand_units",
            "stock_age_weeks", "unit_cost", "unit_price"]
    return latest[keep].reset_index(drop=True)


def predict_history(model_bundle: dict, store_id: str, category: str) -> pd.DataFrame:
    """Actual vs. macro-informed vs. naive-baseline predicted units_sold,
    over the full available history, for one store-category series —
    the 'why this number' view for a single planner-facing line."""
    df = model_bundle["training_frame"]
    series = df[(df["store_id"] == store_id) & (df["category"] == category)].sort_values("week_num").copy()
    if series.empty:
        return series

    series["macro_predicted"] = model_bundle["macro_model"].predict(series[model_bundle["macro_cols"]]).clip(min=0)
    series["baseline_predicted"] = model_bundle["baseline_model"].predict(series[model_bundle["baseline_cols"]]).clip(min=0)
    cols = ["week_num", "units_sold", "macro_predicted", "baseline_predicted"]
    if "week_start" in series.columns:
        cols.insert(1, "week_start")
    return series[cols]


def feature_importance(model_bundle: dict) -> pd.DataFrame:
    model = model_bundle["macro_model"]
    cols = model_bundle["macro_cols"]
    importances = model.feature_importances_
    return (
        pd.DataFrame({"feature": cols, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
