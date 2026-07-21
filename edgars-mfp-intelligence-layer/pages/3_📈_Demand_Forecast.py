import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import forecast, theme
from src.loader import get_data, get_forecast_bundle
from src.sidebar import render_data_source_status

st.set_page_config(page_title="Demand Forecast", page_icon="📈", layout="wide")
render_data_source_status()

st.title("📈 The Localised Demand-Forecasting Brain")
st.caption(
    "Gradient-boosted (XGBoost) sell-through forecast, trained on lagged sales plus the "
    "Zimbabwe Macro Signal Layer — the 'one localised demand-forecasting brain' feeding all "
    "three decision engines (Blueprint section 1)."
)

data = get_data()
bundle = get_forecast_bundle()

st.subheader("Does the macro layer actually help?")
st.caption("Held-out weeks (last 20% of history, walk-forward split), same model family both ways.")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Macro-informed model**")
    st.metric("MAE (units/week)", f"{bundle['macro_metrics']['mae']:.2f}")
    st.metric("R²", f"{bundle['macro_metrics']['r2']:.3f}")
with c2:
    st.markdown("**Naive baseline** (recent sales history only, no macro features)")
    st.metric("MAE (units/week)", f"{bundle['baseline_metrics']['mae']:.2f}")
    st.metric("R²", f"{bundle['baseline_metrics']['r2']:.3f}")

improvement = (1 - bundle["macro_metrics"]["mae"] / bundle["baseline_metrics"]["mae"]) * 100
st.success(
    f"Conditioning on the macro signal layer cuts forecast error by **{improvement:.0f}%** "
    "on this simulation — directly evidencing the blueprint's claim that a forecast blind to "
    "the parallel-rate gap and till currency-mix is a materially worse forecast."
)

st.divider()
st.subheader("What the model actually leans on")
importance = forecast.feature_importance(bundle)
fig = px.bar(
    importance, x="importance", y="feature", orientation="h",
    color_discrete_sequence=[theme.CATEGORICAL[0]],
)
theme.apply(fig)
fig.update_layout(yaxis=dict(categoryorder="total ascending"), xaxis_title="Feature importance", yaxis_title="")
st.plotly_chart(fig, width="stretch")

st.divider()
st.subheader("Inspect a single store-category series")
stores = sorted(data["stores"]["store_id"].unique())
categories = sorted(data["categories"]["category"].unique())
col1, col2 = st.columns(2)
store_id = col1.selectbox("Store", stores, index=stores.index("S10") if "S10" in stores else 0)
category = col2.selectbox("Category", categories, index=0)

history = forecast.predict_history(bundle, store_id, category)
if history.empty:
    st.warning("No history for this combination.")
else:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=history["week_start"], y=history["units_sold"], name="Actual",
                               line=dict(color=theme.TEXT_PRIMARY, width=2)))
    fig2.add_trace(go.Scatter(x=history["week_start"], y=history["macro_predicted"], name="Macro-informed forecast",
                               line=dict(color=theme.CATEGORICAL[0], width=2, dash="dash")))
    fig2.add_trace(go.Scatter(x=history["week_start"], y=history["baseline_predicted"], name="Naive baseline",
                               line=dict(color=theme.CATEGORICAL[5], width=2, dash="dot")))
    theme.apply(fig2)
    fig2.update_layout(yaxis_title="Units sold / week", xaxis_title="")
    st.plotly_chart(fig2, width="stretch")
