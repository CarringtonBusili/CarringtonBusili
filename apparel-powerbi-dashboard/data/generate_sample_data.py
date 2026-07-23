"""
Synthetic data generator for the Meridian Apparel Group Power BI dashboard.

Meridian is a fictional, vertically integrated apparel manufacturer and
multi-chain retailer used purely to give the Power BI star schema (see
../model/data-model.md) something realistic to load and the DAX measure
library (../model/dax-measures.md) something to compute against. No real
company's financials are represented.

Produces one CSV per dimension/fact table into ./csv, ready to be loaded
into Power BI via Get Data > Text/CSV or Get Data > Folder. Everything is
derived from a fixed RANDOM_SEED so the output is reproducible.

Run:
    pip install pandas numpy
    python generate_sample_data.py
"""
import os

import numpy as np
import pandas as pd

RANDOM_SEED = 42
OUT_DIR = os.path.join(os.path.dirname(__file__), "csv")

HISTORY_START = pd.Timestamp("2024-07-01")  # first trading week (Monday)
N_WEEKS = 104  # 2 trading years


def rng():
    return np.random.default_rng(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Dim_Date — weekly trading calendar (13 trading periods x 4 weeks per year)
# ---------------------------------------------------------------------------
def build_dim_date() -> pd.DataFrame:
    weeks = pd.date_range(HISTORY_START, periods=N_WEEKS, freq="W-MON")
    rows = []
    for i, wk in enumerate(weeks):
        trading_year = 1 + i // 52
        week_in_year = i % 52
        trading_period = 1 + week_in_year // 4          # 1..13
        week_in_period = 1 + week_in_year % 4             # 1..4
        rows.append({
            "date_key": wk.date().isoformat(),
            "week_start": wk.date().isoformat(),
            "week_end": (wk + pd.Timedelta(days=6)).date().isoformat(),
            "week_num": i + 1,
            "calendar_month": wk.month,
            "calendar_month_name": wk.strftime("%B"),
            "calendar_quarter": f"Q{((wk.month - 1) // 3) + 1}",
            "calendar_year": wk.year,
            "trading_year": f"TY{trading_year}",
            "trading_period": f"P{trading_period:02d}",
            "trading_period_num": trading_period,
            "week_in_trading_period": week_in_period,
            "is_school_holiday_peak": wk.month in (1, 4, 8, 12),
            "is_festive_peak": wk.month == 12,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dim_Chain / Dim_Store
# ---------------------------------------------------------------------------
CHAINS = {
    "MER": {"name": "Meridian Fashion", "format": "Department Store", "n_stores": 6, "sqm_range": (1400, 2600)},
    "URB": {"name": "Urban Basics",     "format": "Value Apparel",    "n_stores": 5, "sqm_range": (600, 1100)},
    "TNY": {"name": "TinyThreads",      "format": "Kids Specialist",  "n_stores": 4, "sqm_range": (300, 600)},
}

REGIONS = ["Northern", "Central", "Coastal", "Western", "Metro"]


def build_dim_store() -> pd.DataFrame:
    r = rng()
    rows = []
    sid = 1
    for chain_code, spec in CHAINS.items():
        for i in range(spec["n_stores"]):
            sqm = int(r.uniform(*spec["sqm_range"]))
            rows.append({
                "store_id": f"ST{sid:03d}",
                "store_name": f"{spec['name']} {REGIONS[i % len(REGIONS)]} {i + 1}",
                "chain_code": chain_code,
                "chain_name": spec["name"],
                "store_format": spec["format"],
                "region": REGIONS[i % len(REGIONS)],
                "size_sqm": sqm,
                "open_date": (HISTORY_START - pd.Timedelta(days=int(r.uniform(365, 365 * 8)))).date().isoformat(),
                "cash_propensity": float(np.clip(r.normal(
                    0.55 if chain_code == "URB" else 0.35 if chain_code == "MER" else 0.45, 0.08), 0.1, 0.9)),
            })
            sid += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dim_Supplier
# ---------------------------------------------------------------------------
def build_dim_supplier() -> pd.DataFrame:
    rows = [
        {"supplier_id": "SUP01", "supplier_name": "Meridian Manufacturing – Plant A", "supplier_type": "Internal Manufacturing", "country": "Home Market", "lead_time_days": 21, "payment_terms_days": 0},
        {"supplier_id": "SUP02", "supplier_name": "Meridian Manufacturing – Plant B", "supplier_type": "Internal Manufacturing", "country": "Home Market", "lead_time_days": 28, "payment_terms_days": 0},
        {"supplier_id": "SUP03", "supplier_name": "Delta Textile Mills",     "supplier_type": "External", "country": "Regional",       "lead_time_days": 35, "payment_terms_days": 30},
        {"supplier_id": "SUP04", "supplier_name": "Horizon Garments Co.",    "supplier_type": "External", "country": "Import",         "lead_time_days": 56, "payment_terms_days": 45},
        {"supplier_id": "SUP05", "supplier_name": "Stridewell Footwear",     "supplier_type": "External", "country": "Import",         "lead_time_days": 63, "payment_terms_days": 45},
        {"supplier_id": "SUP06", "supplier_name": "Coastal Home Textiles",   "supplier_type": "External", "country": "Regional",       "lead_time_days": 28, "payment_terms_days": 30},
        {"supplier_id": "SUP07", "supplier_name": "Everyday Accessories Ltd", "supplier_type": "External", "country": "Import",        "lead_time_days": 42, "payment_terms_days": 30},
        {"supplier_id": "SUP08", "supplier_name": "ActiveGear Sportswear",   "supplier_type": "External", "country": "Import",         "lead_time_days": 49, "payment_terms_days": 45},
        {"supplier_id": "SUP09", "supplier_name": "SchoolBrand Uniforms",    "supplier_type": "External", "country": "Home Market",     "lead_time_days": 21, "payment_terms_days": 30},
        {"supplier_id": "SUP10", "supplier_name": "Northline Denim Co.",     "supplier_type": "External", "country": "Regional",        "lead_time_days": 35, "payment_terms_days": 30},
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dim_Product — Group > Department > Category, plus size/colour/source
# ---------------------------------------------------------------------------
DEPARTMENTS = {
    # department: (group, [categories], unit_cost, unit_price, base_weekly_units_per_store, supplier_id, source_type)
    "Menswear":        ("Apparel",         ["Shirts", "Trousers", "Denim"],      12.0, 26.0, 22, "SUP01", "Own Manufacture"),
    "Womenswear":       ("Apparel",         ["Dresses", "Knitwear", "Denim"],     11.0, 28.0, 26, "SUP01", "Own Manufacture"),
    "Kidswear":         ("Apparel",         ["Playwear", "Knitwear"],             7.0,  16.0, 30, "SUP02", "Own Manufacture"),
    "School Uniforms":  ("Apparel",         ["Uniform Sets", "Uniform Basics"],   9.0,  20.0, 18, "SUP09", "External"),
    "Sportswear":       ("Apparel",         ["Activewear", "Outerwear"],          13.0, 30.0, 12, "SUP08", "External"),
    "Footwear":         ("Footwear",        ["Casual", "School Shoes"],           15.0, 34.0, 14, "SUP05", "External"),
    "Home & Textiles":  ("Home & Textiles", ["Bedding", "Towels"],                8.0,  19.0, 10, "SUP06", "External"),
    "Accessories":      ("Accessories",     ["Bags", "Belts & Small Leather"],    4.0,  10.0, 16, "SUP07", "External"),
}
SIZES_APPAREL = ["XS", "S", "M", "L", "XL"]
SIZES_FOOTWEAR = ["3", "4", "5", "6", "7", "8", "9"]
COLOURS = ["Black", "Navy", "White", "Grey", "Print"]
SKUS_PER_DEPT = 5


def build_dim_product() -> pd.DataFrame:
    r = rng()
    rows = []
    pid = 1
    for dept, (group, cats, cost, price, base_units, supplier, source) in DEPARTMENTS.items():
        for i in range(SKUS_PER_DEPT):
            cat = cats[i % len(cats)]
            size = (SIZES_FOOTWEAR if dept == "Footwear" else SIZES_APPAREL)[i % len(SIZES_FOOTWEAR if dept == "Footwear" else SIZES_APPAREL)]
            price_jitter = float(r.uniform(0.85, 1.2))
            rows.append({
                "product_id": f"SKU{pid:04d}",
                "product_name": f"{dept} {cat} {i + 1}",
                "product_group": group,
                "department": dept,
                "category": cat,
                "size": size,
                "colour": COLOURS[i % len(COLOURS)],
                "supplier_id": supplier,
                "source_type": source,
                "unit_cost": round(cost * price_jitter, 2),
                "unit_price": round(price * price_jitter, 2),
                "base_weekly_units_per_store": max(2, int(base_units * r.uniform(0.6, 1.3) / SKUS_PER_DEPT * 2)),
                "moq": int(r.choice([150, 200, 250, 300, 400])),
                "reorder_cycle_weeks": int(r.choice([4, 6, 8])),
            })
            pid += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fact_Sales & Fact_Inventory — grain: store x product x week
# ---------------------------------------------------------------------------
UPT_BY_DEPT = {  # units per transaction (basket size driver)
    "Menswear": 1.6, "Womenswear": 1.8, "Kidswear": 2.6, "School Uniforms": 3.2,
    "Sportswear": 1.7, "Footwear": 1.3, "Home & Textiles": 1.5, "Accessories": 2.1,
}


def build_fact_sales_and_inventory(dim_date, dim_store, dim_product):
    r = rng()
    sales_rows, inv_rows = [], []
    weeks = dim_date[["date_key", "week_num", "is_school_holiday_peak", "is_festive_peak"]].to_dict("records")

    for _, prod in dim_product.iterrows():
        upt = UPT_BY_DEPT[prod["department"]]
        cycle = int(prod["reorder_cycle_weeks"])
        flat_receipt = int(prod["base_weekly_units_per_store"] * cycle * 1.1)

        for _, store in dim_store.iterrows():
            stock = flat_receipt  # opening stock
            age = 0
            for wk in weeks:
                due = wk["week_num"] % cycle == 0
                overstocked = stock > flat_receipt * 1.5
                arrival = flat_receipt if (due and not overstocked) else 0
                if arrival:
                    age = 0
                stock += arrival

                seasonal = 1.0
                if prod["department"] in ("Kidswear", "School Uniforms") and wk["is_school_holiday_peak"]:
                    seasonal *= 1.4
                if wk["is_festive_peak"]:
                    seasonal *= 1.35
                noise = float(r.normal(1.0, 0.12))
                demand = max(0.0, prod["base_weekly_units_per_store"] * seasonal * noise)
                units_sold = min(demand, stock)
                stock -= units_sold
                age += 1

                gross_price = prod["unit_price"]
                discount_rate = 0.0
                # markdown kicks in on ageing stock, deeper the older it gets
                if age > cycle * 1.5:
                    discount_rate = min(0.5, 0.1 + 0.05 * (age - cycle * 1.5))
                net_price = gross_price * (1 - discount_rate)

                gross_sales_value = units_sold * gross_price
                discount_value = units_sold * gross_price * discount_rate
                net_sales_value = units_sold * net_price
                cogs_value = units_sold * prod["unit_cost"]

                cash_share = float(np.clip(store["cash_propensity"] + r.normal(0, 0.05), 0.05, 0.95))
                cash_sales_value = net_sales_value * cash_share
                credit_sales_value = net_sales_value - cash_sales_value

                transactions = units_sold / upt if upt else 0
                cash_transactions = transactions * cash_share
                credit_transactions = transactions - cash_transactions

                sales_rows.append({
                    "date_key": wk["date_key"], "store_id": store["store_id"], "product_id": prod["product_id"],
                    "units_sold": round(units_sold, 2),
                    "gross_sales_value": round(gross_sales_value, 2),
                    "discount_value": round(discount_value, 2),
                    "net_sales_value": round(net_sales_value, 2),
                    "cogs_value": round(cogs_value, 2),
                    "cash_sales_value": round(cash_sales_value, 2),
                    "credit_sales_value": round(credit_sales_value, 2),
                    "cash_transactions": round(cash_transactions, 2),
                    "credit_transactions": round(credit_transactions, 2),
                })
                inv_rows.append({
                    "date_key": wk["date_key"], "store_id": store["store_id"], "product_id": prod["product_id"],
                    "stock_on_hand_units": round(stock, 2),
                    "stock_on_hand_cost": round(stock * prod["unit_cost"], 2),
                    "stock_on_hand_retail": round(stock * prod["unit_price"], 2),
                    "stock_age_weeks": age,
                    "units_received": arrival,
                })
    return pd.DataFrame(sales_rows), pd.DataFrame(inv_rows)


# ---------------------------------------------------------------------------
# Fact_PurchaseOrders — PO / OTIF grain
# ---------------------------------------------------------------------------
def build_fact_purchase_orders(dim_date, dim_product, dim_supplier):
    r = rng()
    rows = []
    po_id = 1
    supplier_lookup = dim_supplier.set_index("supplier_id").to_dict("index")
    order_weeks = dim_date.iloc[::3]  # a new PO roughly every 3 weeks per product

    for _, prod in dim_product.iterrows():
        supplier = supplier_lookup[prod["supplier_id"]]
        lead_days = supplier["lead_time_days"]
        for _, wk in order_weeks.iterrows():
            order_date = pd.Timestamp(wk["date_key"])
            promised_date = order_date + pd.Timedelta(days=int(lead_days))
            ordered_qty = int(prod["base_weekly_units_per_store"] * 15 * r.uniform(0.8, 1.2))
            ordered_cost = round(ordered_qty * prod["unit_cost"], 2)

            delay_days = int(r.normal(-3 if supplier["supplier_type"] == "Internal Manufacturing" else -1, 3.5))
            actual_date = promised_date + pd.Timedelta(days=delay_days)
            fill_rate = float(np.clip(r.normal(0.99, 0.015), 0.9, 1.0))
            received_qty = int(min(ordered_qty, round(ordered_qty * fill_rate)))

            on_time = actual_date <= promised_date
            in_full = received_qty >= ordered_qty * 0.95

            rows.append({
                "po_id": f"PO{po_id:05d}", "supplier_id": prod["supplier_id"], "product_id": prod["product_id"],
                "department": prod["department"], "order_date": order_date.date().isoformat(),
                "promised_date": promised_date.date().isoformat(), "actual_delivery_date": actual_date.date().isoformat(),
                "ordered_qty": ordered_qty, "received_qty": received_qty, "ordered_cost": ordered_cost,
                "on_time_flag": bool(on_time), "in_full_flag": bool(in_full), "otif_flag": bool(on_time and in_full),
            })
            po_id += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fact_OTB — chain x department x trading period
# ---------------------------------------------------------------------------
def build_fact_otb(dim_date, dim_store, dim_product):
    r = rng()
    rows = []
    period_keys = dim_date.groupby(["trading_year", "trading_period"], as_index=False).agg(
        period_start=("date_key", "min"))
    chains = dim_store[["chain_code", "chain_name"]].drop_duplicates()
    depts = dim_product["department"].unique()

    for _, chain in chains.iterrows():
        for dept in depts:
            base_sales = float(r.uniform(15000, 60000))
            opening = base_sales * float(r.uniform(2.0, 3.0))
            for _, per in period_keys.iterrows():
                trend = 1 + 0.01 * r.normal(0, 1)
                planned_sales = round(base_sales * trend, 2)
                planned_markdown = round(planned_sales * float(r.uniform(0.03, 0.09)), 2)
                planned_receipts = round(planned_sales * float(r.uniform(0.9, 1.15)), 2)
                planned_closing = round(opening + planned_receipts - planned_sales - planned_markdown, 2)
                committed_receipts = round(planned_receipts * float(r.uniform(0.4, 0.85)), 2)
                otb_value = round(planned_receipts - committed_receipts, 2)

                rows.append({
                    "trading_year": per["trading_year"], "trading_period": per["trading_period"],
                    "period_start": per["period_start"], "chain_code": chain["chain_code"], "chain_name": chain["chain_name"],
                    "department": dept,
                    "opening_stock_cost": round(opening, 2), "planned_sales_cost": planned_sales,
                    "planned_markdown_cost": planned_markdown, "planned_receipts_cost": planned_receipts,
                    "committed_receipts_cost": committed_receipts, "otb_value": otb_value,
                    "planned_closing_stock_cost": planned_closing,
                })
                opening = planned_closing
                base_sales *= trend
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fact_Manufacturing — plant x department x week work orders
# ---------------------------------------------------------------------------
def build_fact_manufacturing(dim_date):
    r = rng()
    rows = []
    plants = [
        {"plant_id": "SUP01", "plant_name": "Plant A", "departments": ["Menswear", "Womenswear"], "capacity_units": 3200},
        {"plant_id": "SUP02", "plant_name": "Plant B", "departments": ["Kidswear"], "capacity_units": 2600},
    ]
    wo_id = 1
    for plant in plants:
        for dept in plant["departments"]:
            for _, wk in dim_date.iterrows():
                planned_units = int(plant["capacity_units"] / len(plant["departments"]) * r.uniform(0.8, 1.0))
                available_hours = 40.0
                downtime_hours = float(np.clip(r.normal(3.5, 2.0), 0, 15))
                run_hours = max(0.0, available_hours - downtime_hours)
                performance_rate = float(np.clip(r.normal(0.92, 0.05), 0.6, 1.0))
                actual_units = int(planned_units * (run_hours / available_hours) * performance_rate)
                defect_rate = float(np.clip(r.normal(0.025, 0.012), 0.0, 0.15))
                defect_units = int(actual_units * defect_rate)
                scrap_units = int(defect_units * float(r.uniform(0.3, 0.7)))
                good_units = actual_units - defect_units
                labor_hours = round(run_hours * float(r.uniform(0.9, 1.1)), 1)
                material_cost = round(actual_units * float(r.uniform(4.5, 7.5)), 2)
                labor_cost = round(labor_hours * float(r.uniform(8.0, 12.0)), 2)
                overhead_cost = round((material_cost + labor_cost) * 0.18, 2)

                rows.append({
                    "work_order_id": f"WO{wo_id:05d}", "plant_id": plant["plant_id"], "plant_name": plant["plant_name"],
                    "department": dept, "date_key": wk["date_key"],
                    "planned_units": planned_units, "actual_units_produced": actual_units,
                    "good_units": good_units, "defect_units": defect_units, "scrap_units": scrap_units,
                    "available_hours": available_hours, "downtime_hours": round(downtime_hours, 1),
                    "labor_hours": labor_hours,
                    "material_cost": material_cost, "labor_cost": labor_cost, "overhead_cost": overhead_cost,
                    "manufacturing_cost_total": round(material_cost + labor_cost + overhead_cost, 2),
                    "on_time_completion_flag": bool(r.uniform(0, 1) > 0.12),
                })
                wo_id += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fact_Finance — chain x month P&L and working capital
# ---------------------------------------------------------------------------
def build_fact_finance(fact_sales, dim_date, dim_store):
    r = rng()
    ds = fact_sales.merge(dim_store[["store_id", "chain_code", "chain_name"]], on="store_id")
    ds = ds.merge(dim_date[["date_key", "calendar_month", "calendar_year"]], on="date_key")
    monthly = ds.groupby(["chain_code", "chain_name", "calendar_year", "calendar_month"], as_index=False).agg(
        revenue=("net_sales_value", "sum"), cogs=("cogs_value", "sum"))

    rows = []
    for _, row in monthly.iterrows():
        revenue, cogs = row["revenue"], row["cogs"]
        gross_margin = revenue - cogs
        opex = round(revenue * float(r.uniform(0.22, 0.30)), 2)
        ebitda = round(gross_margin - opex, 2)
        budget_revenue = round(revenue * float(r.uniform(0.92, 1.08)), 2)
        budget_ebitda = round(ebitda * float(r.uniform(0.85, 1.15)), 2)
        inventory_value = round(revenue * float(r.uniform(1.6, 2.4)), 2)
        debtors_balance = round(revenue * float(r.uniform(0.3, 0.6)), 2)
        creditors_balance = round(cogs * float(r.uniform(0.5, 0.9)), 2)

        rows.append({
            "chain_code": row["chain_code"], "chain_name": row["chain_name"],
            "calendar_year": int(row["calendar_year"]), "calendar_month": int(row["calendar_month"]),
            "revenue": round(revenue, 2), "cogs": round(cogs, 2), "gross_margin": round(gross_margin, 2),
            "opex": opex, "ebitda": ebitda,
            "budget_revenue": budget_revenue, "budget_ebitda": budget_ebitda,
            "inventory_value": inventory_value, "debtors_balance": debtors_balance,
            "creditors_balance": creditors_balance,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fact_Credit — store-credit book by chain x month
# ---------------------------------------------------------------------------
def build_fact_credit(fact_finance):
    r = rng()
    rows = []
    book = {}
    for _, row in fact_finance.sort_values(["chain_code", "calendar_year", "calendar_month"]).iterrows():
        key = row["chain_code"]
        opening = book.get(key, row["revenue"] * 0.9)
        credit_sales = round(row["revenue"] * float(r.uniform(0.25, 0.45)), 2)
        collections = round(opening * float(r.uniform(0.55, 0.75)) + credit_sales * float(r.uniform(0.2, 0.4)), 2)
        write_offs = round(opening * float(r.uniform(0.005, 0.02)), 2)
        closing = round(max(0.0, opening + credit_sales - collections - write_offs), 2)
        active_accounts = int(closing / float(r.uniform(180, 260)))
        new_accounts = int(active_accounts * float(r.uniform(0.02, 0.06)))
        arrears_30 = round(closing * float(r.uniform(0.08, 0.14)), 2)
        arrears_60 = round(closing * float(r.uniform(0.03, 0.07)), 2)
        arrears_90plus = round(closing * float(r.uniform(0.02, 0.05)), 2)
        bad_debt_provision = round(arrears_90plus * float(r.uniform(0.5, 0.8)), 2)
        interest_income = round(closing * float(r.uniform(0.015, 0.03)), 2)

        rows.append({
            "chain_code": row["chain_code"], "chain_name": row["chain_name"],
            "calendar_year": row["calendar_year"], "calendar_month": row["calendar_month"],
            "opening_balance": round(opening, 2), "credit_sales": credit_sales, "collections": collections,
            "write_offs": write_offs, "closing_balance": closing,
            "active_accounts": active_accounts, "new_accounts": new_accounts,
            "arrears_30": arrears_30, "arrears_60": arrears_60, "arrears_90plus": arrears_90plus,
            "bad_debt_provision": bad_debt_provision, "interest_income": interest_income,
        })
        book[key] = closing
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    dim_date = build_dim_date()
    dim_store = build_dim_store()
    dim_supplier = build_dim_supplier()
    dim_product = build_dim_product()

    fact_sales, fact_inventory = build_fact_sales_and_inventory(dim_date, dim_store, dim_product)
    fact_po = build_fact_purchase_orders(dim_date, dim_product, dim_supplier)
    fact_otb = build_fact_otb(dim_date, dim_store, dim_product)
    fact_mfg = build_fact_manufacturing(dim_date)
    fact_finance = build_fact_finance(fact_sales, dim_date, dim_store)
    fact_credit = build_fact_credit(fact_finance)

    tables = {
        "dim_date": dim_date, "dim_store": dim_store, "dim_supplier": dim_supplier, "dim_product": dim_product,
        "fact_sales": fact_sales, "fact_inventory": fact_inventory, "fact_purchase_orders": fact_po,
        "fact_otb": fact_otb, "fact_manufacturing": fact_mfg, "fact_finance": fact_finance, "fact_credit": fact_credit,
    }
    for name, df in tables.items():
        path = os.path.join(OUT_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"{name:22s} {len(df):>7,} rows -> {path}")


if __name__ == "__main__":
    main()
