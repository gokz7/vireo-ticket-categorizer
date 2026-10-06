import pandas as pd

t = pd.read_csv("outputs/tickets_clean.csv")
t = t[t["in_window"]]

print("1. Billing-assigned chat tickets:")
q1 = t[(t["assigned_team"] == "Billing") & (t["channel"] == "chat") & t["resolver_team"].isin(["Billing", "Logistics"])]
print(q1.groupby("resolver_team")["sla_breach"].agg(breach_pct=lambda x: (x.mean()*100).round(1), count="sum"))

print("\n2. Logistics-resolved tickets:")
q2 = t[(t["resolver_team"] == "Logistics") & t["assigned_team"].isin(["Billing", "Logistics"])]
print(q2.groupby("assigned_team")["sla_breach"].agg(breach_pct=lambda x: (x.mean()*100).round(1), count="sum"))

print("\n3. Ticket ID gaps:")
nums = t["ticket_id"].str.extract(r'(\d+)')[0].astype(int)
span = nums.max() - nums.min() + 1
print(f"Span (max-min+1): {span} | Row count: {len(t)} | Missing IDs: {span - len(t)}")