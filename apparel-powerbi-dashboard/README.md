# Apparel Power BI dashboard — Meridian Apparel Group

A complete, ready-to-build Power BI dashboard package for an apparel
**manufacturer and multi-chain retailer**: data model, sample data, DAX
measure library, and a page-by-page report design, covering Retail Trading
and Inventory as specified, plus suggested Finance, Credit/Financial
Services, and Manufacturing dashboards.

> **Why not a `.pbix` file?** Power BI Desktop is a Windows GUI application
> and isn't available in this environment, so a binary `.pbix` can't be
> authored or verified here. What's below is everything a `.pbix` would
> contain, in a form you can act on directly: real sample data, copy-paste
> DAX, and an exact build spec — importing it into Power BI Desktop is a
> Get Data + paste-measures exercise (roughly 30–60 minutes), not a design
> exercise. See "Build it" below.

## What's here

```
apparel-powerbi-dashboard/
├── data/
│   ├── generate_sample_data.py   # regenerates all 11 CSVs (seeded, reproducible)
│   └── csv/                       # ready-to-load sample dataset
├── model/
│   ├── data-model.md              # star schema, ERD, relationships, Power Query M
│   └── dax-measures.md            # every KPI as a copy-paste DAX measure
└── report/
    └── report-design.md           # page-by-page visuals, layout, drillthrough, nav
```

## KPI coverage

**Retail Trading**
- Store performance: $ turnover, basket value, UPT, by chain, by trading
  period, cash/credit split (value & %)
- Sales revenue per square metre

**Inventory**
- Stock turn · Sell-through · Markdown alerts & predictive clearance ·
  OTB tracker · OTIF · Supplier performance by sales · Product performance
  by Group / Department / Category

**Finance** (suggested) — P&L bridge, EBITDA & margin, budget variance,
working capital (DIO/DSO/DPO), cash conversion cycle.

**Credit / Financial Services** (suggested) — credit book balance, arrears
ageing (30/60/90+), bad-debt coverage, collections rate, interest income,
credit sales mix.

**Manufacturing** (suggested) — OEE (Availability x Performance x Quality),
production attainment, scrap/defect rate, cost per unit, on-time work
orders, make-vs-buy unit cost feeding the retail margin story.

Full rationale for the Finance/Credit/Manufacturing KPI choices is in
[`model/dax-measures.md`](model/dax-measures.md) sections 4–6.

## The business (fictional, for this demo)

**Meridian Apparel Group** — three retail chains (Meridian Fashion, a
department-store banner; Urban Basics, value; TinyThreads, kids specialist),
15 stores, two owned manufacturing plants making Menswear/Womenswear/
Kidswear, and eight external suppliers for Footwear, Sportswear, Home &
Textiles, Accessories, and School Uniforms. 8 departments, 40 SKUs, 104
weeks (2 trading years) of weekly history. All figures are synthetic.

## Build it

1. **Get the data.** `data/csv/` already has all 11 tables generated. To
   regenerate (e.g. after tweaking assumptions):
   ```bash
   cd data && pip install pandas numpy && python generate_sample_data.py
   ```
2. **Load into Power BI Desktop.** Get Data → Folder → point at `data/csv/`,
   or load each CSV individually. Set column types per the table in
   [`model/data-model.md`](model/data-model.md#power-query-m--loading-each-csv).
3. **Wire the model.** Build the relationships in
   [`model/data-model.md`](model/data-model.md#relationship-summary-set-these-in-model-view),
   including the two derived bridge tables (`Dim_Month`, and the
   trading-period key on `Dim_Date`) it walks through.
4. **Paste in the measures.** Create a blank `_Measures` table, then copy
   every DAX block from [`model/dax-measures.md`](model/dax-measures.md) in
   as a new measure (organise into display folders matching the doc's
   section headings).
5. **Build the pages.** Follow [`report/report-design.md`](report/report-design.md)
   page by page — it specifies visuals, fields, filters, conditional
   formatting, and drillthrough targets for all 12 pages, plus a suggested
   build order if you want a demoable dashboard after step 3 of the report
   build rather than waiting for all 12 pages.
6. **Swap in real data.** Once the shape is proven, point the same Power
   Query steps at a real extract (D365, SAP, a POS export — anything that
   can produce flat files with the same column names) and every measure and
   visual keeps working unchanged.

## Related work in this repository

[`../edgars-mfp-intelligence-layer/`](../edgars-mfp-intelligence-layer/) is a
Streamlit app doing merchandise financial planning (capital-weighted
Open-to-Buy, predictive markdown, dynamic assortment) for a similar apparel
retail domain. That project is a different tool for a different job — a
Python decision-engine app, not a BI dashboard — but its OTB and markdown
logic is a useful cross-reference if you want to push this Power BI model's
markdown/OTB measures toward genuinely predictive (not just rule-based)
scoring.
