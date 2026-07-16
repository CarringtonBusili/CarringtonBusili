import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import macro_signals, theme
from src.loader import get_data

st.set_page_config(page_title="Macro Signal Layer", page_icon="🌍", layout="wide")

st.title("🌍 The Zimbabwe Macro Signal Layer")
st.caption(
    "The part no global vendor will build for a single market (Blueprint section 6). "
    "Real internal signals, real public calendars, and constructed proxies clearly labelled "
    "as such — never presented as live feeds."
)

data = get_data()

st.subheader("Signal catalogue")
st.dataframe(macro_signals.SIGNAL_CATALOGUE, width="stretch", hide_index=True)

st.divider()
st.subheader("Parallel-rate pressure and the resulting spend-velocity 'buy-now' surges")

macro = data["macro"]
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=macro["week_start"], y=macro["parallel_rate_premium"], name="Parallel-rate premium",
    line=dict(color=theme.CATEGORICAL[0], width=2),
))
fig.add_trace(go.Scatter(
    x=macro["week_start"], y=macro["liquidity_pressure_index"], name="Liquidity pressure index (normalised)",
    line=dict(color=theme.CATEGORICAL[5], width=2, dash="dot"),
))
jump_weeks = macro[macro["jump_week"]]
fig.add_trace(go.Scatter(
    x=jump_weeks["week_start"], y=jump_weeks["liquidity_pressure_index"], mode="markers",
    name="FX regime shift", marker=dict(color=theme.STATUS["critical"], size=9, symbol="triangle-up"),
))
theme.apply(fig)
fig.update_layout(xaxis_title="", yaxis_title="")
st.plotly_chart(fig, width="stretch")

fig_sv = px.bar(
    macro, x="week_start", y="spend_velocity_index",
    color_discrete_sequence=[theme.CATEGORICAL[4]],
    labels={"spend_velocity_index": "Spend-velocity index", "week_start": ""},
)
theme.apply(fig_sv)
st.plotly_chart(fig_sv, width="stretch")
st.caption(
    "Spikes right after a regime shift are the 'buy-now' surge as ZiG holders rush to convert "
    "into goods before the rate moves again; the dip that follows is the pulled-forward demand "
    "not repeating. A model blind to this reads both as noise."
)

st.divider()
st.subheader("Till currency-mix by store profile")
st.markdown(
    "A single global forecast can't work across 27 stores when the store network's real "
    "liquidity position looks like this:"
)
summary = macro_signals.store_profile_liquidity_summary(data)
fig2 = px.bar(
    summary, x="profile", y="avg_usd_share", error_y="volatility",
    color_discrete_sequence=[theme.CATEGORICAL[0]],
    labels={"avg_usd_share": "Avg. USD till-share", "profile": ""},
)
theme.apply(fig2)
fig2.update_yaxes(tickformat=".0%")
st.plotly_chart(fig2, width="stretch")

st.divider()
st.subheader("Demand sensitivity to liquidity pressure, by profile × category")
st.caption(
    "Correlation between the liquidity pressure index and weekly sell-through. Strongly negative "
    "= the category is being squeezed as ZiG loses purchasing power; near zero = insulated "
    "(e.g. USD-tipped border/mining trade)."
)
sens = macro_signals.demand_sensitivity_to_pressure(data)
pivot = sens.pivot(index="profile", columns="category", values="corr_with_liquidity_pressure")
fig3 = px.imshow(
    pivot, color_continuous_scale=theme.DIVERGING, zmin=-0.6, zmax=0.6, aspect="auto",
    labels=dict(color="correlation"),
)
theme.apply(fig3)
fig3.update_layout(coloraxis_colorbar=dict(title=""))
st.plotly_chart(fig3, width="stretch")
