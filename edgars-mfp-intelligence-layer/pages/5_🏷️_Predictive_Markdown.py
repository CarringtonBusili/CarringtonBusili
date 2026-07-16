import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src import theme
from src.loader import get_markdown_report

st.set_page_config(page_title="Predictive Markdown", page_icon="🏷️", layout="wide")

st.title("🏷️ Predictive Markdown and Lifecycle Elasticity")
st.caption(
    "Blueprint section 5.2 — acting weeks before the native D365 Lifecycle Worksheet flags "
    "stagnation, bounded by a replacement-cost floor, with reallocation considered before any "
    "discount."
)

report = get_markdown_report()
s = report["summary"]
queue = report["queue"]
flagged = report["flagged"]
reallocation = report["reallocation"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Lines flagged for action", f"{s['n_lines_flagged']}")
k2.metric("Net benefit of acting now", f"${s['total_net_benefit_usd']:,.0f}")
k3.metric("Replacement-cost floor binding", f"{s['n_floor_binding']}", "can't discount further without selling below tomorrow's restock cost")
k4.metric("Reallocation net saving", f"${s['reallocation_net_saving_usd']:,.0f}", f"{s['reallocation_moves']} transfers")

st.caption(
    "'Net benefit of acting now' compares a disciplined pre-emptive markdown today against the "
    "counterfactual of waiting for the retrospective Lifecycle Worksheet to flag the same stock "
    "~12 weeks later: extra carrying cost accrues, and the reactive clearance that follows goes "
    "deeper. That gap — not same-week carrying cost alone — is the real margin the blueprint "
    "says is 'routinely lost to late clearance'."
)

st.divider()
st.subheader("Flagged lines, ranked by benefit of acting now")
st.dataframe(
    flagged[["store_id", "profile", "category", "weeks_to_clear_at_current_velocity",
             "recommended_discount_depth", "reactive_panic_discount_depth", "floor_binding",
             "net_benefit_usd"]]
    .style.format({
        "weeks_to_clear_at_current_velocity": "{:.1f}",
        "recommended_discount_depth": "{:.0%}",
        "reactive_panic_discount_depth": "{:.0%}",
        "net_benefit_usd": "${:,.0f}",
    }),
    width="stretch", hide_index=True, height=380,
)

st.divider()
st.subheader("Sell-through projection for a flagged line")
if flagged.empty:
    st.info("No lines currently flagged.")
else:
    options = [f"{r.store_id} · {r.category}" for r in flagged.itertuples()]
    choice = st.selectbox("Pick a flagged store-category", options)
    store_id, category = choice.split(" · ")
    row = flagged[(flagged["store_id"] == store_id) & (flagged["category"] == category)].iloc[0]

    weeks = np.arange(0, 20)
    stock_do_nothing = np.clip(row["stock_on_hand_units"] - row["predicted_velocity"] * weeks, 0, None)
    achieved_velocity = row["predicted_velocity"] * (1 + 1.8 * row["recommended_discount_depth"])
    stock_markdown = np.clip(row["stock_on_hand_units"] - achieved_velocity * weeks, 0, None)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weeks, y=stock_do_nothing, name="Do nothing (current velocity)",
                              line=dict(color=theme.CATEGORICAL[5], width=2)))
    fig.add_trace(go.Scatter(x=weeks, y=stock_markdown, name=f"With {row['recommended_discount_depth']:.0%} markdown",
                              line=dict(color=theme.CATEGORICAL[0], width=2)))
    theme.apply(fig)
    fig.update_layout(xaxis_title="Weeks from now", yaxis_title="Projected stock on hand (units)")
    st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Reallocation before discounting")
st.caption(
    "Where an inter-branch transfer costs less than the avoided markdown loss, move the stock "
    "to a store profile where it still sells at full price."
)
if reallocation.empty:
    st.info("No profitable reallocation opportunities identified this cycle.")
else:
    st.dataframe(
        reallocation.style.format({
            "transfer_cost_usd": "${:,.0f}", "avoided_markdown_loss_usd": "${:,.0f}", "net_saving_usd": "${:,.0f}",
        }),
        width="stretch", hide_index=True, height=320,
    )
