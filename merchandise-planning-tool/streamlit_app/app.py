"""
Streamlit build of the Merchandise Planning & Buying tool.

Reuses the same data simulation / KPI math / forecasting engine as the
FastAPI backend (backend/app/{data_gen,kpis,forecasting}.py) directly in
this process — no separate API server needed for this deployment.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import data_gen, kpis  # noqa: E402
from app.forecasting import ForecastStore, build_recommendation  # noqa: E402

CATEGORICAL = ["#2a78d6", "#008300", "#e87ba4", "#eda100", "#1baf7a", "#eb6834"]
STATUS = {
    "Urgent Buy": "#d03b3b",
    "Buy": "#fab219",
    "On Track": "#0ca30c",
    "Hold / Markdown": "#ec835a",
}
ICON = {"Urgent Buy": "⛔", "Buy": "⬆️", "On Track": "✅", "Hold / Markdown": "⏸️"}

st.set_page_config(page_title="Merchandise Planning & Buying", page_icon="📦", layout="wide")


@st.cache_resource(show_spinner="Simulating history and training AI forecast models…")
def get_store():
    products, history = data_gen.generate_dataset()
    forecast_store = ForecastStore(history)
    return products, history, forecast_store


def current_inventory(history: pd.DataFrame, product_id: str) -> float:
    row = history[(history["product_id"] == product_id) & (history["weeks_ago"] == 0)]
    return float(row["ending_inventory"].iloc[0]) if not row.empty else 0.0


def fmt_currency(v: float, compact: bool = True) -> str:
    if compact and abs(v) >= 1000:
        return f"${v / 1000:,.1f}K" if abs(v) < 1_000_000 else f"${v / 1_000_000:,.2f}M"
    return f"${v:,.0f}"


def fmt_pct(v: float, digits: int = 1) -> str:
    return f"{v * 100:.{digits}f}%"


products, history, forecast_store = get_store()

st.sidebar.markdown("### 📦 Merchandise Planning & Buying")
st.sidebar.caption("Merchandise Financial Planning")
page = st.sidebar.radio("View", ["Overview", "AI Buying", "Product Detail"], label_visibility="collapsed")

# ---------------------------------------------------------------- Overview
if page == "Overview":
    st.title("Planning Overview")
    period_weeks = st.radio("Period", [4, 13, 26, 52], index=1, horizontal=True, format_func=lambda w: f"{w} wks")

    summary = kpis.summary_kpis(history, products, period_weeks)
    by_category = kpis.category_breakdown(history, products, period_weeks)
    trend = kpis.trend_series(history, max(period_weeks * 2, 26))

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", fmt_currency(summary["revenue"]))
    c2.metric("Gross Margin", fmt_pct(summary["gross_margin_pct"]), fmt_currency(summary["gross_margin"]))
    c3.metric("GMROI", f"{summary['gmroi']:.2f}x")
    c4.metric("Inventory Turnover", f"{summary['inventory_turnover']:.2f}x")
    c5.metric("Sell-Through", fmt_pct(summary["sell_through_pct"]))

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Weeks of Supply", f"{summary['weeks_of_supply']:.1f}")
    c7.metric("Markdown %", fmt_pct(summary["markdown_pct"]))
    c8.metric(
        "Sales vs. Plan",
        fmt_pct(summary["sales_plan_variance_pct"]),
        delta=fmt_pct(summary["sales_plan_variance_pct"]),
        delta_color="normal",
    )
    c9.metric("Stockout Rate", fmt_pct(summary["stockout_rate_pct"]))
    c10.metric("Inventory Value", fmt_currency(summary["ending_inventory_cost_value"]))

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.subheader("Weekly Sales: Actual vs. Plan")
        trend_df = pd.DataFrame(trend)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_df["week_index"], y=trend_df["units_sold"],
            name="Actual units", line=dict(color="#2a78d6", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=trend_df["week_index"], y=trend_df["planned_units"],
            name="Planned units", line=dict(color="#898781", width=2, dash="dot"),
        ))
        fig.update_layout(
            height=320, margin=dict(l=0, r=10, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis_title="Week", yaxis_title="Units",
        )
        st.plotly_chart(fig, width='stretch')

    with col_b:
        st.subheader("Revenue by Category")
        cat_df = pd.DataFrame(by_category)
        fig2 = go.Figure(go.Bar(
            x=cat_df["revenue"], y=cat_df["category"], orientation="h",
            marker_color=CATEGORICAL[: len(cat_df)],
        ))
        fig2.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0), xaxis_title="Revenue ($)")
        st.plotly_chart(fig2, width='stretch')

    st.subheader("Category Performance")
    display_df = cat_df[[
        "category", "revenue", "gross_margin_pct", "sell_through_pct",
        "gmroi", "inventory_turnover", "weeks_of_supply", "markdown_pct",
    ]].rename(columns={
        "category": "Category", "revenue": "Revenue", "gross_margin_pct": "GM%",
        "sell_through_pct": "Sell-Through", "gmroi": "GMROI", "inventory_turnover": "Turns",
        "weeks_of_supply": "WOS", "markdown_pct": "Markdown%",
    })
    # NumberColumn's printf-style format doesn't auto-scale fractions into
    # percentages (unlike a "percent" preset) — pre-multiply by 100 so
    # "%.1f%%" prints "45.1%" instead of "0.5%".
    for col in ["GM%", "Sell-Through", "Markdown%"]:
        display_df[col] = display_df[col] * 100
    st.dataframe(
        display_df,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="$%.0f"),
            "GM%": st.column_config.NumberColumn(format="%.1f%%"),
            "Sell-Through": st.column_config.NumberColumn(format="%.1f%%"),
            "GMROI": st.column_config.NumberColumn(format="%.2fx"),
            "Turns": st.column_config.NumberColumn(format="%.2fx"),
            "WOS": st.column_config.NumberColumn(format="%.1f"),
            "Markdown%": st.column_config.NumberColumn(format="%.1f%%"),
        },
        hide_index=True, width='stretch',
    )

# ------------------------------------------------------------------ Buying
elif page == "AI Buying":
    st.title("AI Buying Recommendations")
    st.caption(
        "Demand forecast (gradient-boosted regressor + seasonal baseline) blended into an "
        "open-to-buy recommendation per SKU: forecast over lead time + reorder cycle, plus "
        "safety stock, minus on-hand inventory."
    )

    recs = []
    for _, product in products.iterrows():
        fc = forecast_store.get(product["product_id"])
        if fc is None:
            continue
        recs.append(build_recommendation(product, fc, current_inventory(history, product["product_id"])))
    recs_df = pd.DataFrame(recs)

    total_spend = recs_df["recommended_order_cost"].sum()
    urgent = recs_df[recs_df["action"] == "Urgent Buy"]
    avg_accuracy = 1 - recs_df["forecast_wape"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recommended Spend", fmt_currency(total_spend))
    c2.metric("SKUs Tracked", len(recs_df))
    c3.metric("Avg. Forecast Accuracy", fmt_pct(avg_accuracy))
    c4.metric("Urgent Buys", len(urgent), fmt_currency(urgent["recommended_order_cost"].sum()))

    fc1, fc2 = st.columns(2)
    category_filter = fc1.selectbox("Category", ["All"] + sorted(products["category"].unique().tolist()))
    action_filter = fc2.selectbox("Action", ["All"] + list(STATUS.keys()))

    filtered = recs_df.copy()
    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]
    if action_filter != "All":
        filtered = filtered[filtered["action"] == action_filter]

    priority = {"Urgent Buy": 0, "Buy": 1, "On Track": 2, "Hold / Markdown": 3}
    filtered = filtered.assign(_p=filtered["action"].map(priority)).sort_values(
        ["_p", "recommended_order_cost"], ascending=[True, False]
    )
    filtered["Action"] = filtered["action"].apply(lambda a: f"{ICON[a]} {a}")

    view = filtered[[
        "name", "category", "Action", "current_inventory_units", "current_weeks_of_supply",
        "target_weeks_of_supply", "momentum_pct", "recommended_order_units",
        "recommended_order_cost", "forecast_wape",
    ]].rename(columns={
        "name": "Product", "category": "Category", "current_inventory_units": "On Hand",
        "current_weeks_of_supply": "Cur. WOS", "target_weeks_of_supply": "Target WOS",
        "momentum_pct": "Momentum", "recommended_order_units": "Recommended Qty",
        "recommended_order_cost": "Order Cost", "forecast_wape": "WAPE",
    })
    view["Accuracy"] = (1 - view["WAPE"]) * 100
    view["Momentum"] = view["Momentum"] * 100
    view = view.drop(columns=["WAPE"])

    st.dataframe(
        view,
        column_config={
            "On Hand": st.column_config.NumberColumn(format="%.0f"),
            "Cur. WOS": st.column_config.NumberColumn(format="%.1f"),
            "Target WOS": st.column_config.NumberColumn(format="%.1f"),
            "Momentum": st.column_config.NumberColumn(format="%.1f%%"),
            "Recommended Qty": st.column_config.NumberColumn(format="%.0f u"),
            "Order Cost": st.column_config.NumberColumn(format="$%.0f"),
            "Accuracy": st.column_config.NumberColumn(format="%.1f%%"),
        },
        hide_index=True, width='stretch', height=560,
    )

# ------------------------------------------------------------- Product Detail
else:
    st.title("Product Forecast Detail")
    product_label = st.selectbox(
        "Product",
        products.apply(lambda p: f"{p['name']} ({p['product_id']})", axis=1),
    )
    product_id = product_label.split("(")[-1].rstrip(")")
    product = products[products["product_id"] == product_id].iloc[0]
    fc = forecast_store.get(product_id)
    inv = current_inventory(history, product_id)

    st.caption(f"{product['category']} · ${product['retail_price']:.2f} retail / ${product['unit_cost']:.2f} cost")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("On Hand", f"{inv:.0f} u")
    c2.metric("Lead Time", f"{int(product['lead_time_weeks'])} wks")
    c3.metric("Target WOS", f"{product['target_wos']:.1f}")
    c4.metric("AI Forecast Accuracy", fmt_pct(1 - fc.wape))

    st.subheader("12-Week Demand Forecast")
    recent_history = fc.history[-26:]
    hist_df = pd.DataFrame(recent_history)
    fc_df = pd.DataFrame(fc.forecast)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fc_df["week_index"], y=fc_df["high_90"], line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=fc_df["week_index"], y=fc_df["low_90"], line=dict(width=0),
        fill="tonexty", fillcolor="rgba(42,120,214,0.15)", name="90% confidence",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=hist_df["week_index"], y=hist_df["units_sold"], name="Actual units",
        line=dict(color="#52514e", width=2),
    ))
    bridge_x = [hist_df["week_index"].iloc[-1]] + fc_df["week_index"].tolist()
    bridge_y = [hist_df["units_sold"].iloc[-1]] + fc_df["forecast_units"].tolist()
    fig.add_trace(go.Scatter(
        x=bridge_x, y=bridge_y, name="AI forecast",
        line=dict(color="#2a78d6", width=2, dash="dash"),
    ))
    fig.update_layout(
        height=380, margin=dict(l=0, r=10, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="Week", yaxis_title="Units",
    )
    st.plotly_chart(fig, width='stretch')

    rec = build_recommendation(product, fc, inv)
    st.subheader("Buy Recommendation")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Action", f"{ICON[rec['action']]} {rec['action']}")
    r2.metric("Recommended Order", f"{rec['recommended_order_units']:.0f} u", fmt_currency(rec["recommended_order_cost"]))
    r3.metric("Forecasted Demand (coverage)", f"{rec['forecast_demand_units']:.0f} u")
    r4.metric("Safety Stock", f"{rec['safety_stock_units']:.0f} u")
    st.caption(rec["reason"])
