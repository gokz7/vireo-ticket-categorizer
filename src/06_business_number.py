"""
06_business_number.py - Calculate final business metrics.
Run from the project root: python src/06_business_number.py
"""
import pandas as pd
import numpy as np
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

def main():
    ROOT = Path(__file__).resolve().parent.parent
    df = pd.read_csv(ROOT / "outputs" / "tickets_labelled.csv", parse_dates=["created_at"])
    df = df[df["in_window"]]
    
    agents = pd.read_csv(ROOT / "data" / "agents.csv")
    ag_count = agents.groupby("team")["agent_id"].nunique()

    # 1. Billing Handoffs and Volume
    ba = df[df["assigned_team"] == "Billing"]
    ba_handoffs = ba[ba["resolver_team"] != "Billing"]
    pct_handoffs_all = len(ba_handoffs) / len(ba) * 100
    
    ba_hd = ba[ba["source_system"] == "helpdesk"]
    ba_hd_handoffs = ba_hd[ba_hd["resolver_team"] != "Billing"]
    pct_handoffs_hd = len(ba_hd_handoffs) / len(ba_hd) * 100
    
    days_in_window = (df["created_at"].max() - df["created_at"].min()).days
    ann_vol = len(ba) / days_in_window * 365

    print(f"1. Billing-assigned: {len(ba)} tickets")
    print(f"   Handoffs (all rows): {pct_handoffs_all:.1f}%")
    print(f"   Handoffs (helpdesk-only): {pct_handoffs_hd:.1f}%")
    print(f"   Annual volume: {len(ba)} / {days_in_window} days * 365 = {ann_vol:.1f}")

    # 2. Cost Per Handoff
    df_apr = df[df["created_at"] >= "2025-04-01"]
    ba_apr = df_apr[df_apr["assigned_team"] == "Billing"]
    br_ho = ba_apr[ba_apr["resolver_team"] != "Billing"]["sla_breach"].mean()
    br_res = ba_apr[ba_apr["resolver_team"] == "Billing"]["sla_breach"].mean()
    
    excess_cost = (br_ho - br_res) * 350
    cost_per_ho = 305 + excess_cost
    
    print(f"2. Breach rate hand-offs (since Apr 1): {br_ho*100:.1f}%")
    print(f"   Breach rate resolved by Billing (since Apr 1): {br_res*100:.1f}%")
    print(f"   Excess breach cost: ({br_ho*100:.1f}% - {br_res*100:.1f}%) * 350 = Rs {excess_cost:.1f}")
    print(f"   Cost per hand-off: 305 + {excess_cost:.1f} = Rs {cost_per_ho:.1f}")

    # 3. Value Calculation
    avoided_ho = ann_vol * (pct_handoffs_all / 100 - 0.10)
    val_yr = avoided_ho * cost_per_ho
    hire_share = val_yr / 450000

    print(f"3. Avoided hand-offs/yr: {ann_vol:.1f} * ({pct_handoffs_all:.1f}% - 10.0%) = {avoided_ho:.1f}")
    print(f"   Value/yr: {avoided_ho:.1f} * Rs {cost_per_ho:.1f} = Rs {val_yr:,.1f}")
    print(f"   Share of one hire: Rs {val_yr:,.1f} / 450,000 = {hire_share:.1f}")

    # 4. Sensitivity (CANCELLATION mapped to Billing)
    canc_tks = df[df["issue_label"] == "CANCELLATION"]
    print(f"4. CANCELLATION tickets: {len(canc_tks)}")
    
    df_sens = df.copy()
    df_sens.loc[df_sens["issue_label"] == "CANCELLATION", "owner_team"] = "Billing"
    
    sens_tks = df_sens["owner_team"].value_counts().rename("tickets")
    sens_tbl = pd.DataFrame(sens_tks)
    sens_tbl["agents"] = sens_tbl.index.map(ag_count).fillna(0).astype(int)
    sens_tbl["tks_per_ag"] = np.where(sens_tbl["agents"] > 0, (sens_tbl["tickets"] / sens_tbl["agents"]).round(1), np.nan)
    
    # Exclude Unclassified and Escalations for the agent view as before
    clean_tbl = sens_tbl.drop(["Escalations & Warranty", "Unclassified"], errors="ignore")
    print(clean_tbl.to_string())

    # 5. API Cost
    print("5. paid API calls: 0, cost per run: Rs 0")

if __name__ == "__main__":
    main()