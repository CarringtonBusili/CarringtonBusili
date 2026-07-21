import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from src import theme
from src.loader import get_otb_report
from src.sidebar import render_data_source_status

st.set_page_config(page_title="Capital-Weighted OTB", page_icon="💰", layout="wide")
render_data_source_status()

st.title("💰 Capital-Weighted Open-to-Buy")
st.caption(
    "Blueprint section 5.1 — the core engine. Ranks Open-to-Buy candidates on the capital "
    "they recycle fastest, not just on projected sales."
)

st.latex(
    r"""
    \text{RAROCE} = \frac{(V_{est} \cdot W_{sell} \cdot M_{hc}) - (C_{cap} \cdot W_{sell})
    - FX_{loss} - (P_{def} \cdot L_{md})}{I_{cap}} \times \frac{52}{W_{sell}}
    """
)
with st.expander("Term definitions"):
    st.markdown(
        """
- **V_est** — predicted sell-through velocity (units/week), from the demand-forecast page
- **W_sell** — expected weeks to sell the order
- **M_hc** — hard-currency gross margin per unit
- **C_cap** — weekly carrying cost = capital deployed × weekly borrowing rate
- **FX_loss** — expected hard-currency loss from depreciation over the holding period
- **P_def · L_md** — probability of a markdown × expected markdown loss
- **I_cap** — working capital deployed in the purchase order

Annualising (× 52/W_sell) means fast-turning lines rank higher — exactly the behaviour a 35%+
cost-of-capital economy demands.
"""
    )

report = get_otb_report()
group_buy = report["group_buy"]
allocation = report["allocation"]

st.divider()
k1, k2, k3 = st.columns(3)
k1.metric("Total group-level capital committed", f"${report['total_capital_committed_usd']:,.0f}")
k2.metric("Capital reallocated vs. today's flat split", f"${report['capital_reallocated_usd']:,.0f}")
k3.metric("Categories ranked", f"{len(group_buy)}")

st.subheader("Group-level (national) buy, ranked by annualised RAROCE")
st.caption(
    "Triple-digit annualised figures look extreme but are expected here: apparel margins are "
    "high and the holding period is one 8-week cycle, so × 52/W_sell compounds fast. Treat this "
    "as a **ranking metric** — capital that recycles faster ranks higher, which is the point at "
    "35%+ — not a literal forecast return."
)
st.dataframe(
    group_buy[["otb_priority_rank", "category", "recommended_group_qty", "moq", "pack_size",
               "capital_committed_usd", "weighted_raroce_annualised"]]
    .style.format({
        "capital_committed_usd": "${:,.0f}",
        "weighted_raroce_annualised": "{:.1%}",
    }),
    width="stretch", hide_index=True,
)

fig = px.bar(
    group_buy.sort_values("weighted_raroce_annualised"),
    x="weighted_raroce_annualised", y="category", orientation="h",
    color_discrete_sequence=[theme.CATEGORICAL[0]],
    labels={"weighted_raroce_annualised": "Annualised RAROCE", "category": ""},
)
theme.apply(fig)
fig.update_xaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Store-level allocation: demand-weighted vs. today's flat split")
st.caption(
    "Because Edgars procures centrally in USD, the group buy is aggregated then reallocated to "
    "stores by predicted demand share — replacing the flat, affinity-blind split every store "
    "gets today."
)
category_filter = st.selectbox("Category", sorted(allocation["category"].unique()))
view = allocation[allocation["category"] == category_filter].sort_values("capital_reallocated_usd", ascending=False)

fig2 = px.bar(
    view, x="store_id", y="capital_reallocated_usd", color="profile",
    color_discrete_sequence=theme.CATEGORICAL,
    labels={"capital_reallocated_usd": "Capital shift vs. flat split (USD)", "store_id": ""},
)
theme.apply(fig2)
st.plotly_chart(fig2, width="stretch")

st.dataframe(
    view[["store_id", "profile", "candidate_qty", "allocated_qty", "flat_qty_today",
          "allocated_capital_usd", "capital_reallocated_usd", "raroce_annualised"]]
    .style.format({
        "allocated_capital_usd": "${:,.0f}", "capital_reallocated_usd": "${:,.0f}",
        "raroce_annualised": "{:.1%}",
    }),
    width="stretch", hide_index=True, height=350,
)
