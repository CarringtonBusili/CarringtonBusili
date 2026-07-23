# DAX measure library — Meridian Apparel Group dashboard

All measures below assume the tables, columns, and relationships in
[`data-model.md`](./data-model.md). Organise them in Power BI as a display
folder per section heading (right-click each measure → **Home Table** /
**Display Folder**) so the field list stays navigable.

Create every measure in a dedicated blank **`_Measures`** table (Modelling →
New Table → `_Measures = {1}`, then hide the column) rather than scattering
them across the fact tables — keeps the field list clean and matches how
you'll want to hand this model off.

## A note on time intelligence

`Dim_Date` is a **weekly** trading calendar (one row per week-start), not a
daily calendar, because the brief asks for "trading period" reporting — real
apparel retailers compare Period 5 this trading year to Period 5 last trading
year, not calendar-date `SAMEPERIODLASTYEAR`. Built-in DAX time-intelligence
functions (`SAMEPERIODLASTYEAR`, `TOTALYTD`, `DATEADD`) require a contiguous
**daily** date table to behave correctly, so this model deliberately doesn't
use them. Instead, comparisons use `Dim_Date[week_num]` — a simple sequential
integer (1…104) already in the sample data — which makes "same trading week,
prior trading year" a plain filter, no daily grain required. If you later
add a real daily `Dim_Date` for calendar reporting, keep it as a second,
separate date table (star schema per subject area) rather than retrofitting
weekly facts onto it.

```dax
Current Week Num = MAX ( Dim_Date[week_num] )

Weeks In Period = DISTINCTCOUNT ( Dim_Date[date_key] )
```

---

## 1 · Retail trading — store performance

```dax
Total Units Sold =
SUM ( Fact_Sales[units_sold] )

Gross Sales Value =
SUM ( Fact_Sales[gross_sales_value] )

-- "Turnover" = net of markdown/discount, the headline retail KPI
Net Sales Value =
SUM ( Fact_Sales[net_sales_value] )

COGS =
SUM ( Fact_Sales[cogs_value] )

Gross Margin $ =
[Net Sales Value] - [COGS]

Gross Margin % =
DIVIDE ( [Gross Margin $], [Net Sales Value] )
```

### Cash vs. credit split (value and %)

```dax
Cash Sales Value =
SUM ( Fact_Sales[cash_sales_value] )

Credit Sales Value =
SUM ( Fact_Sales[credit_sales_value] )

Cash Sales % =
DIVIDE ( [Cash Sales Value], [Net Sales Value] )

Credit Sales % =
DIVIDE ( [Credit Sales Value], [Net Sales Value] )
```
Use `Cash Sales Value` / `Credit Sales Value` as a stacked bar for the
**value** split, and `Cash Sales %` / `Credit Sales %` (or a single measure
returning both via a disconnected "Tender" slicer table) for the **%** view.

### Basket / UPT

```dax
Total Transactions =
SUM ( Fact_Sales[cash_transactions] ) + SUM ( Fact_Sales[credit_transactions] )

Average Basket Value =
DIVIDE ( [Net Sales Value], [Total Transactions] )

Units Per Transaction (UPT) =
DIVIDE ( [Total Units Sold], [Total Transactions] )
```

### Store / chain ranking and prior-period comparison

```dax
Store Rank by Turnover =
RANKX ( ALL ( Dim_Store[store_name] ), [Net Sales Value], , DESC )

Net Sales Value PY (same trading week) =
VAR CurrentWeek = [Current Week Num]
RETURN
    CALCULATE (
        [Net Sales Value],
        FILTER ( ALL ( Dim_Date ), Dim_Date[week_num] = CurrentWeek - 52 )
    )

Net Sales Value YoY % =
DIVIDE ( [Net Sales Value] - [Net Sales Value PY (same trading week)], [Net Sales Value PY (same trading week)] )
```

## 2 · Sales revenue per square metre

