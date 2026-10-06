"""
02_clean.py - Data cleaning, feature engineering, and flag generation.
Run from the project root:  python src/02_clean.py
"""
import pandas as pd
from pathlib import Path

def main():
    print("========================================")
    print(" VIREO AUDIO: DATA CLEANING SCRIPT")
    print("========================================\n")

    DATA = Path(__file__).resolve().parent.parent / "data"
    OUTPUT = Path(__file__).resolve().parent.parent / "outputs"
    OUTPUT.mkdir(exist_ok=True)

    print("Loading datasets...")
    tickets = pd.read_csv(DATA / "tickets.csv", parse_dates=["created_at", "first_response_at", "resolved_at"])
    agents = pd.read_csv(DATA / "agents.csv")
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])

    # --- Rule 1: Timezone & Durations ---
    print("\n--- 1. Timezone & Durations ---")
    is_legacy = tickets["source_system"] == "legacy_fd"
    has_resolved = tickets["resolved_at"].notna()
    
    # Legacy system resolved_at is UTC; add 330 mins to align with IST
    tickets.loc[is_legacy & has_resolved, "resolved_at"] += pd.to_timedelta(330, unit='min')

    tickets["resolve_mins"] = (tickets["resolved_at"] - tickets["created_at"]).dt.total_seconds() / 60.0
    tickets["first_resp_mins"] = (tickets["first_response_at"] - tickets["created_at"]).dt.total_seconds() / 60.0

    print("resolve_mins percentiles (status == 'resolved'):")
    resolved_mask = tickets["status"] == "resolved"
    q = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95]
    print(tickets[resolved_mask].groupby("source_system")["resolve_mins"].describe(percentiles=q)[['1%', '5%', '25%', '50%', '75%', '95%']].round(0))
    
    neg_count = (tickets["resolve_mins"] < 0).sum()
    print(f"\nNegative resolve_mins count: {neg_count} (Expected: 0)")

    # --- Rule 2: Time Windows ---
    print("\n--- 2. Time Windows ---")
    tickets["in_window"] = tickets["created_at"] >= "2025-01-01"
    tickets["pre_policy"] = tickets["created_at"] < "2025-04-01"
    print(f"in_window (>= 2025-01-01): {tickets['in_window'].sum():,} rows flagged")
    print(f"pre_policy (< 2025-04-01): {tickets['pre_policy'].sum():,} rows flagged")

    # --- Rule 3: Near-duplicate detection ---
    print("\n--- 3. Near-duplicates ---")
    # Entity duplicates (same customer, product, and creation time)
    tickets["dup_entity"] = tickets.duplicated(subset=["customer_id", "product_sku", "created_at"], keep=False)
    
    # Text duplicates (same message text, excluding blanks)
    text_mask = tickets["customer_message"].notna() & (tickets["customer_message"].str.strip() != "")
    dup_text_idx = tickets[text_mask].duplicated(subset=["customer_message"], keep=False)
    tickets["dup_text"] = False
    tickets.loc[dup_text_idx[dup_text_idx].index, "dup_text"] = True

    tickets["month"] = tickets["created_at"].dt.to_period("M")
    dup_rows = tickets[tickets["dup_entity"] | tickets["dup_text"]]
    print("Duplicates by source_system:")
    print(dup_rows["source_system"].value_counts())
    print("\nDuplicates by month:")
    print(dup_rows["month"].value_counts().sort_index())
    
    print("\n5 Example pairs of dup_text:")
    dup_texts = tickets[tickets["dup_text"]].groupby("customer_message")
    count = 0
    for msg, group in dup_texts:
        if len(group) > 1:
            print(f"\nGroup {count+1}: '{msg[:80]}...'")
            print(group[["ticket_id", "source_system", "created_at"]].to_string(index=False))
            count += 1
            if count == 5:
                break
    tickets.drop(columns=["month"], inplace=True)

    # --- Rule 4: SLA Targets & Team match ---
    print("\n--- 4. SLA & Team Match ---")
    sla_map = {'chat': 15, 'voice': 120, 'social': 240, 'email': 480}
    tickets["sla_target_min"] = tickets["channel"].map(sla_map)
    tickets["sla_breach"] = tickets["first_resp_mins"] > tickets["sla_target_min"]

    # Agents: deduplicate to find core assignment
    agent_info = agents.drop_duplicates("agent_id", keep="last")
    agent_dict = agent_info.set_index("agent_id")[["team", "tier"]]
    tickets = tickets.join(agent_dict.rename(columns={"team": "resolver_team", "tier": "resolver_tier"}), on="agent_id")
    
    tickets["team_mismatch"] = tickets["resolver_team"] != tickets["assigned_team"]
    
    print(f"SLA Breaches Found: {tickets['sla_breach'].sum():,}")
    print(f"Team Mismatches Found: {tickets['team_mismatch'].sum():,}")

    # --- Rule 5: Order Join (Direct and Fallback) ---
    print("\n--- 5. Order Join ---")
    tickets["matched_order_id"] = tickets["order_id"]
    tickets["join_method"] = "none"
    tickets.loc[tickets["matched_order_id"].notna(), "join_method"] = "id"
    
    # Fallback missing orders via merge_asof (latest order before ticket creation)
    missing_order_mask = tickets["order_id"].isna()
    if missing_order_mask.sum() > 0:
        t_missing = tickets.loc[missing_order_mask, ["customer_id", "product_sku", "created_at"]].copy()
        t_missing_sorted = t_missing.sort_values("created_at")
        orders_sorted = orders.sort_values("order_date")
        
        fallback = pd.merge_asof(
            t_missing_sorted,
            orders_sorted[["order_date", "customer_id", "sku", "order_id"]].rename(columns={"order_id": "fb_order"}),
            left_on="created_at",
            right_on="order_date",
            left_by=["customer_id", "product_sku"],
            right_by=["customer_id", "sku"],
            direction="backward"
        )
        
        fallback.index = t_missing_sorted.index
        success = fallback["fb_order"].notna()
        
        tickets.loc[fallback[success].index, "matched_order_id"] = fallback.loc[success, "fb_order"]
        tickets.loc[fallback[success].index, "join_method"] = "fallback"

    order_to_lot = orders.set_index("order_id")["lot_code"].to_dict()
    tickets["lot_code"] = tickets["matched_order_id"].map(order_to_lot)
    
    print("Match Rate by Method:")
    print(tickets["join_method"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

    # --- Rule 6: Violations ---
    print("\n--- 6. Rule Violations ---")
    tickets["gw_over_cap"] = (tickets["refund_reason_code"] == "GW-OTHER") & (pd.to_numeric(tickets["refund_amount_inr"], errors="coerce") > 500)
    tickets["refund_and_replacement"] = tickets["refund_amount_inr"].notna() & (tickets["replacement_issued"] == "Y")
    
    print(f"Goodwill > 500 Violation: {tickets['gw_over_cap'].sum():,} flagged")
    print(f"Refund AND Replacement Violation: {tickets['refund_and_replacement'].sum():,} flagged")

    # --- Rule 7: Transfers ---
    print("\n--- 7. Transfers ---")
    print("Transfers field explicitly left blank for legacy_fd records.")

    # Save output
    out_file = OUTPUT / "tickets_clean.csv"
    tickets.to_csv(out_file, index=False)
    print(f"\nCleaned dataset saved: {out_file} ({len(tickets):,} rows, {tickets.shape[1]} columns)")

if __name__ == "__main__":
    main()