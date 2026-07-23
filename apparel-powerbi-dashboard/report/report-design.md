# Report design — Meridian Apparel Group dashboard

Page-by-page blueprint for the Power BI report built on top of
[`../model/data-model.md`](../model/data-model.md) and
[`../model/dax-measures.md`](../model/dax-measures.md). Layout is written as
zones (top/left/centre/right) rather than pixel coordinates — lay it out on a
1280x720 canvas (Power BI's default 16:9) and it translates directly.

## Navigation & shell (applies to every page)

- **Top band**: report title, a chain logo/segmented button `[All chains |
  Meridian Fashion | Urban Basics | TinyThreads]` bound to `Dim_Store[chain_name]`,
  and a page-navigator (buttons, not tabs, so mobile behaves) across the 11
  pages grouped into four sections: **Retail Trading**, **Inventory**,
  **Finance & Credit**, **Manufacturing**.
- **Left rail slicers** (sync'd across all Retail Trading + Inventory pages
  via **Sync slicers**): Trading Year, Trading Period, Chain, Region,
  Department. Finance/Credit pages use their own Calendar Year/Month slicer
  pair (different grain — see the data model's note on `Dim_Month`).
- **Date-range bookmarks**: four buttons — *This Period*, *This Trading Year*,
  *Last Trading Year*, *L4W* — each a bookmark that sets the Trading
  Period/Year slicers, for one-click period switching without hunting through
  a slicer list.
- **Colour system**: one categorical palette for the three chains (used
  consistently on every chain-coloured visual), a single accent colour for
  "the number", greys for comparison/prior-period series, and a 3-colour
  traffic-light scale (green/amber/red) reserved *only* for alert/status
  visuals (Markdown Signal, OTIF, arrears) so red always means "needs
  attention" and never just "a category".

---

## Section: Retail Trading

### 1. Executive Overview

Purpose: one-screen answer to "how is the business trading right now."

| Zone | Visual | Fields |
|---|---|---|
| Top KPI strip | 6 KPI cards w/ sparkline + vs. LY (%) | Net Sales Value, Gross Margin %, Sales Revenue per Sqm, Stock Turn, OTIF %, EBITDA Margin % |
| Centre-left | Line chart, Net Sales Value by week | `Dim_Date[week_start]` axis, split by `chain_name` |
| Centre-right | Donut, Cash vs Credit Sales Value | `Cash Sales Value` / `Credit Sales Value` |
| Bottom-left | Bar, Net Sales Value by Department | sorted descending |
| Bottom-right | Table, Chain scorecard | Chain, Turnover, GM%, Sales/Sqm, Stock Turn, OTIF% — conditional formatting (data bars) on each column |

### 2. Store Performance

Purpose: the brief's core ask — turnover, basket, size, chain, trading
period, cash/credit split, all in one place.

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Net Sales Value, Average Basket Value, Units Per Transaction, Cash Sales %, Credit Sales % |
| Left | Matrix, Store x Trading Period | Rows: `chain_name` > `store_name`; Columns: `trading_period`; Values: `Net Sales Value`, conditional-formatted heatmap |
| Centre | Clustered column, Turnover by Chain by Trading Period | axis: trading_period, legend: chain_name |
| Right | Stacked bar (100%), Cash vs Credit % by Store | axis: store_name, values: Cash Sales %, Credit Sales % |
| Bottom | Scatter, Basket Value vs UPT by store | X: Average Basket Value, Y: UPT, size: Net Sales Value, colour: chain_name, tooltip: store_name — flags stores winning on basket vs. on traffic |
| Slicer | Store Format, Region | in addition to the shared left rail |
| Drillthrough | right-click a store → **Store Detail** page (below) |

### 3. Store Detail (drillthrough)

Single-store deep dive: KPI cards (Turnover, Basket, UPT, Sales/Sqm, Cash%),
weekly trend line, department mix donut, top 10 SKUs table, cash/credit trend
over time. Reached via drillthrough from Store Performance, Executive
Overview chain table, and the Sales-per-Sqm page.

### 4. Sales Revenue per Sqm

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI card + gauge | Sales Revenue per Sqm (Annualised), target line at group average |
| Left | Bar, Sales/Sqm by Store, sorted descending | colour by chain |
| Right | Scatter, Size (sqm) vs Turnover | X: `size_sqm`, Y: `Net Sales Value`, size: Sales/Sqm — bubble far below the trend line = underperforming for its footprint |
| Bottom | Table | Store, Size (sqm), Turnover, Sales/Sqm, Rank, vs. Chain Average % |

---

## Section: Inventory

### 5. Inventory Health (Stock Turn & Sell-Through)

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Stock Turn (Annualised), Sell-Through %, Closing Stock (Cost), Avg Stock Age (Weeks) |
| Left | Line, Stock Turn trend by Department | monthly/period trend, one line per department |
| Centre | Bar, Sell-Through % by Category | sorted, reference line at target (e.g. 80%) |
| Right | Heatmap matrix, Weeks of Cover | rows: department, columns: store — colour scale, dark = overstocked |
| Bottom | Table, worst 15 SKUs by Stock Turn | SKU, Department, Stock Turn, Sell-Through %, Closing Stock (Units) |

### 6. Markdown & Clearance

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Discount Value, Markdown Rate %, count of "🔴 Markdown now" items |
| Left | Table/matrix, Markdown watchlist | Store, SKU, `Markdown Signal`, Predicted Weeks to Clear, Sell-Through %, Avg Stock Age — conditional formatting (icon set) on `Markdown Signal`, sorted worst-first |
| Right | Bar, Markdown $ impact by Department | Discount Value by department, current vs. prior period |
| Bottom | Trend, Markdown Rate % over time | by chain |
| Interaction | Clicking a watchlist row cross-filters the Markdown $ chart to that SKU's history |

### 7. OTB Tracker

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Open-to-Buy $, Planned Receipts Cost, OTB Committed % |
| Left | Waterfall, OTB bridge | Opening Stock → + Planned Receipts → − Planned Sales → − Planned Markdown → Planned Closing Stock |
| Centre | Matrix, OTB by Chain x Department x Trading Period | Values: Open-to-Buy $, conditional formatting |
| Right | Bar, Committed vs. Open receipts | stacked, by department |
| Slicer | Trading Period (single-select, since OTB is inherently period-based, not a range) |

### 8. Supplier & OTIF Performance

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | OTIF %, On-Time %, In-Full %, Average Delivery Delay (Days) |
| Left | Bar, OTIF % by Supplier | sorted descending, reference line at target (e.g. 95%) |
| Centre | Scatter, Supplier scorecard | X: Net Sales Value, Y: OTIF %, size: PO Value (Ordered), colour: supplier_type (Internal/External) |
| Right | Table, Supplier detail | Supplier, Type, Net Sales Value, Sell-Through %, OTIF %, Avg Delivery Delay, Supplier Rank by Sales |
| Bottom | Trend, OTIF % over trading period | by supplier_type — shows whether internal plants consistently outperform external suppliers |
| Drillthrough | supplier → PO-level table (order/promised/actual dates, flags) |

### 9. Product Performance (Group / Department / Category)

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Net Sales Value, Gross Margin %, Sell-Through %, Category Rank leaders |
| Left | Decomposition tree or drillable matrix | `product_group` → `department` → `category`, measure: Net Sales Value |
| Centre | Bar, Top/Bottom 10 SKUs by Sales | two side-by-side bars |
| Right | Scatter, Margin vs Sell-Through by category | X: Sell-Through %, Y: Gross Margin %, size: Net Sales Value, quadrant lines at group medians — identifies "fix the price" vs "fix the buy" categories |
| Bottom | Table | full department/category grid with Sales Mix %, sortable |

---

## Section: Finance & Credit

### 10. Finance & Profitability

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Revenue, EBITDA, EBITDA Margin %, Revenue Variance to Budget % |
| Left | Waterfall, P&L bridge | Revenue → − COGS → Gross Margin → − OpEx → EBITDA |
| Centre | Combo chart, Actual vs Budget | bars: Revenue/EBITDA actual, line: budget, by month |
| Right | KPI cards, working capital | Inventory Days, Debtor Days, Creditor Days, Cash Conversion Cycle |
| Bottom | Bar, EBITDA by Chain | with budget variance as a data label |
| Slicer | Calendar Year / Month (this page's own pair, monthly grain via `Dim_Month`) |

### 11. Credit / Financial Services

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | Credit Book Balance (EoP), Arrears % of Book, Bad Debt Coverage %, Credit Sales % of Total Sales |
| Left | Stacked bar, Arrears ageing | Arrears 30 / 60 / 90+ by chain |
| Centre | Line, Book balance trend | Credit Book Balance (EoP) over time, by chain |
| Right | KPI cards | Active Accounts, New Accounts Opened, Collections Rate %, Interest Income |
| Bottom | Table | Chain, Book Balance, Arrears %, Bad Debt Provision, Collections Rate % |
| Alert | conditional formatting on Arrears 90+ % — red above a policy threshold (e.g. 5%) |

---

## Section: Manufacturing

### 12. Manufacturing Operations

| Zone | Visual | Fields |
|---|---|---|
| Top | KPI cards | OEE %, Production Attainment %, Defect Rate %, Cost per Unit Produced |
| Left | Gauge or bullet, OEE % | with Availability/Performance/Quality broken out as three mini bars underneath |
| Centre | Line, Output vs Plan | Actual Units Produced vs Planned Units, weekly, by plant |
| Right | Bar, Downtime Hours by reason-proxy (department) | (extend the fact with a downtime-reason column if the real source system captures it) |
| Bottom-left | Table, Work order on-time % by plant/department | On-Time Work Order %, Units per Labor Hour |
| Bottom-right | Bar, Make vs Buy unit cost | Avg Unit Cost – Own Manufacture vs – External, by department, feeding the retail margin story on the Product Performance page |

---

## Drillthrough pages

| Drillthrough page | Reached from | Filters received |
|---|---|---|
| Store Detail | Store Performance, Executive Overview, Sales/Sqm | `store_id` |
| Product Detail | Product Performance, Markdown & Clearance | `product_id` |
| Supplier Detail (PO list) | Supplier & OTIF Performance | `supplier_id` |

Each drillthrough page needs the standard **Back** button (Power BI inserts
one automatically) and should *not* inherit the page-level slicers — use the
default "keep all filters" only for the entity being drilled into.

## Mobile layout

Build a mobile layout (View → Mobile Layout) for at minimum the Executive
Overview and Markdown & Clearance pages — those two are the ones a buyer or
store ops manager actually needs on a phone between meetings. Stack KPI cards
vertically, drop the scatter/heatmap visuals (illegible at phone width), keep
the tables.

## Build order

If building incrementally, this order gets a demoable dashboard fastest and
matches how the KPIs build on each other:

1. Executive Overview + Store Performance (proves the model and cash/credit
   split work)
2. Inventory Health + Markdown & Clearance (proves `Fact_Inventory` and the
   sell-through/stock-turn measures)
3. OTB Tracker + Supplier & OTIF Performance
4. Product Performance
5. Finance & Profitability + Credit
6. Manufacturing Operations
7. Drillthrough pages + mobile layout last, once the page set is stable