```dax
Selling Area (sqm) =
SUM ( Dim_Store[size_sqm] )

Sales Revenue per Sqm =
DIVIDE ( [Net Sales Value], [Selling Area (sqm)] )

-- annualised, so a single trading period's sqm productivity is comparable
-- to a full-year figure regardless of how many weeks are in the filter
Sales Revenue per Sqm (Annualised) =
DIVIDE ( [Net Sales Value], [Selling Area (sqm)] ) * DIVIDE ( 52, [Weeks In Period] )
```

## 3 · Inventory

### Stock levels

```dax
-- point-in-time snapshot as of the last week in the current filter
Closing Stock (Units) =
CALCULATE ( SUM ( Fact_Inventory[stock_on_hand_units] ), LASTDATE ( Dim_Date[date_key] ) )

Closing Stock (Cost) =
CALCULATE ( SUM ( Fact_Inventory[stock_on_hand_cost] ), LASTDATE ( Dim_Date[date_key] ) )

Closing Stock (Retail) =
CALCULATE ( SUM ( Fact_Inventory[stock_on_hand_retail] ), LASTDATE ( Dim_Date[date_key] ) )

-- average of weekly closing stock across the filtered weeks — the
-- conventional denominator for stock turn
Average Stock on Hand (Cost) =
AVERAGEX ( VALUES ( Dim_Date[date_key] ), CALCULATE ( SUM ( Fact_Inventory[stock_on_hand_cost] ) ) )
```

### Stock turn

```dax
-- COGS / average inventory at cost, annualised to the 52-trading-week year
Stock Turn (Annualised) =
DIVIDE ( [COGS], [Average Stock on Hand (Cost)] ) * DIVIDE ( 52, [Weeks In Period] )
```

### Sell-through

```dax
-- % of total available stock (cumulative units sold + what's still on hand)
-- that has sold — the standard practical sell-through read for a period or
-- season-to-date view
Units Received =
SUM ( Fact_Inventory[units_received] )

Sell-Through % =
DIVIDE ( [Total Units Sold], [Total Units Sold] + [Closing Stock (Units)] )
```

### Markdown alerts and predictive markdown

```dax
Discount Value =
SUM ( Fact_Sales[discount_value] )

Markdown Rate % =
DIVIDE ( [Discount Value], [Gross Sales Value] )

-- stock-weighted average age, in weeks, of stock currently on hand
Avg Stock Age (Weeks) =
DIVIDE (
    SUMX ( Fact_Inventory, Fact_Inventory[stock_age_weeks] * Fact_Inventory[stock_on_hand_units] ),
    SUM ( Fact_Inventory[stock_on_hand_units] )
)

-- weeks of cover at the period's average sell rate
Weeks of Cover =
DIVIDE ( [Closing Stock (Units)], DIVIDE ( [Total Units Sold], [Weeks In Period] ) )

-- predictive: weeks-of-cover using only the last 4 weeks' sell rate, so a
-- slowing item gets flagged before the season-to-date average catches up
Units Sold L4W =
VAR CurrentWeek = [Current Week Num]
RETURN
    CALCULATE (
        [Total Units Sold],
        FILTER ( ALL ( Dim_Date ), Dim_Date[week_num] > CurrentWeek - 4 && Dim_Date[week_num] <= CurrentWeek )
    )

Predicted Weeks to Clear (L4W run-rate) =
DIVIDE ( [Closing Stock (Units)], DIVIDE ( [Units Sold L4W], 4 ) )

-- traffic-light alert, driven by stock cover + how much of it has sold —
-- tune the thresholds to the business's actual markdown policy
Markdown Signal =
VAR WksCover   = [Predicted Weeks to Clear (L4W run-rate)]
VAR SellThru   = [Sell-Through %]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( WksCover ), "n/a",
        WksCover > 12 && SellThru < 0.35, "🔴 Markdown now",
        WksCover > 8  && SellThru < 0.50, "🟠 Markdown watch",
        "🟢 Healthy"
    )
```
Drop `Markdown Signal` into a table/matrix of Store x Product with
`Predicted Weeks to Clear`, `Sell-Through %`, and `Avg Stock Age (Weeks)` as
supporting columns, then conditional-format the signal column — that's the
"markdown alerts" view. It doubles as the shortlist feeding a manual or
Power Automate markdown-approval workflow.

