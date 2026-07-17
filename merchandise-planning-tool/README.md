# Merchandise Planning & Buying Tool

A merchandise financial planning (MFP) dashboard that tracks the core KPIs a
buying/planning team lives in, plus an AI forecasting model that predicts
SKU-level demand and recommends what to buy.

- **Backend**: FastAPI + pandas + scikit-learn. Generates a deterministic
  2-year synthetic sales/inventory history for 19 SKUs across 6 categories,
  computes retail math KPIs, and trains a gradient-boosted demand forecaster
  per SKU.
- **Frontend**: React + TypeScript + Vite + Tailwind + Recharts. Three views:
  Overview (KPI dashboard), AI Buying (recommendation table), and per-product
  forecast detail.
- **Streamlit build** (`streamlit_app/`): the same three views as a single
  Python app, for quick internal sharing without standing up the API/React
  stack. Imports `backend/app/{data_gen,kpis,forecasting}.py` directly.

## KPIs tracked

| KPI | Formula |
|---|---|
| Sell-Through % | units sold / (beginning inventory + receipts) |
| Gross Margin % | gross margin $ / revenue $ |
| GMROI | gross margin $ (annualized) / average inventory at cost |
| Inventory Turnover | COGS (annualized) / average inventory at cost |
| Weeks of Supply | ending inventory units / trailing 4-wk avg weekly sales |
| Markdown % | (full-price revenue potential − actual revenue) / full-price potential |
| Sales Plan Variance | (actual units − planned units) / planned units |
| Stockout Rate | weeks demand exceeded on-hand inventory / total weeks |

## The AI model

For each SKU, `backend/app/forecasting.py`:

1. Builds calendar (seasonality), trend, and lag/rolling-sales features from
   weekly history.
2. Trains a `GradientBoostingRegressor`, blended 70/30 with a seasonal-naive
   baseline for robustness on short per-SKU series.
3. Backtests on the most recent 8 weeks to produce a WAPE accuracy score and
   a residual std (used for the forecast's 90% confidence band).
4. Retrains on full history and rolls forward recursively for a 12-week
   forecast.
5. Converts the forecast into an open-to-buy recommendation: forecasted
   demand over (lead time + reorder cycle) + safety stock − on-hand
   inventory, labeled Urgent Buy / Buy / On Track / Hold-Markdown based on
   current vs. target weeks of supply.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (Vite proxies `/api` to `http://localhost:8000`).

### Streamlit build

```bash
cd streamlit_app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`. No separate API process needed — it imports
the backend's data/KPI/forecasting modules in-process and caches the trained
models with `st.cache_resource`.

## Deploying the Streamlit app (Streamlit Community Cloud)

1. **Push this repo to GitHub** (already done if you're reading this from
   the repo). Streamlit Cloud deploys straight from a GitHub branch — no
   Dockerfile or build config needed.
2. **Go to [share.streamlit.io](https://share.streamlit.io)** and sign in
   with GitHub. Authorize Streamlit to access this repository (or your fork)
   if prompted.
3. Click **"New app"** → **"Deploy a public app from GitHub"** (or "From
   existing repo") and fill in:
   - **Repository**: `CarringtonBusili/CarringtonBusili`
   - **Branch**: the branch you want live (e.g. `main`, or this feature
     branch)
   - **Main file path**: `merchandise-planning-tool/streamlit_app/app.py`
   - App URL: pick a subdomain, e.g. `merch-planning-buying`
4. **Dependencies**: Streamlit Cloud auto-installs from the
   `requirements.txt` in the same folder as the main file
   (`streamlit_app/requirements.txt`) — nothing else to configure. If you
   need a specific Python version, add a `runtime.txt` (e.g. `3.11`) next to
   `app.py`, or set it under "Advanced settings" before deploying.
5. Click **Deploy**. First boot takes longer than usual — it's not just
   installing packages, it's also running the app once to simulate the
   2-year history and train the 19 per-SKU forecast models
   (`st.cache_resource`, so this only happens on cold start / after a
   reboot, not per user session).
6. **Managing it afterward** (via the app's "⋮" menu on share.streamlit.io):
   - **Reboot app** — clears the cache and re-trains, e.g. after pushing new
     commits (Streamlit Cloud also auto-redeploys on push to the tracked
     branch).
   - **Logs** — for debugging a failed boot or exception.
   - **Settings → Secrets** — not needed here (no API keys or credentials
     used), but this is where `st.secrets` values would go if added later.
   - **Delete app** — tears it down and frees the subdomain.
7. No separate backend deploy is needed for this build — `streamlit_app/`
   imports `backend/app/` directly from the same repo checkout, so a single
   Streamlit Cloud app is the whole deployment.

**Pinned versions matter here**: `streamlit_app/requirements.txt` pins
`streamlit==1.59.2`. Streamlit's dataframe/chart rendering depends on a
matching `pyarrow` build; leaving `streamlit` on an old pin while `pyarrow`
resolves to whatever's newest at install time can crash the app's Python
process outright (this happened during development — traced to
`streamlit==1.38.0` against an unpinned, much newer `pyarrow`). If you bump
`streamlit`, let `pip` re-resolve `pyarrow` rather than pinning it
separately.

## API endpoints

- `GET /api/kpis/summary?period_weeks=13`
- `GET /api/kpis/by-category?period_weeks=13`
- `GET /api/kpis/trend?weeks=26&category=Denim`
- `GET /api/products` / `GET /api/products/{id}`
- `GET /api/products/{id}/forecast`
- `GET /api/buying/recommendations?category=&action=`
- `GET /api/buying/summary`
