import streamlit as st

from src import theme  # noqa: F401 (registers the shared Plotly template)
from src.loader import get_diagnostic_report

st.set_page_config(
    page_title="Edgars MFP Intelligence Layer",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 The Localised MFP Intelligence Layer")
st.caption(
    "A predictive merchandise-planning brain on top of Microsoft Dynamics 365 LS Central, "
    "built for the realities of the Zimbabwean economy — **Northlea Consulting**, for the "
    "Edgars Executive Committee."
)

st.info(
    "**This is a working simulation, not Edgars' real data.** No live Edgars/D365 extract "
    "exists for this demo, so every store, sale, till reading and FX series here is "
    "synthetically generated (fixed random seed, reproducible) to the shape described in the "
    "blueprint — 27 stores across 5 local-economy profiles, 8 apparel categories, 104 weeks "
    "of history. The engines below (forecast, Capital-Weighted OTB, Predictive Markdown, "
    "Dynamic Assortment) are fully functional against this data and are exactly what would run "
    "against a real Phase 1 flat-file extract.",
    icon="🧪",
)

st.subheader("The gap this closes")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        "**What D365 LS Central already does:** tracks Open-to-Buy budgets, gives a "
        "retrospective markdown overview (Lifecycle Worksheet), manages assortment via the "
        "JAM extension, and runs a native demand forecast within an operational scope."
    )
with col2:
    st.markdown(
        "**What it can't do:** make merchandise decisions in the context of a 35%+ cost of "
        "capital, hard-currency scarcity and an FX-volatile economy. A global forecast is "
        "blind to a widening parallel-rate gap; a global OTB ledger treats a dollar the same "
        "whether money costs 2% or 40%."
    )

st.divider()
st.subheader("Phase 1 Historical Diagnostic — headline numbers, from this simulation")

report = get_diagnostic_report()
s = report["summary"]

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Capital trapped in slow/dead stock",
    f"${s['trapped_capital_usd']:,.0f}",
    f"{s['trapped_capital_pct']:.1f}% of stock value",
    delta_color="off",
)
k2.metric(
    "Annual carrying cost on that capital",
    f"${s['annual_carrying_cost_usd']:,.0f}",
    f"at {35:.0f}%+ cost of capital",
    delta_color="off",
)
k3.metric(
    "Margin at risk from late clearance",
    f"${s['margin_at_risk_usd']:,.0f}",
)
k4.metric(
    "Margin lost to stock-outs on winners",
    f"${s['total_lost_margin_from_stockouts_usd']:,.0f}",
    "flat allocation, blind to local affinity",
    delta_color="off",
)

st.caption(
    "These are simulated figures illustrating the mechanics described in Blueprint section 2 "
    "(working capital liberation, carrying-cost penalty, margin preservation, supply-chain "
    "resilience) — not an audit of Edgars' actual position. Phase 1 replaces this page with "
    "real, audited numbers from Edgars' own extract."
)

st.divider()
st.subheader("Explore the engines")
st.markdown(
    """
Use the sidebar to walk through each layer of the intelligence stack, in the order data
actually flows:

1. **📊 Phase 1 Diagnostic** — the Margin Leakage & Trapped Capital report
2. **🌍 Macro Signal Layer** — the Zimbabwe-specific signals conditioning the forecast
3. **📈 Demand Forecast** — the macro-informed vs. naive XGBoost sell-through model
4. **💰 Capital-Weighted OTB** — the RAROCE-ranked buy recommendation
5. **🏷️ Predictive Markdown** — pre-emptive markdown & inter-branch reallocation
6. **🧩 Dynamic Assortment** — branch economic-profile clustering for JAM
"""
)