### OTB tracker

```dax
Opening Stock Cost (OTB) =
SUM ( Fact_OTB[opening_stock_cost] )

Planned Sales Cost =
SUM ( Fact_OTB[planned_sales_cost] )

Planned Markdown Cost =
SUM ( Fact_OTB[planned_markdown_cost] )

Planned Receipts Cost =
SUM ( Fact_OTB[planned_receipts_cost] )

Committed Receipts Cost =
SUM ( Fact_OTB[committed_receipts_cost] )

Planned Closing Stock Cost =
SUM ( Fact_OTB[planned_closing_stock_cost] )

-- Open-to-Buy = Planned Receipts − Receipts Already Committed (on order)
Open-to-Buy $ =
SUM ( Fact_OTB[otb_value] )

OTB Committed % =
DIVIDE ( [Committed Receipts Cost], [Planned Receipts Cost] )
```

### OTIF (On Time In Full)

```dax
PO Count =
COUNTROWS ( Fact_PurchaseOrders )

On-Time PO Count =
CALCULATE ( COUNTROWS ( Fact_PurchaseOrders ), Fact_PurchaseOrders[on_time_flag] = TRUE )

In-Full PO Count =
CALCULATE ( COUNTROWS ( Fact_PurchaseOrders ), Fact_PurchaseOrders[in_full_flag] = TRUE )

OTIF PO Count =
CALCULATE ( COUNTROWS ( Fact_PurchaseOrders ), Fact_PurchaseOrders[otif_flag] = TRUE )

On-Time % =
DIVIDE ( [On-Time PO Count], [PO Count] )

In-Full % =
DIVIDE ( [In-Full PO Count], [PO Count] )

OTIF % =
DIVIDE ( [OTIF PO Count], [PO Count] )

Average Delivery Delay (Days) =
AVERAGEX (
    Fact_PurchaseOrders,
    DATEDIFF ( Fact_PurchaseOrders[promised_date], Fact_PurchaseOrders[actual_delivery_date], DAY )
)

PO Value (Ordered) =
SUM ( Fact_PurchaseOrders[ordered_cost] )
```

### Supplier performance by sales

Because `Dim_Product` relates to `Dim_Supplier` on `supplier_id`, every sales
measure above already slices correctly by supplier once you drop
`Dim_Supplier[supplier_name]` on a visual — no new measures needed for the
$ view. Add these for a supplier scorecard:

```dax
Supplier Rank by Sales =
RANKX ( ALL ( Dim_Supplier[supplier_name] ), [Net Sales Value], , DESC )

-- blends the "sales" ask with delivery reliability into one sortable score
Supplier Scorecard Index =
VAR SalesShare = DIVIDE ( [Net Sales Value], CALCULATE ( [Net Sales Value], ALL ( Dim_Supplier ) ) )
RETURN
    ( SalesShare * 0.5 ) + ( [OTIF %] * 0.3 ) + ( [Sell-Through %] * 0.2 )
```
A supplier table with `Net Sales Value`, `Sell-Through %`, `OTIF %`, and
`Average Delivery Delay (Days)` side by side is the standard supplier
scorecard view.

### Product performance by group / department / category

No new measures required — build a matrix using the
`Dim_Product[product_group] > [department] > [category]` hierarchy on rows
and `Net Sales Value`, `Gross Margin %`, `Total Units Sold`, `Sell-Through %`
on columns. Add:

