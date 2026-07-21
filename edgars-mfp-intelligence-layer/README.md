# Edgars MFP Intelligence Layer

A working implementation of the Merchandise Financial Planning (MFP) intelligence layer
described in Northlea Consulting's blueprint for Edgars: a localised demand-forecasting brain
sitting on top of Microsoft Dynamics 365 LS Central, driving three decision engines —
**Capital-Weighted Open-to-Buy**, **Predictive Markdown**, and **Dynamic Assortment** —
conditioned on a Zimbabwe macro signal layer (till currency-mix, parallel-rate pressure, school
terms, tobacco season).

**It runs on real data.** From the sidebar, upload your own flat-file extract (CSV or Parquet —
sales by store/category/date, stock on hand, unit cost & price, optionally till currency-mix and
a store-profile label) and every engine computes against it, exactly matching the blueprint's
Phase 1 ask: *"a secure, read-only historic extract delivered as a flat file... no IT integration
required."* No Edgars extract has been uploaded yet, so by default the app runs on a synthetic
demo dataset (27 stores across 5 local-economy profiles, 8 apparel categories, 104 weeks, fixed
random seed) shaped to the same schema, so the dashboard is fully explorable out of the box.

## Run it

```bash
pip install -r requirements.txt
streamlit run Home.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## Uploading your own data

In the sidebar, switch **Data source** to "My own uploaded extract" and upload a CSV or Parquet
file. Required columns (common header spellings are auto-detected — see `src/ingest.py`
`ALIASES` for the full list):

| Column | Meaning |
|---|---|
| `date` | Transaction or period date |
| `store_id` | Branch identifier |
| `category` | Merchandise category |
| `units_sold` | Units sold that row |
| `unit_cost`, `unit_price` | Per-unit cost and selling price |
| `stock_on_hand` | Stock on hand as of that row |

Optional but recommended: `usd_till_share` (till currency-mix, 0–1 or 0–100) powers the macro
signal layer; `store_profile` (a segment/region label) lets the Dynamic Assortment page compare
data-driven clusters against your existing static ranging. A "Download CSV template" button in
the sidebar gives a worked example. The sidebar reports rows used/dropped and flags which
optional signals are missing so you know exactly what the numbers are (and aren't) conditioned on.

Two things a sales-only extract can't provide, by nature of the data: **stock-out losses** need
an unconstrained-demand signal (sales alone are already censored by what was in stock), so that
figure reads $0 on real data; and the **parallel-rate premium** is a constructed proxy the
blueprint sources from external market data (USDT-P2P & FMCG indices) — without that feed
connected, it falls back to a same-signal proxy derived from your till-mix data alone.

## What's inside

| Path | What it does |
|---|---|
| `src/config.py` | Store profiles, categories, cost of capital, calendar constants |
| `src/data_gen.py` | Synthetic sales/stock/OTB/till-mix generator, with deliberate affinity mismatches and a couple of "drifted" branches |
| `src/ingest.py` | Parses and validates a real uploaded extract into the same internal shape as the synthetic generator |
| `src/loader.py` | Cached data/model loaders, keyed on the active data source so switching invalidates correctly |
| `src/sidebar.py` | The data-source picker (synthetic demo vs. upload) and per-page status indicator |
| `src/macro_signals.py` | The Zimbabwe Macro Signal Layer feature table and summaries |
| `src/forecast.py` | XGBoost demand forecast (macro-informed vs. naive baseline) |
| `src/engines/diagnostic.py` | Phase 1 Margin Leakage & Trapped Capital report |
| `src/engines/otb.py` | Capital-Weighted Open-to-Buy (RAROCE ranking) |
| `src/engines/markdown.py` | Predictive Markdown & inter-branch reallocation |
| `src/engines/assortment.py` | Dynamic branch micro-clustering for JAM |
| `Home.py` + `pages/` | The Streamlit dashboard |

## Notes on the synthetic demo data

- **Affinity mismatches** are baked into the data generator so that a flat, capital-agnostic
  buying process (today's naive baseline) produces genuine dead stock in some store-category
  pairs and genuine stock-outs in others — the exact failure mode the blueprint describes.
- **Two branches (S10, S21)** are deliberately "drifted": labelled under one static profile but
  behaving like another, so the Dynamic Assortment page has real drift to catch.
- **RAROCE figures are annualised** per the blueprint's formula, so they can look like large
  percentages given apparel margins and an 8-week holding period — treat them as a ranking
  signal, not a literal expected return. This applies to real data too.
- All dollar figures in demo mode are illustrative outputs of the simulation, not Edgars' actual
  financials.
