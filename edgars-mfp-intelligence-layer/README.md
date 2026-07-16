# Edgars MFP Intelligence Layer — Simulation

A working simulation of the Merchandise Financial Planning (MFP) intelligence layer described
in Northlea Consulting's blueprint for Edgars: a localised demand-forecasting brain sitting on
top of Microsoft Dynamics 365 LS Central, driving three decision engines — **Capital-Weighted
Open-to-Buy**, **Predictive Markdown**, and **Dynamic Assortment** — conditioned on a Zimbabwe
macro signal layer (till currency-mix, parallel-rate pressure, school terms, tobacco season).

No real Edgars/D365 extract exists for this project, so a synthetic dataset (27 stores across
5 local-economy profiles, 8 apparel categories, 104 weeks of history, fixed random seed) stands
in for the flat-file extract Phase 1 of the blueprint calls for. Every engine here is fully
functional against that data — it's the same code that would run against a real Phase 1 export.

## Run it

```bash
pip install -r requirements.txt
streamlit run Home.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## What's inside

| Path | What it does |
|---|---|
| `src/config.py` | Store profiles, categories, cost of capital, calendar constants |
| `src/data_gen.py` | Synthetic sales/stock/OTB/till-mix generator, with deliberate affinity mismatches and a couple of "drifted" branches |
| `src/macro_signals.py` | The Zimbabwe Macro Signal Layer feature table and summaries |
| `src/forecast.py` | XGBoost demand forecast (macro-informed vs. naive baseline) |
| `src/engines/diagnostic.py` | Phase 1 Margin Leakage & Trapped Capital report |
| `src/engines/otb.py` | Capital-Weighted Open-to-Buy (RAROCE ranking) |
| `src/engines/markdown.py` | Predictive Markdown & inter-branch reallocation |
| `src/engines/assortment.py` | Dynamic branch micro-clustering for JAM |
| `Home.py` + `pages/` | The Streamlit dashboard |

## Notes on the simulation

- **Affinity mismatches** are baked into the data generator so that a flat, capital-agnostic
  buying process (today's naive baseline) produces genuine dead stock in some store-category
  pairs and genuine stock-outs in others — the exact failure mode the blueprint describes.
- **Two branches (S10, S21)** are deliberately "drifted": labelled under one static profile but
  behaving like another, so the Dynamic Assortment page has real drift to catch.
- **RAROCE figures are annualised** per the blueprint's formula, so they can look like large
  percentages given apparel margins and an 8-week holding period — treat them as a ranking
  signal, not a literal expected return.
- All dollar figures are illustrative outputs of the simulation, not Edgars' actual financials.
