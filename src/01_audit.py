"""
01_audit.py - READ-ONLY data audit. No cleaning, no modelling.
Run from the project root:  python src/01_audit.py
Tip: save the output with:  python src/01_audit.py > outputs/audit_output.txt
"""
from pathlib import Path
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 100)

DATA = Path(__file__).resolve().parent.parent / "data"


def section(title):
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def to_dt(series):
    """Parse dates; report how many non-blank values failed to parse."""
    try:
        parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    except (ValueError, TypeError):  # older pandas without format="mixed"
        parsed = pd.to_datetime(series, errors="coerce")
    bad = int((parsed.isna() & series.notna()).sum())
    print(f"  {series.name}: {bad} unparseable non-blank values")
    return parsed


def main():
    try:
        tickets = pd.read_csv(DATA / "tickets.csv")
        agents = pd.read_csv(DATA / "agents.csv")
        orders = pd.read_csv(DATA / "orders.csv")
        customers = pd.read_csv(DATA / "customers.csv")
        products = pd.read_csv(DATA / "products.csv")
    except FileNotFoundError as e:
        print(f"Missing file: {e}. Check the 5 CSVs are in {DATA}")
        return

    section("1. SHAPES, DATE PARSING, MISSING VALUES")
    for name, df in [("tickets", tickets), ("agents", agents), ("orders", orders),
                     ("customers", customers), ("products", products)]:
        print(f"{name}: {df.shape[0]:,} rows, {df.shape[1]} columns")
    print("\nDate parsing (tickets):")
    for c in ["created_at", "first_response_at", "resolved_at"]:
        tickets[c] = to_dt(tickets[c])
    miss = pd.DataFrame({"missing": tickets.isna().sum(),
                         "pct": (tickets.isna().mean() * 100).round(1)})
    print("\nMissing values in tickets (all columns):")
    print(miss)

    section("2. DUPLICATES (H1)")
    n_dup_ids = int(tickets["ticket_id"].duplicated().sum())
    n_dup_rows = int(tickets.duplicated().sum())
    print(f"Repeated ticket_id rows: {n_dup_ids:,}")
    print(f"Fully identical rows:    {n_dup_rows:,}")
    dups = tickets[tickets["ticket_id"].duplicated(keep=False)].sort_values("ticket_id")
    if len(dups):
        print("\nSource systems among duplicated rows:")
        print(dups["source_system"].value_counts())
        print("\nColumns that DIFFER between copies of the same ticket_id")
        print("(number of ticket_ids where the copies disagree):")
        differs = dups.groupby("ticket_id").agg(lambda s: s.nunique(dropna=False) > 1).sum()
        print(differs[differs > 0].sort_values(ascending=False))
        print("\nFirst 3 duplicate pairs (key columns):")
        cols = ["ticket_id", "source_system", "created_at", "resolved_at",
                "assigned_team", "category", "refund_amount_inr", "transfers"]
        print(dups[cols].head(6))

    section("3. VOLUMES (raw vs de-duplicated) - checking Priya's 22% / 16%")
    dedup = tickets.drop_duplicates(subset="ticket_id", keep="first")
    print(f"Raw rows: {len(tickets):,} | unique ticket_ids: {len(dedup):,}")
    print(f"Date range: {tickets['created_at'].min()} -> {tickets['created_at'].max()}")

    print("\nCategory share % (raw vs de-duplicated):")
    cat = pd.DataFrame({
        "raw_%": (tickets["category"].value_counts(normalize=True, dropna=False) * 100).round(1),
        "dedup_%": (dedup["category"].value_counts(normalize=True, dropna=False) * 100).round(1),
        "dedup_n": dedup["category"].value_counts(dropna=False)})
    print(cat)

    print("\nAssigned-team share % (raw vs de-duplicated):")
    team = pd.DataFrame({
        "raw_%": (tickets["assigned_team"].value_counts(normalize=True, dropna=False) * 100).round(1),
        "dedup_%": (dedup["assigned_team"].value_counts(normalize=True, dropna=False) * 100).round(1),
        "dedup_n": dedup["assigned_team"].value_counts(dropna=False)})
    print(team)

    print("\nTickets per month (raw), by source_system:")
    tickets["month"] = tickets["created_at"].dt.to_period("M")
    print(pd.crosstab(tickets["month"], tickets["source_system"], margins=True))

    section("4. TIMESTAMP CHECK (H2) - minutes, by source_system")
    tickets["resolve_mins"] = (tickets["resolved_at"] - tickets["created_at"]).dt.total_seconds() / 60
    tickets["first_resp_mins"] = (tickets["first_response_at"] - tickets["created_at"]).dt.total_seconds() / 60
    done = tickets[tickets["status"] == "resolved"]
    q = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95]
    print("created -> resolved (status=resolved only):")
    print(done.groupby("source_system")["resolve_mins"].describe(percentiles=q).round(0))
    print("\ncreated -> first response (all rows):")
    print(tickets.groupby("source_system")["first_resp_mins"].describe(percentiles=q).round(0))
    print("\nNegative resolve times by source_system:")
    print((tickets["resolve_mins"] < 0).groupby(tickets["source_system"]).sum())
    print("\nResolved before first response, by source_system:")
    print((tickets["resolved_at"] < tickets["first_response_at"]).groupby(tickets["source_system"]).sum())

    section("5. REFUND SCALE (H3) - by source_system")
    raw_ref = tickets["refund_amount_inr"]
    ref = pd.to_numeric(raw_ref, errors="coerce")
    failed = int((ref.isna() & raw_ref.notna()).sum())
    print(f"Non-blank refund values that could not convert to a number: {failed}")
    tickets["refund_num"] = ref
    print(tickets.groupby("source_system")["refund_num"]
          .agg(["count", "median", "mean", "max"]).round(1))
    print("\nMedian refund by source_system and reason code:")
    print(tickets.pivot_table(index="refund_reason_code", columns="source_system",
                              values="refund_num", aggfunc="median").round(0))

    section("6. TRANSFERS (blank vs zero), by source_system")
    print("Non-blank count:")
    print(tickets.groupby("source_system")["transfers"].count())
    print("\nValue counts (helpdesk only):")
    print(tickets.loc[tickets["source_system"] == "helpdesk", "transfers"]
          .value_counts(dropna=False).sort_index())

    section("7. OTHER DISTRIBUTIONS")
    for col in ["status", "channel", "priority", "refund_reason_code",
                "replacement_issued", "csat_score"]:
        print(f"\n{col}:")
        print(tickets[col].value_counts(dropna=False))
    print(f"\nTickets with blank order_id: {tickets['order_id'].isna().mean() * 100:.1f}%")

    section("8. ROSTER (agents.csv)")
    print(f"Rows: {len(agents)} | unique agent_id: {agents['agent_id'].nunique()}")
    multi = agents["agent_id"].value_counts()
    print(f"Agents with more than 1 roster row: {(multi > 1).sum()}")
    names = agents.groupby("name")["agent_id"].nunique()
    print("Display names shared by different agent_ids:")
    print(names[names > 1])
    print(f"Open-ended assignments (blank to_date): {agents['to_date'].isna().sum()}")
    print("\nRoster rows by team and tier:")
    print(agents.groupby(["team", "tier"]).size())

    section("9. LOT CODES (H8) - tickets per lot (rows with a matched order only)")
    joined = tickets.merge(orders[["order_id", "lot_code"]], on="order_id", how="left")
    print(f"Tickets matched to an order: {joined['lot_code'].notna().sum():,} of {len(joined):,}")
    print("Top 10 lot_codes by ticket count:")
    print(joined["lot_code"].value_counts().head(10))
    print(f"\nLot summary: {orders['lot_code'].nunique()} lots, "
          f"median {orders['lot_code'].value_counts().median():.0f} orders per lot")

    section("10. FREE-TEXT SAMPLES (15 random) - tag is the BOT's guess, not truth")
    pool = tickets.dropna(subset=["customer_message", "agent_notes"])
    for _, r in pool.sample(15, random_state=42).iterrows():
        print(f"\n#{r['ticket_id']} | bot tag: {r['category']} | first routed: {r['assigned_team']} "
              f"| {r['channel']} | {r['source_system']}")
        print(f"  Customer: {str(r['customer_message']).replace(chr(10), ' ')[:200]}")
        print(f"  Agent:    {str(r['agent_notes']).replace(chr(10), ' ')[:200]}")


if __name__ == "__main__":
    main()