```dax
Category Rank by Sales =
RANKX ( ALL ( Dim_Product[category] ), [Net Sales Value], , DESC )

Sales Mix % (within Department) =
DIVIDE ( [Net Sales Value], CALCULATE ( [Net Sales Value], ALL ( Dim_Product[category] ) ) )
```

---

## 4 · Finance (suggested)

```dax
Revenue =
SUM ( Fact_Finance[revenue] )

COGS (Finance) =
SUM ( Fact_Finance[cogs] )

Gross Margin $ (Finance) =
SUM ( Fact_Finance[gross_margin] )

Gross Margin % (Finance) =
DIVIDE ( [Gross Margin $ (Finance)], [Revenue] )

OpEx =
SUM ( Fact_Finance[opex] )

EBITDA =
SUM ( Fact_Finance[ebitda] )

EBITDA Margin % =
DIVIDE ( [EBITDA], [Revenue] )

Budget Revenue =
SUM ( Fact_Finance[budget_revenue] )

Revenue Variance to Budget % =
DIVIDE ( [Revenue] - [Budget Revenue], [Budget Revenue] )

Budget EBITDA =
SUM ( Fact_Finance[budget_ebitda] )

EBITDA Variance to Budget $ =
[EBITDA] - [Budget EBITDA]
```

### Working capital

```dax
Months In Period =
COUNTROWS ( SUMMARIZE ( Fact_Finance, Fact_Finance[calendar_year], Fact_Finance[calendar_month] ) )

Avg Inventory Value =
AVERAGEX (
    SUMMARIZE ( Fact_Finance, Fact_Finance[calendar_year], Fact_Finance[calendar_month] ),
    CALCULATE ( SUM ( Fact_Finance[inventory_value] ) )
)

Avg Debtors Balance =
AVERAGEX (
    SUMMARIZE ( Fact_Finance, Fact_Finance[calendar_year], Fact_Finance[calendar_month] ),
    CALCULATE ( SUM ( Fact_Finance[debtors_balance] ) )
)

Avg Creditors Balance =
AVERAGEX (
    SUMMARIZE ( Fact_Finance, Fact_Finance[calendar_year], Fact_Finance[calendar_month] ),
    CALCULATE ( SUM ( Fact_Finance[creditors_balance] ) )
)

Inventory Days (DIO) =
DIVIDE ( [Avg Inventory Value], [COGS (Finance)] ) * ( [Months In Period] * 30.4 )

Debtor Days (DSO) =
DIVIDE ( [Avg Debtors Balance], [Revenue] ) * ( [Months In Period] * 30.4 )

Creditor Days (DPO) =
DIVIDE ( [Avg Creditors Balance], [COGS (Finance)] ) * ( [Months In Period] * 30.4 )

Cash Conversion Cycle (Days) =
[Inventory Days (DIO)] + [Debtor Days (DSO)] - [Creditor Days (DPO)]
```

## 5 · Credit / financial services (suggested)

```dax
Credit Sales (Book) =
SUM ( Fact_Credit[credit_sales] )

Collections =
SUM ( Fact_Credit[collections] )

Write-Offs =
SUM ( Fact_Credit[write_offs] )

-- point-in-time balance: latest month in the current filter, not a sum
-- across months (a balance is a stock, not a flow)
Credit Book Balance (EoP) =
CALCULATE ( SUM ( Fact_Credit[closing_balance] ), LASTDATE ( Dim_Month[month_start_date] ) )

Active Accounts (EoP) =
CALCULATE ( SUM ( Fact_Credit[active_accounts] ), LASTDATE ( Dim_Month[month_start_date] ) )

New Accounts Opened =
SUM ( Fact_Credit[new_accounts] )

Total Arrears =
SUM ( Fact_Credit[arrears_30] ) + SUM ( Fact_Credit[arrears_60] ) + SUM ( Fact_Credit[arrears_90plus] )

Arrears % of Book =
DIVIDE ( [Total Arrears], [Credit Book Balance (EoP)] )

Arrears 90+ % of Book =
DIVIDE ( SUM ( Fact_Credit[arrears_90plus] ), [Credit Book Balance (EoP)] )

Bad Debt Provision =
CALCULATE ( SUM ( Fact_Credit[bad_debt_provision] ), LASTDATE ( Dim_Month[month_start_date] ) )

Bad Debt Coverage % =
DIVIDE ( [Bad Debt Provision], [Total Arrears] )

Interest Income =
SUM ( Fact_Credit[interest_income] )

Credit Sales % of Total Sales =
DIVIDE ( [Credit Sales (Book)], [Revenue] )

Collections Rate % =
VAR OpeningBalance = SUM ( Fact_Credit[opening_balance] )
RETURN
    DIVIDE ( [Collections], OpeningBalance + [Credit Sales (Book)] )
```

