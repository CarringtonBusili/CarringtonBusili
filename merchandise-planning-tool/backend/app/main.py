from __future__ import annotations

from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import data_gen, kpis
from .forecasting import ForecastStore, build_recommendation

app = FastAPI(title="Merchandise Planning & Buying API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Store:
    """In-memory dataset + trained forecast models, built once at startup."""

    def __init__(self) -> None:
        self.products, self.history = data_gen.generate_dataset()
        self.forecast_store = ForecastStore(self.history)

    def product_or_404(self, product_id: str) -> pd.Series:
        rows = self.products[self.products["product_id"] == product_id]
        if rows.empty:
            raise HTTPException(status_code=404, detail=f"Unknown product_id '{product_id}'")
        return rows.iloc[0]

    def current_inventory(self, product_id: str) -> float:
        row = self.history[(self.history["product_id"] == product_id) & (self.history["weeks_ago"] == 0)]
        return float(row["ending_inventory"].iloc[0]) if not row.empty else 0.0


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    store = get_store()
    return sorted(store.products["category"].unique().tolist())


@app.get("/api/products")
def list_products():
    store = get_store()
    out = []
    for _, p in store.products.iterrows():
        out.append({
            **p.to_dict(),
            "current_inventory_units": store.current_inventory(p["product_id"]),
        })
    return out


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    store = get_store()
    p = store.product_or_404(product_id)
    return {**p.to_dict(), "current_inventory_units": store.current_inventory(product_id)}


@app.get("/api/kpis/summary")
def kpi_summary(period_weeks: int = 13):
    store = get_store()
    return kpis.summary_kpis(store.history, store.products, period_weeks)


@app.get("/api/kpis/by-category")
def kpi_by_category(period_weeks: int = 13):
    store = get_store()
    return kpis.category_breakdown(store.history, store.products, period_weeks)


@app.get("/api/kpis/trend")
def kpi_trend(weeks: int = 26, category: str | None = None):
    store = get_store()
    return kpis.trend_series(store.history, weeks, category, store.products)


@app.get("/api/products/{product_id}/kpis")
def product_kpis(product_id: str, period_weeks: int = 13):
    store = get_store()
    store.product_or_404(product_id)
    return kpis.product_kpis(store.history, store.products, product_id, period_weeks)


@app.get("/api/products/{product_id}/forecast")
def product_forecast(product_id: str):
    store = get_store()
    store.product_or_404(product_id)
    fc = store.forecast_store.get(product_id)
    if fc is None:
        raise HTTPException(status_code=404, detail="No forecast available")
    return {
        "product_id": fc.product_id,
        "wape": fc.wape,
        "accuracy_pct": round(1 - fc.wape, 4),
        "residual_std": fc.residual_std,
        "history": fc.history,
        "forecast": fc.forecast,
    }


@app.get("/api/buying/recommendations")
def buying_recommendations(category: str | None = None, action: str | None = None):
    store = get_store()
    products = store.products
    if category:
        products = products[products["category"] == category]

    recs = []
    for _, product in products.iterrows():
        fc = store.forecast_store.get(product["product_id"])
        if fc is None:
            continue
        current_inv = store.current_inventory(product["product_id"])
        recs.append(build_recommendation(product, fc, current_inv))

    if action:
        recs = [r for r in recs if r["action"] == action]

    priority = {"Urgent Buy": 0, "Buy": 1, "On Track": 2, "Hold / Markdown": 3}
    recs.sort(key=lambda r: (priority.get(r["action"], 9), -r["recommended_order_cost"]))
    return recs


@app.get("/api/buying/summary")
def buying_summary():
    recs = buying_recommendations()
    total_cost = sum(r["recommended_order_cost"] for r in recs)
    by_action = {}
    for r in recs:
        by_action.setdefault(r["action"], {"count": 0, "cost": 0.0})
        by_action[r["action"]]["count"] += 1
        by_action[r["action"]]["cost"] += r["recommended_order_cost"]
    return {
        "total_recommended_spend": round(total_cost, 2),
        "sku_count": len(recs),
        "by_action": by_action,
        "avg_forecast_accuracy_pct": round(
            1 - (sum(r["forecast_wape"] for r in recs) / len(recs)), 4
        ) if recs else 0,
    }
