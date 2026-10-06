import pandas as pd
import numpy as np

t = pd.read_csv("outputs/tickets_clean.csv", parse_dates=["created_at", "resolved_at"])
t = t[t["in_window"]]
a = pd.read_csv("data/agents.csv", parse_dates=["from_date"])

print("1. Billing->Logistics Handoff by channel:")
print(t[(t["assigned_team"] == "Billing") & (t["resolver_team"] == "Logistics")]["channel"].value_counts().to_string())
print("Billing chat total:", len(t[(t["assigned_team"] == "Billing") & (t["channel"] == "chat")]))

print("\n2. Helpdesk Transfers:")
hd = t[t["source_system"] == "helpdesk"].copy()
hd["transfers"] = pd.to_numeric(hd["transfers"], errors="coerce").fillna(0)
print(hd.groupby("assigned_team")["transfers"].agg(tks="count", ge1=lambda x: (x>=1).sum(), tot="sum"))

print("\n3. Breach Rate % by Resolver:")
print((t.groupby("resolver_team")["sla_breach"].mean() * 100).round(1).to_string())

print("\n4. Billing HD Repeat Rate (transfers == 0 vs >= 1):")
b_res = hd[(hd["assigned_team"] == "Billing") & hd["status"].isin(["resolved", "closed"]) & hd["resolved_at"].notna()].copy()
merged = b_res[["ticket_id", "customer_id", "product_sku", "resolved_at"]].merge(
    t[["customer_id", "product_sku", "created_at"]].rename(columns={"created_at": "next_c"}), on=["customer_id", "product_sku"])
reps = merged[(merged["next_c"] > merged["resolved_at"]) & (merged["next_c"] <= merged["resolved_at"] + pd.to_timedelta(30, unit="d"))]
b_res["is_repeat"] = b_res["ticket_id"].isin(reps["ticket_id"])
b_res["t_group"] = np.where(b_res["transfers"] >= 1, ">=1", "0")
print(b_res.groupby("t_group")["is_repeat"].mean().mul(100).round(1).to_string())

print("\n5. Roster:")
print(a.groupby("team")["from_date"].agg(["min", "max", "count"]))