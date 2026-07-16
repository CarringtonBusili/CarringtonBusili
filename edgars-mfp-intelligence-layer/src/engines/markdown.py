"""
Predictive Markdown and Lifecycle Elasticity — Blueprint section 5.2.

For each store-category, projects the sell-through curve at the
forecast engine's predicted velocity, finds the point at which carrying
cost overtakes the margin recovered by waiting, and recommends either a
pre-emptive markdown (bounded by a replacement-cost floor) or an
inter-branch reallocation where that is cheaper than discounting.
"""
import numpy as np
import pandas as pd

from src import config

TARGET_WEEKS_TO_CLEAR = 10       # the weeks-of-cover the engine tries to restore
PRICE_ELASTICITY = -1.8          # illustrative apparel price elasticity of demand
MAX_DISCOUNT_DEPTH = 0.6
TRANSFER_COST_PCT_OF_COST = 0.15   # inter-branch transfer cost, as a % of unit cost
ACTION_TRIGGER_WEEKS = 14         # weeks-of-cover above which the engine starts looking

# The counterfactual: what happens if the line is left for the native,
# retrospective Lifecycle Worksheet to catch instead of acting now.
PANIC_DELAY_WEEKS = 12             # how much later the reactive process would flag it
PANIC_DISCOUNT_MULTIPLIER = 1.6    # reactive clearance is steeper — "margin-killing", not disciplined


def _replacement_cost_floor(unit_cost: float, fx_loss_rate_per_week: float) -> float:
    """Never recommend clearing below what restocking will cost tomorrow —
    in an FX-volatile economy that's higher than today's book cost."""
    return unit_cost * (1 + fx_loss_rate_per_week * config.IMPORT_LEAD_TIME_WEEKS)


def _fx_loss_rate_per_week(macro: pd.DataFrame) -> float:
    recent = macro.tail(12)
    if len(recent) < 2:
        return 0.0
    slope = (recent["parallel_rate_premium"].iloc[-1] - recent["parallel_rate_premium"].iloc[0]) / len(recent)
    return float(np.clip(slope, 0.0, 0.01))


