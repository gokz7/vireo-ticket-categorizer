"""03b_other_peek.py - look at tickets the rules could not classify."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "outputs" / "tickets_labelled.csv")
df = df[df["in_window"].astype(str) == "True"]
other = df[df["issue_label"] == "OTHER"]

print(f"OTHER tickets: {len(other):,} of {len(df):,}")
print("\nBy bot category (% of OTHER):")
print((other["category"].value_counts(normalize=True) * 100).round(1).head(8))
print("\nWhat the agent notes say about these (notes_label, top 8):")
print(other["notes_label"].value_counts().head(8))

bill = other[other["category"] == "Billing & Payments"]
rest = other[other["category"] != "Billing & Payments"]
sample = pd.concat([bill.sample(min(10, len(bill)), random_state=1),
                    rest.sample(min(20, len(rest)), random_state=1)])
print("\n30 samples (tag | channel | message):")
for _, r in sample.iterrows():
    msg = str(r["customer_message"]).replace("\n", " ")[:110]
    print(f"{r['category'][:12]:12} | {r['channel'][:5]:5} | {msg}")