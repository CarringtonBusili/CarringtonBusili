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

## API endpoints

- `GET /api/kpis/summary?period_weeks=13`
- `GET /api/kpis/by-category?period_weeks=13`
- `GET /api/kpis/trend?weeks=26&category=Denim`
- `GET /api/products` / `GET /api/products/{id}`
- `GET /api/products/{id}/forecast`
- `GET /api/buying/recommendations?category=&action=`
- `GET /api/buying/summary`
