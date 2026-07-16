"""
Capital-Weighted Open-to-Buy — Blueprint section 5.1.

Implements the RAROCE ranking exactly as specified:

    RAROCE = [(Vest·Wsell·Mhc) - (Ccap·Wsell) - FXloss - (Pdef·Lmd)] / Icap
             × 52 / Wsell

Store-level candidate quantities (sized off the forecast engine's
predicted velocity, not a flat split) are rolled up into a group-level
buy, rounded to the supplier's MOQ / pack size, then reallocated back to
stores by demand share — the "we optimise within real constraints"
mechanic in the blueprint.
"""
import numpy as np
import pandas as pd

from src import config

TARGET_WEEKS_COVER = 8          # one replenishment cycle, matches IMPORT_LEAD_TIME_WEEKS
FX_LOSS_CAP_PER_WEEK = 0.01      # cap on assumed weekly depreciation drag, as a fraction of capital
DEFAULT_MARKDOWN_LOSS_RATE = 0.30  # expected loss rate if a markdown default occurs


def _fx_loss_rate_per_week(macro: pd.DataFrame) -> float:
    """Proxy for expected hard-currency depreciation drag over the holding
    period, from the recent trend in the parallel-rate premium — the
    'FXloss' term the D365 ledger has no concept of."""
    recent = macro.tail(12)
    if len(recent) < 2:
        return 0.0
    slope = (recent["parallel_rate_premium"].iloc[-1] - recent["parallel_rate_premium"].iloc[0]) / len(recent)
    return float(np.clip(slope, 0.0, FX_LOSS_CAP_PER_WEEK))


def _markdown_default_probability(velocity_row: pd.Series) -> float:
    """Pdef: how likely this line needs a markdown, proxied by how far
    predicted velocity has fallen below its own recent baseline."""
    baseline = max(velocity_row["baseline_velocity"], 0.1)
    shortfall = 1 - (velocity_row["predicted_velocity"] / baseline)
    return float(np.clip(shortfall, 0.0, 0.9))


def store_level_candidates(velocity: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    df = velocity.copy()
    fx_rate = _fx_loss_rate_per_week(macro)

    df["vest"] = df["predicted_velocity"].clip(lower=0.2)
    df["candidate_qty"] = (df["vest"] * TARGET_WEEKS_COVER).round()
    df["wsell"] = TARGET_WEEKS_COVER
    df["icap"] = df["candidate_qty"] * df["unit_cost"]
    df["mhc"] = df["unit_price"] - df["unit_cost"]
    df["ccap"] = df["icap"] * config.WEEKLY_BORROW_RATE
    df["fx_loss"] = df["icap"] * fx_rate * (df["wsell"] + config.IMPORT_LEAD_TIME_WEEKS)
    df["p_default"] = df.apply(_markdown_default_probability, axis=1)
    df["l_markdown"] = df["icap"] * DEFAULT_MARKDOWN_LOSS_RATE
    df["markdown_risk_cost"] = df["p_default"] * df["l_markdown"]

    gross_return = df["vest"] * df["wsell"] * df["mhc"]
    net_return = gross_return - (df["ccap"] * df["wsell"]) - df["fx_loss"] - df["markdown_risk_cost"]
    df["raroce_holding_period"] = net_return / df["icap"].replace(0, np.nan)
    df["raroce_annualised"] = df["raroce_holding_period"] * (52 / df["wsell"])
    df["raroce_annualised"] = df["raroce_annualised"].fillna(0.0)
    return df


def _round_to_pack(qty, pack_size, moq):
    if qty <= 0:
        return 0
    rounded = int(np.ceil(qty / pack_size) * pack_size)
    return max(rounded, moq)


def group_level_buy(candidates: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    """Aggregate store candidates into one group (national) buy per
    category, respecting MOQ and pack size, since Edgars procures
    centrally in USD."""
    cat_specs = categories.set_index("category")[["moq", "pack_size", "unit_cost", "unit_price"]]

    rows = []
    for cat_name, grp in candidates.groupby("category", observed=True):
        raw_group_qty = grp["candidate_qty"].sum()
        moq, pack_size = cat_specs.loc[cat_name, "moq"], cat_specs.loc[cat_name, "pack_size"]
        final_qty = _round_to_pack(raw_group_qty, pack_size, moq)

        unit_cost = cat_specs.loc[cat_name, "unit_cost"]
        unit_price = cat_specs.loc[cat_name, "unit_price"]
        capital_committed = final_qty * unit_cost
        weighted_raroce = np.average(grp["raroce_annualised"], weights=grp["icap"].clip(lower=1))

        rows.append({
            "category": cat_name,
            "raw_demand_qty": raw_group_qty,
            "recommended_group_qty": final_qty,
            "moq": moq, "pack_size": pack_size,
            "capital_committed_usd": capital_committed,
            "weighted_raroce_annualised": weighted_raroce,
            "n_stores": len(grp),
        })

    out = pd.DataFrame(rows).sort_values("weighted_raroce_annualised", ascending=False).reset_index(drop=True)
    out["otb_priority_rank"] = range(1, len(out) + 1)
    return out


def store_level_allocation(candidates: pd.DataFrame, group_buy: pd.DataFrame) -> pd.DataFrame:
    """Distribute each category's group buy back to stores by demand
    share — the smart replacement for today's flat per-store split."""
    df = candidates.merge(
        group_buy[["category", "recommended_group_qty"]], on="category", how="left"
    )
    df["demand_share"] = df.groupby("category", observed=True)["candidate_qty"].transform(
        lambda s: s / max(s.sum(), 1e-9)
    )
    df["allocated_qty"] = (df["recommended_group_qty"] * df["demand_share"]).round()
    df["allocated_capital_usd"] = df["allocated_qty"] * df["unit_cost"]

    flat_share = 1.0 / df.groupby("category", observed=True)["store_id"].transform("count")
    df["flat_qty_today"] = (df["recommended_group_qty"] * flat_share).round()
    df["capital_reallocated_usd"] = df["allocated_capital_usd"] - (df["flat_qty_today"] * df["unit_cost"])
    return df


def build_otb_recommendation(data: dict, model_bundle, velocity: pd.DataFrame) -> dict:
    candidates = store_level_candidates(velocity, data["macro"])
    group_buy = group_level_buy(candidates, data["categories"])
    allocation = store_level_allocation(candidates, group_buy)

    total_capital = group_buy["capital_committed_usd"].sum()
    reallocation_moved = allocation["capital_reallocated_usd"].abs().sum() / 2  # moved-from + moved-to double counts

    return {
        "candidates": candidates,
        "group_buy": group_buy,
        "allocation": allocation,
        "total_capital_committed_usd": total_capital,
        "capital_reallocated_usd": reallocation_moved,
    }
