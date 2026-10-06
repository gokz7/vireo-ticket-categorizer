"""
05_charts.py - Generate ticket analytics tables and charts.
Run from the project root:  python src/05_charts.py
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

def main():
    ROOT = Path(__file__).resolve().parent.parent
    OUTPUT = ROOT / "outputs"

    # Load data
    df = pd.read_csv(OUTPUT / "tickets_labelled.csv", parse_dates=["created_at"])
    df = df[df["in_window"]].copy()
    df["month"] = df["created_at"].dt.to_period("M").astype(str)

    agents = pd.read_csv(ROOT / "data" / "agents.csv")
    ag_count = agents.groupby("team")["agent_id"].nunique()

    # Table generator
    def make_table(col):
        tks = df[col].value_counts().rename("tickets")
        pct = (tks / len(df) * 100).round(1).rename("pct_total")
        res = pd.concat([tks, pct], axis=1)
        res["agents"] = res.index.map(ag_count).fillna(0).astype(int)
        res["tks_per_ag"] = np.where(res["agents"] > 0, (res["tickets"] / res["agents"]).round(1), np.nan)
        return res

    own_tbl = make_table("owner_team")
    own_tbl.loc[own_tbl.index.isin(["Escalations & Warranty", "Unclassified"]), "tks_per_ag"] = pd.NA
    
    ass_tbl = make_table("assigned_team")
    ass_tbl.loc[ass_tbl.index == "Escalations & Warranty", "tks_per_ag"] = pd.NA

    print("1. Table by owner_team:")
    print(own_tbl.to_string())
    print("\n2. Table by assigned_team:")
    print(ass_tbl.to_string())

    # Sensitivity Calculation
    unclass = own_tbl.loc["Unclassified", "tickets"] if "Unclassified" in own_tbl.index else 0
    class_tks = len(df) - unclass

    def get_sens(teams):
        tks = own_tbl.reindex(teams)["tickets"].sum()
        ags = ag_count.reindex(teams).sum()
        adj_tks = tks + (tks / class_tks) * unclass if class_tks > 0 else tks
        return round(adj_tks / ags, 1) if ags > 0 else np.nan

    print("\n3. Sensitivity (Unclassified Pro-Rated):")
    print(f"Billing: {get_sens(['Billing'])} | Logistics: {get_sens(['Logistics'])} | Returns Desk: {get_sens(['Returns Desk'])}")
    print(f"Frontline (Combined): {get_sens(['Chat Frontline', 'Email Frontline', 'Voice Frontline'])}")

    # Chart 1: Monthly Tickets by Issue Label (Stacked Bar)
    issue_mo = df.groupby(["month", "issue_label"]).size().unstack(fill_value=0)
    ax = issue_mo.plot(kind="bar", stacked=True, figsize=(10, 6), colormap="tab20")
    ax.set_title("Monthly Tickets by Issue Label")
    ax.set_ylabel("Tickets")
    plt.xticks(rotation=45, ha="right")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    plt.savefig(OUTPUT / "monthly_tickets_by_issue.png", dpi=150)
    plt.close()

    # Chart 2: Monthly Owner vs Assigned (Two Panels)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    own_mo = df.groupby(["month", "owner_team"]).size().unstack(fill_value=0)
    ass_mo = df.groupby(["month", "assigned_team"]).size().unstack(fill_value=0)
    
    own_mo.plot(kind="line", marker="o", ax=ax1, colormap="tab10")
    ax1.set_title("Tickets by True Owner Team")
    ax1.set_ylabel("Tickets")
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend(fontsize='small')
    
    ass_mo.plot(kind="line", marker="o", ax=ax2, colormap="tab10")
    ax2.set_title("Tickets by Bot Assigned Team")
    ax2.tick_params(axis='x', rotation=45)
    ax2.legend(fontsize='small')
    
    plt.tight_layout()
    plt.savefig(OUTPUT / "monthly_tickets_by_owner.png", dpi=150)
    plt.close()

if __name__ == "__main__":
    main()