def build_markdown_queue(classified: pd.DataFrame, velocity: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    df = classified.merge(
        velocity[["store_id", "category", "predicted_velocity"]],
        on=["store_id", "category"], how="left",
    )
    df["predicted_velocity"] = df["predicted_velocity"].fillna(df["avg_weekly_velocity"]).clip(lower=0.1)
    fx_rate = _fx_loss_rate_per_week(macro)

    df["weeks_to_clear_at_current_velocity"] = df["stock_on_hand_units"] / df["predicted_velocity"]
    df["replacement_cost_floor"] = _replacement_cost_floor(df["unit_cost"], fx_rate)
    df["max_discount_depth"] = (1 - df["replacement_cost_floor"] / df["unit_price"]).clip(lower=0, upper=MAX_DISCOUNT_DEPTH)

    needs_action = df["weeks_to_clear_at_current_velocity"] > ACTION_TRIGGER_WEEKS
    needed_velocity = (df["stock_on_hand_units"] / TARGET_WEEKS_TO_CLEAR).clip(lower=0.01)
    uplift_ratio = (needed_velocity / df["predicted_velocity"]) - 1
    raw_discount = (uplift_ratio / abs(PRICE_ELASTICITY)).clip(lower=0)

    df["recommended_discount_depth"] = np.where(
        needs_action, np.minimum(raw_discount, df["max_discount_depth"]), 0.0
    )
    df["floor_binding"] = needs_action & (raw_discount > df["max_discount_depth"])

    achieved_velocity = df["predicted_velocity"] * (1 + abs(PRICE_ELASTICITY) * df["recommended_discount_depth"])
    df["weeks_to_clear_after_markdown"] = np.where(
        needs_action, df["stock_on_hand_units"] / achieved_velocity.clip(lower=0.01),
        df["weeks_to_clear_at_current_velocity"],
    )

    weeks_saved = (df["weeks_to_clear_at_current_velocity"] - df["weeks_to_clear_after_markdown"]).clip(lower=0)
    df["margin_given_up_usd"] = (
        df["stock_on_hand_units"] * df["unit_price"] * df["recommended_discount_depth"]
    )

    # Counterfactual: leave it for the retrospective Lifecycle Worksheet to
    # flag PANIC_DELAY_WEEKS later. By then the same stock has accrued extra
    # carrying cost, and the resulting reactive clearance goes deeper —
    # this is the actual "acting weeks earlier recovers more margin" case,
    # not a same-period carrying-cost-vs-discount trade-off.
    panic_discount_depth = np.where(
        needs_action, np.minimum(df["recommended_discount_depth"] * PANIC_DISCOUNT_MULTIPLIER, MAX_DISCOUNT_DEPTH), 0.0
    )
    df["reactive_panic_discount_depth"] = panic_discount_depth
    df["margin_given_up_if_delayed_usd"] = (
        df["stock_on_hand_units"] * df["unit_price"] * df["reactive_panic_discount_depth"]
    )
    df["extra_carrying_cost_from_delay_usd"] = np.where(
        needs_action, df["stock_value_usd"] * config.WEEKLY_BORROW_RATE * PANIC_DELAY_WEEKS, 0.0
    )
    df["carrying_cost_avoided_usd"] = weeks_saved * df["stock_value_usd"] * config.WEEKLY_BORROW_RATE

    df["net_benefit_usd"] = (
        (df["margin_given_up_if_delayed_usd"] + df["extra_carrying_cost_from_delay_usd"])
        - df["margin_given_up_usd"]
    )
    df["action_required"] = needs_action

    return df


def reallocation_opportunities(markdown_queue: pd.DataFrame) -> pd.DataFrame:
    """Where a same-category store elsewhere is understocked relative to
    its own demand, and the transfer cost is lower than the avoided
    markdown loss, recommend a transfer instead of a discount."""
    rows = []
    for cat, grp in markdown_queue.groupby("category", observed=True):
        senders = grp[grp["action_required"] & (grp["recommended_discount_depth"] > 0)]
        receivers = grp[grp["weeks_to_clear_at_current_velocity"] < TARGET_WEEKS_TO_CLEAR * 0.5]
        if senders.empty or receivers.empty:
            continue

        receivers = receivers.sort_values("weeks_to_clear_at_current_velocity")
        for _, send in senders.iterrows():
            surplus_units = max(send["stock_on_hand_units"] - send["predicted_velocity"] * TARGET_WEEKS_TO_CLEAR, 0)
            if surplus_units < 1:
                continue
            for _, recv in receivers.iterrows():
                if recv["store_id"] == send["store_id"]:
                    continue
                shortfall_units = max(recv["predicted_velocity"] * TARGET_WEEKS_TO_CLEAR - recv["stock_on_hand_units"], 0)
                transfer_qty = min(surplus_units, shortfall_units)
                if transfer_qty < 1:
                    continue

                transfer_cost = transfer_qty * send["unit_cost"] * TRANSFER_COST_PCT_OF_COST
                avoided_markdown_loss = transfer_qty * send["unit_price"] * send["recommended_discount_depth"]
                if transfer_cost < avoided_markdown_loss:
                    rows.append({
                        "category": cat,
                        "from_store": send["store_id"], "to_store": recv["store_id"],
                        "transfer_qty": round(transfer_qty),
                        "transfer_cost_usd": transfer_cost,
                        "avoided_markdown_loss_usd": avoided_markdown_loss,
                        "net_saving_usd": avoided_markdown_loss - transfer_cost,
                    })
                    surplus_units -= transfer_qty
                if surplus_units < 1:
                    break

    if not rows:
        return pd.DataFrame(columns=["category", "from_store", "to_store", "transfer_qty",
                                      "transfer_cost_usd", "avoided_markdown_loss_usd", "net_saving_usd"])
    return pd.DataFrame(rows).sort_values("net_saving_usd", ascending=False).reset_index(drop=True)


def build_markdown_report(data: dict, classified: pd.DataFrame, velocity: pd.DataFrame) -> dict:
    queue = build_markdown_queue(classified, velocity, data["macro"])
    reallocation = reallocation_opportunities(queue)

    flagged = queue[queue["action_required"]].sort_values("net_benefit_usd", ascending=False)
    summary = {
        "n_lines_flagged": len(flagged),
        "total_carrying_cost_avoided_usd": flagged["carrying_cost_avoided_usd"].sum(),
        "total_margin_given_up_usd": flagged["margin_given_up_usd"].sum(),
        "total_net_benefit_usd": flagged["net_benefit_usd"].sum(),
        "n_floor_binding": int(queue["floor_binding"].sum()),
        "reallocation_net_saving_usd": reallocation["net_saving_usd"].sum() if len(reallocation) else 0.0,
        "reallocation_moves": len(reallocation),
    }
    return {"queue": queue, "flagged": flagged, "reallocation": reallocation, "summary": summary}
