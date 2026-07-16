"""
Cached data/model loaders shared across every Streamlit page, so the 27
stores, the demand model and the three decision engines are computed
once per session rather than once per page.
"""
import streamlit as st

from src import data_gen, forecast
from src.engines import assortment, diagnostic, markdown, otb


@st.cache_data(show_spinner="Loading the synthetic Edgars historical extract (Phase 1 stand-in)...")
def get_data():
    return data_gen.generate_all()


@st.cache_resource(show_spinner="Training the localised demand-forecasting brain (XGBoost)...")
def get_forecast_bundle():
    return forecast.train_models(get_data())


@st.cache_data(show_spinner="Scoring current sell-through velocity per store/category...")
def get_velocity():
    return forecast.latest_velocity_forecast(get_forecast_bundle())


@st.cache_data(show_spinner="Running the Phase 1 Margin Leakage & Trapped Capital diagnostic...")
def get_diagnostic_report():
    return diagnostic.build_diagnostic_report(get_data())


@st.cache_data(show_spinner="Ranking the Capital-Weighted Open-to-Buy...")
def get_otb_report():
    return otb.build_otb_recommendation(get_data(), get_forecast_bundle(), get_velocity())


@st.cache_data(show_spinner="Scanning for pre-emptive markdown and reallocation candidates...")
def get_markdown_report():
    diag = get_diagnostic_report()
    return markdown.build_markdown_report(get_data(), diag["classified"], get_velocity())


@st.cache_data(show_spinner="Clustering branch economic profiles...")
def get_assortment_report():
    return assortment.build_assortment_report(get_data())
