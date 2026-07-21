"""Data-source picker: synthetic demo data vs. a real uploaded extract.
The full control panel renders once (on Home); every other page shows a
small read-only status line so it's always clear which dataset the
numbers on screen came from.
"""
import io

import pandas as pd
import streamlit as st

from src.ingest import ALIASES, IngestError, OPTIONAL_FIELDS, REQUIRED_FIELDS
from src.loader import data_meta, get_data


def _template_csv_bytes() -> bytes:
    rows = []
    stores = [("S01", "mining_town"), ("S02", "civil_servant_suburb")]
    categories = ["Menswear", "Kidswear"]
    dates = pd.date_range("2025-01-06", periods=3, freq="W-MON")
    for store_id, profile in stores:
        for category in categories:
            for i, d in enumerate(dates):
                rows.append({
                    "date": d.date().isoformat(), "store_id": store_id, "category": category,
                    "units_sold": 20 + i * 3, "unit_cost": 10.0, "unit_price": 22.0,
                    "stock_on_hand": 150 - i * 15, "usd_till_share": 0.6, "store_profile": profile,
                })
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue().encode()


def render_data_source_controls():
    st.sidebar.subheader("Data source")
    choice = st.sidebar.radio(
        "Run the engines on:", ["Synthetic demo data", "My own uploaded extract"],
        index=1 if st.session_state.get("data_source") == "upload" else 0,
        label_visibility="collapsed",
    )

    if choice == "Synthetic demo data":
        st.session_state["data_source"] = "synthetic"
    else:
        st.session_state["data_source"] = "upload"
        uploaded = st.sidebar.file_uploader("Historic extract (CSV or Parquet)", type=["csv", "parquet"])
        if uploaded is not None:
            st.session_state["uploaded_bytes"] = uploaded.getvalue()
            st.session_state["uploaded_name"] = uploaded.name

        with st.sidebar.expander("Expected format"):
            st.caption(
                "One row per sale (or pre-aggregated by week). Required columns "
                f"(any of these header spellings work): **{', '.join(REQUIRED_FIELDS)}**. "
                f"Optional: **{', '.join(OPTIONAL_FIELDS)}** — without `usd_till_share` the "
                "macro layer runs on a neutral placeholder; without `store_profile` the "
                "Dynamic Assortment page can't compare against a static label."
            )
            st.download_button(
                "Download CSV template", data=_template_csv_bytes(),
                file_name="edgars_mfp_extract_template.csv", mime="text/csv",
            )

        if not st.session_state.get("uploaded_bytes"):
            st.sidebar.info("Upload a file to switch off the synthetic demo data.")
            st.session_state["data_source"] = "synthetic"

    if st.session_state.get("data_source") == "upload" and st.session_state.get("uploaded_bytes"):
        try:
            data = get_data()
        except IngestError as e:
            st.sidebar.error(str(e))
            st.error(f"Couldn't use the uploaded file: {e}")
            st.stop()
        meta = data.get("meta", {})
        st.sidebar.success(
            f"Using **{meta.get('file_name')}** — {meta.get('n_stores')} stores, "
            f"{meta.get('n_categories')} categories, {meta.get('n_weeks')} weeks "
            f"({meta.get('rows_used'):,} rows used, {meta.get('rows_dropped')} dropped)."
        )
        if not meta.get("has_till_data"):
            st.sidebar.warning("No `usd_till_share` column found — macro signal layer is running on a flat placeholder.")
        if not meta.get("has_profile_data"):
            st.sidebar.warning("No `store_profile` column found — all branches are labelled 'unclassified'.")
    else:
        st.sidebar.caption("Using the synthetic demo dataset (27 stores, 104 weeks).")


def render_data_source_status():
    meta = data_meta()
    if meta.get("source") == "upload":
        st.sidebar.success(f"Data source: **{meta.get('file_name')}** (uploaded)")
    else:
        st.sidebar.caption("Data source: synthetic demo dataset")
    st.sidebar.caption("Change this on the **Home** page.")
