"""
Cached data/model loaders shared across every Streamlit page.

Two data sources are supported: the synthetic demo dataset, and a real
uploaded flat-file extract (see `src/ingest.py`). Every cached function
is keyed on `_dataset_key()` so switching source (or uploading a new
file) correctly invalidates the forecast model and all four engines —
a plain no-argument `@st.cache_resource` would otherwise keep serving
results computed against the previous dataset.
"""
import hashlib

import streamlit as st

from src import data_gen, forecast, ingest
from src.engines import assortment, diagnostic, markdown, otb


def _dataset_key():
    if st.session_state.get("data_source") == "upload" and st.session_state.get("uploaded_bytes"):
        digest = hashlib.md5(st.session_state["uploaded_bytes"]).hexdigest()[:12]
        return ("upload", digest, st.session_state.get("uploaded_name", ""))
    return ("synthetic",)


@st.cache_data(show_spinner="Loading the historical extract...")
def _load_data(key):
    if key[0] == "upload":
        return ingest.build_dataset_from_upload(st.session_state["uploaded_bytes"], st.session_state["uploaded_name"])
    return data_gen.generate_all()


def get_data():
    return _load_data(_dataset_key())


@st.cache_resource(show_spinner="Training the localised demand-forecasting brain (XGBoost)...")
def _load_forecast_bundle(key):
    return forecast.train_models(_load_data(key))


def get_forecast_bundle():
    return _load_forecast_bundle(_dataset_key())


@st.cache_data(show_spinner="Scoring current sell-through velocity per store/category...")
def _load_velocity(key):
    return forecast.latest_velocity_forecast(_load_forecast_bundle(key))


def get_velocity():
    return _load_velocity(_dataset_key())


@st.cache_data(show_spinner="Running the Phase 1 Margin Leakage & Trapped Capital diagnostic...")
def _load_diagnostic_report(key):
    return diagnostic.build_diagnostic_report(_load_data(key))


def get_diagnostic_report():
    return _load_diagnostic_report(_dataset_key())


@st.cache_data(show_spinner="Ranking the Capital-Weighted Open-to-Buy...")
def _load_otb_report(key):
    return otb.build_otb_recommendation(_load_data(key), _load_forecast_bundle(key), _load_velocity(key))


def get_otb_report():
    return _load_otb_report(_dataset_key())


@st.cache_data(show_spinner="Scanning for pre-emptive markdown and reallocation candidates...")
def _load_markdown_report(key):
    diag = _load_diagnostic_report(key)
    return markdown.build_markdown_report(_load_data(key), diag["classified"], _load_velocity(key))


def get_markdown_report():
    return _load_markdown_report(_dataset_key())


@st.cache_data(show_spinner="Clustering branch economic profiles...")
def _load_assortment_report(key):
    return assortment.build_assortment_report(_load_data(key))


def get_assortment_report():
    return _load_assortment_report(_dataset_key())


def data_meta():
    """Small info dict about the active dataset, for the sidebar/header:
    {'source': 'synthetic'|'upload', ...}. Synthetic has no `meta` key
    in its data dict, so this fills one in consistently."""
    data = get_data()
    if "meta" in data:
        return data["meta"]
    return {
        "source": "synthetic", "n_weeks": len(data["calendar"]),
        "n_stores": len(data["stores"]), "n_categories": len(data["categories"]),
    }
