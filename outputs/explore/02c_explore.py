"""
02c_explore.py - Full business metric dive (filtered to in_window == True).
Saves complete tables to outputs/explore/ CSVs to prevent truncation.
Run from the project root:  python src/02c_explore.py > outputs/explore_output.txt
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Fix display truncation
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 250)

def section(title):
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")

def save_csv(df, filename, out_dir):
    out_path = out_dir / filename
    df.to_csv(out_path)
    print(f" -> Saved to outputs/explore/{filename}")

def main():
    DATA = Path(__file__).resolve().parent.parent / "data"
    OUTPUT = Path(__file__).resolve().parent.parent / "outputs"
    EXPLORE_DIR = OUTPUT / "explore"
    EXPLORE_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    tickets = pd.read_csv(OUTPUT / "tickets_clean.csv", 
                          parse_dates=["created_at", "first_response_at", "resolved_at"])
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
    products = pd.read_csv(DATA / "products.csv")
    agents = pd.read_csv(DATA / "agents.csv")

    # Filter to in_window == True
    pre_filter_count = len(tickets)
    tickets = tickets[tickets['in_window'] == True].copy()
    print(f"Filtered to in_window == True: {len(tickets):,} rows (dropped {pre_filter_count - len(tickets):,})")
    
    # Generate common features
    tickets['month'] = tickets['created_at'].dt.to_period('M')
    tickets['hour'] = tickets['created_at'].dt.hour
    shift_map = {h: 'Night' if h < 6 or h >= 22 else 'Morning' if h < 14 else 'Day' for h in range(24)}
    tickets['shift'] = tickets['hour'].map(shift_map)

    # ---------------------------------------------------------
    section("1. HAND-OFF MAP (Resolved & Closed)")
    # ---------------------------------------------------------
    t_closed = tickets[tickets['status'].isin(['resolved', 'closed'])]
    
    handoff_cnt = pd.crosstab(t_closed['assigned_team'], t_closed['resolver_team'], margins=True)
    handoff_pct = pd.crosstab(t_closed['assigned_team'], t_closed['resolver_team'], normalize='index').mul(100).round(1)
    
    print("\nCounts:")
    print(handoff_cnt)
    save_csv(handoff_cnt, "1_handoff_counts.csv", EXPLORE_DIR)
    
    print("\nRow %:")
    print(handoff_pct)
    save_csv(handoff_pct, "1_handoff_pct.csv", EXPLORE_DIR)

    hd_closed = t_closed[t_closed['source_system'] == 'helpdesk']
    zero_transfers = hd_closed[hd_closed['transfers'] == 0]
    mismatch_rate = (zero_transfers['assigned_team'] != zero_transfers['resolver_team']).mean() * 100
    print(f"\nAmong Helpdesk rows with transfers == 0, resolver != assigned: {mismatch_rate:.1f}%")

    # ---------------------------------------------------------
    section("2. SLA BREACHES")
    # ---------------------------------------------------------
    def agg_breach(df, index_cols, file_name):
        res = df.groupby(index_cols)['sla_breach'].agg(
            breach_rate=lambda x: round(x.mean() * 100, 1),
            breach_count='sum',
            total='count'
        )
        print(f"\nBy {index_cols}:")
        print(res)
        save_csv(res, file_name, EXPLORE_DIR)

    agg_breach(tickets, ['assigned_team', 'channel'], "2_breach_by_team_channel.csv")
    
    billing_tk = tickets[tickets['assigned_team'] == 'Billing']
    agg_breach(billing_tk, ['shift'], "2_breach_billing_shift.csv")
    agg_breach(billing_tk, ['hour'], "2_breach_billing_hour.csv")
    
    agg_breach(tickets, ['resolver_team'], "2_breach_by_resolver.csv")

    # ---------------------------------------------------------
    section("3. ROSTER & TICKETS PER AGENT")
    # ---------------------------------------------------------
    roster_hc = agents.groupby(['team', 'shift', 'site']).size().reset_index(name='headcount')
    print("\nHeadcount by Team x Shift x Site:")
    print(roster_hc)
    save_csv(roster_hc, "3_roster_headcount.csv", EXPLORE_DIR)

    agents['from_month'] = pd.to_datetime(agents['from_date']).dt.to_period('M')
    agents_by_month = agents.groupby('from_month').size().reset_index(name='new_agents')
    print("\nAgents by from_date month:")
    print(agents_by_month)
    save_csv(agents_by_month, "3_roster_agents_by_month.csv", EXPLORE_DIR)

    # Tickets per agent per month (Exclude Tier 2)
    months = sorted(tickets['month'].unique())
    active_records = []
    for m in months:
        active = agents[agents['from_month'] <= m]
        active_by_team = active.groupby('team').size()
        for t, count in active_by_team.items():
            active_records.append({'month': m, 'team': t, 'active_agents': count})
    active_df = pd.DataFrame(active_records)

    # Use resolver_team to measure work completed
    t1_tickets = tickets[tickets['resolver_team'] != 'Escalations & Warranty']
    tk_by_team_mo = t1_tickets.groupby(['resolver_team', 'month']).size().reset_index(name='tickets')
    
    tk_per_agent = tk_by_team_mo.merge(active_df, left_on=['resolver_team', 'month'], right_on=['team', 'month'])
    tk_per_agent['tickets_per_agent'] = (tk_per_agent['tickets'] / tk_per_agent['active_agents']).round(1)
    tk_per_agent = tk_per_agent[['month', 'team', 'active_agents', 'tickets', 'tickets_per_agent']]
    
    print("\nTickets per Agent per Month (Tier 1 only):")
    print(tk_per_agent.head(15))
    save_csv(tk_per_agent, "3_roster_tickets_per_agent.csv", EXPLORE_DIR)

    # ---------------------------------------------------------
    section("4. VOLUME DRIVERS")
    # ---------------------------------------------------------
    t_prod = tickets.merge(products[['sku', 'product_name']], left_on='product_sku', right_on='sku')
    o_prod = orders.merge(products[['sku', 'product_name']], on='sku')
    o_prod['month'] = o_prod['order_date'].dt.to_period('M')
    
    tk_mo_prod = pd.crosstab(t_prod['month'], t_prod['product_name'])
    ord_mo_prod = pd.crosstab(o_prod['month'], o_prod['product_name'])
    
    print("\nOrders per month by product:")
    print(ord_mo_prod)
    save_csv(ord_mo_prod, "4_orders_per_month.csv", EXPLORE_DIR)
    
    print("\nTickets per month by product:")
    print(tk_mo_prod)
    save_csv(tk_mo_prod, "4_tickets_per_month.csv", EXPLORE_DIR)

    rate_mo_prod = (tk_mo_prod / ord_mo_prod * 100).round(1).fillna(0)
    print("\nTickets per 100 orders by product by month:")
    print(rate_mo_prod)
    save_csv(rate_mo_prod, "4_tickets_per_100_orders.csv", EXPLORE_DIR)

    pattern = 'charging case|led|not charging'
    t_prod['has_issue'] = t_prod['customer_message'].str.contains(pattern, case=False, na=False) | \
                          t_prod['agent_notes'].str.contains(pattern, case=False, na=False)
    issue_share = (t_prod.groupby('month')['has_issue'].mean() * 100).round(1).reset_index(name='issue_share_pct')
    print("\nShare of tickets containing case/charging keywords by month:")
    print(issue_share)
    save_csv(issue_share, "4_charging_issue_share.csv", EXPLORE_DIR)

    # ---------------------------------------------------------
    section("5. REPEAT CONTACTS")
    # ---------------------------------------------------------
    t_res = tickets[tickets['status'].isin(['resolved', 'closed'])].copy()
    t_res = t_res[t_res['resolved_at'].notna()]
    t_all = tickets[['ticket_id', 'customer_id', 'product_sku', 'created_at']].copy()
    
    merged = t_res[['ticket_id', 'customer_id', 'product_sku', 'resolved_at']].merge(
        t_all.rename(columns={'ticket_id': 'next_ticket', 'created_at': 'next_created_at'}),
        on=['customer_id', 'product_sku']
    )
    
    # Fix DeprecationWarning by using pd.to_timedelta
    is_repeat = (merged['next_created_at'] > merged['resolved_at']) & \
                (merged['next_created_at'] <= merged['resolved_at'] + pd.to_timedelta(30, unit='d'))
    
    repeat_tids = merged[is_repeat]['ticket_id'].unique()
    t_res['is_repeat'] = t_res['ticket_id'].isin(repeat_tids)
    
    cost_map = {'chat': 210, 'email': 260, 'voice': 520, 'social': 240}
    t_res['contact_cost'] = t_res['channel'].map(cost_map)
    
    repeats = t_res.groupby('assigned_team').agg(
        repeats=('is_repeat', 'sum'),
        resolved_tickets=('ticket_id', 'count'),
    )
    repeats['repeat_rate_%'] = (repeats['repeats'] / repeats['resolved_tickets'] * 100).round(1)
    repeats['cost_rs'] = t_res[t_res['is_repeat']].groupby('assigned_team')['contact_cost'].sum().fillna(0)
    
    print("\nRepeats by Assigned Team:")
    print(repeats)
    save_csv(repeats, "5_repeat_contacts.csv", EXPLORE_DIR)

    # ---------------------------------------------------------
    section("6. TRANSFERS (Helpdesk Only)")
    # ---------------------------------------------------------
    hd = tickets[tickets['source_system'] == 'helpdesk'].copy()
    hd['transfers'] = pd.to_numeric(hd['transfers'], errors='coerce').fillna(0)
    
    transfers = hd.groupby('assigned_team').agg(
        tickets=('ticket_id', 'count'),
        tickets_with_transfers=('transfers', lambda x: (x >= 1).sum()),
        total_transfers=('transfers', 'sum')
    )
    transfers['total_transfers'] = transfers['total_transfers'].astype(int)
    transfers['cost_rs'] = transfers['total_transfers'] * 305
    
    print("\nTransfers by Assigned Team (Cost = Rs 305/transfer):")
    print(transfers)
    save_csv(transfers, "6_transfers_by_team.csv", EXPLORE_DIR)

if __name__ == "__main__":
    main()