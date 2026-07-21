import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from src import theme
from src.loader import get_assortment_report
from src.sidebar import render_data_source_status

st.set_page_config(page_title="Dynamic Assortment", page_icon="🧩", layout="wide")
render_data_source_status()

st.title("🧩 Dynamic Micro-Clustering and Assortment")
st.caption(
    "Blueprint section 5.3 (expansion phase). We don't rewrite JAM — we supply the dynamic, "
    "branch-level economic-profile signal its static rules can't see: real till currency-mix, "
    "realised category mix, and liquidity sensitivity, clustered independently of each store's "
    "assumed profile label."
)

report = get_assortment_report()
clustered = report["clustered"]
crosstab = report["crosstab"]
drift = report["drift_candidates"]

st.subheader("Data-driven clusters vs. static profile labels")
fig = px.scatter(
    clustered, x="pca_x", y="pca_y", color=clustered["dynamic_cluster"].astype(str),
    symbol="profile", hover_data=["store_id", "profile", "avg_usd_share"],
    color_discrete_sequence=theme.CATEGORICAL,
    labels={"color": "Dynamic cluster", "pca_x": "", "pca_y": ""},
)
theme.apply(fig)
fig.update_traces(marker=dict(size=12, line=dict(width=1, color=theme.SURFACE)))
st.plotly_chart(fig, width="stretch")
st.caption(
    "Each point is a branch, positioned by its actual till-mix / category-mix / volatility "
    "signature (PCA projection). Color = the cluster the data puts it in; shape = the static "
    "profile label JAM currently ranges it under. Mismatches are branches running on a stale "
    "assumption."
)

st.divider()
col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("Static profile × dynamic cluster")
    fig2 = px.imshow(
        crosstab, color_continuous_scale=theme.SEQUENTIAL_BLUE, aspect="auto", text_auto=True,
        labels=dict(color="stores"),
    )
    theme.apply(fig2)
    st.plotly_chart(fig2, width="stretch")

with col2:
    st.subheader("Branches JAM is likely mis-ranging today")
    if drift.empty:
        st.success("No drifted branches detected this cycle — static labels still match the data.")
    else:
        st.dataframe(
            drift.style.format({"avg_usd_share": "{:.0%}", "till_volatility": "{:.2f}"}),
            width="stretch", hide_index=True,
        )
        st.caption(
            "These stores' real economics (till-mix, volatility, category mix) no longer match "
            "the static profile label they're ranged under — a mining town's suburb going "
            "cash-strapped, a mall drifting toward border-town trade patterns, etc."
        )
