import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from src import theme
from src.loader import get_diagnostic_report

st.set_page_config(page_title="Phase 1 Diagnostic", page_icon="📊", layout="wide")

st.title("📊 Phase 1 — Historical Diagnostic")
st.caption(
    "The Margin Leakage & Trapped Capital report: zero integration, read-only, run entirely "
    "on the historic extract (Blueprint section 7 / 11). This is the deliverable that costs "
    "the gap on Edgars' own figures before a cent of build is committed."
)

report = get_diagnostic_report()
classified = report["classified"]
s = report["summary"]

st.subheader("Headline value pool")
k1, k2, k3 = st.columns(3)
k1.metric("Total stock value (snapshot)", f"${s['total_stock_value_usd']:,.0f}")
k2.metric("Trapped in slow/dead stock", f"${s['trapped_capital_usd']:,.0f}", f"{s['trapped_capital_pct']:.1f}%", delta_color="off")
k3.metric("— of which dead", f"${s['dead_stock_usd']:,.0f}")

k4, k5, k6 = st.columns(3)
k4.metric("Annual carrying cost", f"${s['annual_carrying_cost_usd']:,.0f}")
k5.metric("Saved by clearing 3 months earlier", f"${s['carrying_cost_saved_3mo_earlier_usd']:,.0f}")
k6.metric("Margin at risk from late clearance", f"${s['margin_at_risk_usd']:,.0f}")

st.caption(
    f"Method: a store-category is **slow** at ≥{18} weeks of cover (stock ÷ trailing "
    f"12-week average sell-through) and **dead** at ≥{28} weeks. Margin at risk assumes an "
    "eventual 20% (slow) or 45% (dead) clearance discount if nothing changes."
)

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Trapped capital by category")
    by_cat = report["trapped_capital_by_category"]
    fig = px.bar(
        by_cat, x="category", y="trapped_capital_usd",
        color_discrete_sequence=[theme.CATEGORICAL[7]],
        labels={"trapped_capital_usd": "Trapped capital (USD)", "category": ""},
    )
    theme.apply(fig)
    st.plotly_chart(fig, width="stretch")

with col2:
    st.subheader("Margin lost to stock-outs on winners")
    lost = report["lost_sales_by_category"].head(10)
    fig2 = px.bar(
        lost, x="lost_margin_usd", y="category", color="profile", orientation="h",
        color_discrete_sequence=theme.CATEGORICAL,
        labels={"lost_margin_usd": "Lost margin (USD)", "category": ""},
    )
    theme.apply(fig2)
    fig2.update_layout(yaxis=dict(categoryorder="total ascending"))
    st.plotly_chart(fig2, width="stretch")

st.caption(
    "Left: capital sitting in stock that isn't moving. Right: the flip side under today's flat, "
    "affinity-blind allocation — high-affinity store-category pairs starved of stock while "
    "low-affinity ones sit overstocked (Blueprint: 'fewer stock-outs on winners, no over-buys "
    "on losers')."
)

st.divider()
st.subheader("Store-category detail (latest snapshot)")
health_filter = st.multiselect("Filter by health", ["healthy", "slow", "dead"], default=["slow", "dead"])
view = classified[classified["health"].isin(health_filter)] if health_filter else classified
st.dataframe(
    view[["store_id", "profile", "category", "stock_on_hand_units", "weeks_of_cover",
          "health", "stock_value_usd", "margin_at_risk_usd"]]
    .sort_values("stock_value_usd", ascending=False)
    .style.format({
        "weeks_of_cover": "{:.1f}", "stock_value_usd": "${:,.0f}", "margin_at_risk_usd": "${:,.0f}",
    }),
    width="stretch", height=420,
)