## 6 · Manufacturing (suggested)

```dax
Planned Units =
SUM ( Fact_Manufacturing[planned_units] )

Actual Units Produced =
SUM ( Fact_Manufacturing[actual_units_produced] )

Good Units =
SUM ( Fact_Manufacturing[good_units] )

Defect Units =
SUM ( Fact_Manufacturing[defect_units] )

Scrap Units =
SUM ( Fact_Manufacturing[scrap_units] )

Production Attainment % =
DIVIDE ( [Actual Units Produced], [Planned Units] )

Defect Rate % =
DIVIDE ( [Defect Units], [Actual Units Produced] )

Scrap Rate % =
DIVIDE ( [Scrap Units], [Actual Units Produced] )
```

### OEE — Overall Equipment Effectiveness

```dax
Available Hours =
SUM ( Fact_Manufacturing[available_hours] )

Downtime Hours =
SUM ( Fact_Manufacturing[downtime_hours] )

Availability % =
DIVIDE ( [Available Hours] - [Downtime Hours], [Available Hours] )

-- approximation: actual output against what plan implies for the hours
-- actually run — swap in a true ideal-run-rate figure if the plant tracks one
Performance % =
MIN ( 1, DIVIDE ( [Actual Units Produced], [Planned Units] * [Availability %] ) )

Quality % =
DIVIDE ( [Good Units], [Actual Units Produced] )

OEE % =
[Availability %] * [Performance %] * [Quality %]
```

### Cost and labour

```dax
Manufacturing Cost Total =
SUM ( Fact_Manufacturing[manufacturing_cost_total] )

Cost per Unit Produced =
DIVIDE ( [Manufacturing Cost Total], [Actual Units Produced] )

Labor Hours =
SUM ( Fact_Manufacturing[labor_hours] )

Units per Labor Hour =
DIVIDE ( [Actual Units Produced], [Labor Hours] )

On-Time Work Order % =
DIVIDE (
    CALCULATE ( COUNTROWS ( Fact_Manufacturing ), Fact_Manufacturing[on_time_completion_flag] = TRUE ),
    COUNTROWS ( Fact_Manufacturing )
)
```

### Make vs. buy

```dax
Avg Unit Cost – Own Manufacture =
CALCULATE ( AVERAGE ( Dim_Product[unit_cost] ), Dim_Product[source_type] = "Own Manufacture" )

Avg Unit Cost – External =
CALCULATE ( AVERAGE ( Dim_Product[unit_cost] ), Dim_Product[source_type] = "External" )

Own-Manufacture Sales Mix % =
DIVIDE (
    CALCULATE ( [Net Sales Value], Dim_Product[source_type] = "Own Manufacture" ),
    [Net Sales Value]
)
```
Pairs the plant-floor OEE/cost story with the retail margin it ultimately
funds — own-manufactured departments (Menswear, Womenswear, Kidswear) should
show a materially better `Gross Margin %` than bought-in departments; this
measure is what makes that comparison a one-visual story.
