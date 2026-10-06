"""
02b_explore.py - Deep dive into business metrics and assumptions.
Run from the project root:  python src/02b_explore.py > outputs/explore_output.txt
"""
import pandas as pd
import numpy as np
from pathlib import Path

def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")

def main():
    DATA = Path(__file__).resolve().parent.parent / "data"
    OUTPUT = Path(__file__).resolve().parent.parent / "outputs"

    print("Loading data...")
    tickets = pd.read_csv(OUTPUT / "tickets_clean.csv", parse_dates=["created_at", "first_response_at", "resolved_at"])
    orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
    products = pd.read_csv(DATA / "products.csv")
    
    # ---------------------------------------------------------
    section("1. REAL RE-IMPORT CHECK (Cross-System Duplicates)")
    # ---------------------------------------------------------
    # Join tickets to itself to find matches across systems
    t_subset = tickets[['ticket_id', 'customer_id', 'product_sku', 'created_at', 'customer_message', 'source_system']]
    pairs = t_subset.merge(t_subset, on=['customer_id', 'product_sku'])
    
    # Filter to pairs across DIFFERENT source systems, avoid counting A-B and B-A
    cross_sys = pairs[(pairs['source_system_x'] < pairs['source_system_y'])].copy()
    
    # Exact match: created_at is identical
    exact_match = cross_sys[cross_sys['created_at_x'] == cross_sys['created_at_y']]
    
    # Message match: same text, not blank, within 2 days
    msg_valid = cross_sys['customer_message_x'].notna() & (cross_sys['customer_message_x'].str.strip() != "")
    msg_same = cross_sys['customer_message_x'] == cross_sys['customer_message_y']
    time_diff = (cross_sys['created_at_x'] - cross_sys['created_at_y']).abs() <= pd.Timedelta(days=2)
    msg_match = cross_sys[msg_valid & msg_same & time_diff]

    print("Exact matches (same time & product & customer) across systems:")
    print(exact_match.groupby(['source_system_x', 'source_system_y']).size().to_string())
    
    print("\nMessage matches (same text & product & customer, within 2 days) across systems:")
    print(msg_match.groupby(['source_system_x', 'source_system_y']).size().to_string())

    # ---------------------------------------------------------
    section("2. HAND-OFF MAP (Assigned vs Resolver Team)")
    # ---------------------------------------------------------
    closed_tk = tickets[tickets['status'].isin(['resolved', 'closed'])]
    
    print("All rows (Counts):")
    print(pd.crosstab(closed_tk['assigned_team'], closed_tk['resolver_team'], margins=True))
    print("\nAll rows (Row %):")
    print(pd.crosstab(closed_tk['assigned_team'], closed_tk['resolver_team'], normalize='index').mul(100).round(1))

    print("\nHelpdesk only (Row %):")
    hd_closed = closed_tk[closed_tk['source_system'] == 'helpdesk']
    print(pd.crosstab(hd_closed['assigned_team'], hd_closed['resolver_team'], normalize='index').mul(100).round(1))

    # ---------------------------------------------------------
    section("3. SLA BREACHES (Cost = Breaches * Rs 350)")
    # ---------------------------------------------------------
    def print_sla_stats(groupby_col):
        stats = tickets.groupby(groupby_col)['sla_breach'].agg(['mean', 'sum', 'count'])
        stats['mean'] = (stats['mean'] * 100).round(1).astype(str) + '%'
        stats['cost_rs'] = stats['sum'] * 350
        print(f"\nBy {groupby_col}:")
        print(stats.rename(columns={'mean': 'breach_rate', 'sum': 'breaches', 'count': 'total_tickets'}))

    tickets['hour'] = tickets['created_at'].dt.hour
    shift_map = {h: 'Night' if h < 6 or h >= 22 else 'Morning' if h < 14 else 'Day' for h in range(24)}
    tickets['shift'] = tickets['hour'].map(shift_map)
    tickets['month'] = tickets['created_at'].dt.to_period('M')

    print_sla_stats('channel')
    print_sla_stats('hour')
    print_sla_stats('shift')
    print_sla_stats('assigned_team')
    print_sla_stats('month')

    # ---------------------------------------------------------
    section("4. VOLUME DRIVERS (Products & Lots)")
    # ---------------------------------------------------------
    # Product pivot
    t_prod = tickets.merge(products[['sku', 'product_name']], left_on='product_sku', right_on='sku', how='left')
    prod_pivot = pd.crosstab(t_prod['month'], t_prod['product_name'])
    print("Tickets per month by product:")
    print(prod_pivot)

    # Lot code analysis (ID matched only)
    id_matched = tickets[tickets['join_method'] == 'id']
    tk_by_lot = id_matched.groupby('lot_code').size().rename('tickets')
    ord_by_lot = orders.groupby('lot_code').size().rename('orders')
    
    lots = pd.DataFrame({'tickets': tk_by_lot}).join(ord_by_lot).fillna(0)
    lots = lots[lots['orders'] >= 20].copy()
    lots['tk_per_100_ord'] = (lots['tickets'] / lots['orders'] * 100).round(1)
    
    print("\nTop 15 lots by tickets per 100 orders (min 20 orders):")
    top_lots = lots.sort_values('tk_per_100_ord', ascending=False).head(15)
    print(top_lots)
    
    overall_rate = (lots['tickets'].sum() / lots['orders'].sum() * 100)
    print(f"\nOverall average rate for these lots: {overall_rate:.1f} tickets per 100 orders")

    print("\nDeep dive: Top 5 lots specific issues (Counts):")
    top_5_codes = top_lots.head(5).index
    top_5_tk = id_matched[id_matched['lot_code'].isin(top_5_codes)]
    deep_dive = top_5_tk.groupby('lot_code').agg(
        refund_count=('refund_amount_inr', 'count'),
        replacement_count=('replacement_issued', lambda x: (x == 'Y').sum()),
        doa_count=('refund_reason_code', lambda x: (x == 'DOA-REPL').sum())
    )
    print(deep_dive.loc[top_5_codes])

    # ---------------------------------------------------------
    section("5. REPEAT CONTACTS (Cost by Channel)")
    # ---------------------------------------------------------
    t_res = tickets[tickets['status'].isin(['resolved', 'closed'])].copy()
    t_all = tickets[['customer_id', 'product_sku', 'created_at', 'ticket_id']].copy()
    
    # Merge resolved tickets with all tickets to find subsequent contacts
    repeats_merge = t_res[['ticket_id', 'customer_id', 'product_sku', 'resolved_at']].merge(
        t_all.rename(columns={'ticket_id': 'next_ticket', 'created_at': 'next_created_at'}),
        on=['customer_id', 'product_sku']
    )
    
    # Filter to contacts AFTER resolution, within 30 days
    is_repeat = (repeats_merge['next_created_at'] > repeats_merge['resolved_at']) & \
                (repeats_merge['next_created_at'] <= repeats_merge['resolved_at'] + pd.Timedelta(days=30))
    
    tickets_with_repeat = repeats_merge[is_repeat]['ticket_id'].unique()
    t_res['has_repeat'] = t_res['ticket_id'].isin(tickets_with_repeat)

    contact_cost = {'chat': 210, 'email': 260, 'voice': 520, 'social': 240}
    t_res['contact_cost'] = t_res['channel'].map(contact_cost)

    rep_stats = t_res.groupby(['assigned_team', 'channel'])['has_repeat'].agg(['mean', 'sum', 'count'])
    rep_stats['mean'] = (rep_stats['mean'] * 100).round(1).astype(str) + '%'
    rep_stats = rep_stats.reset_index()
    rep_stats['cost_rs'] = rep_stats['sum'] * rep_stats['channel'].map(contact_cost)
    
    print("Repeat rates and costs by Assigned Team and Channel:")
    print(rep_stats.rename(columns={'mean': 'repeat_rate', 'sum': 'repeats', 'count': 'resolved_tickets'}))
    print(f"\nTotal Repeat Cost (Resolved Tickets): Rs {rep_stats['cost_rs'].sum():,}")

    # ---------------------------------------------------------
    section("6. FALLBACK CHECK (Algorithm Accuracy)")
    # ---------------------------------------------------------
    has_order = tickets[tickets['order_id'].notna()].copy()
    has_order = has_order.sort_values('created_at')
    orders_sorted = orders.sort_values('order_date')
    
    fallback_test = pd.merge_asof(
        has_order[['ticket_id', 'created_at', 'customer_id', 'product_sku', 'order_id']],
        orders_sorted[['order_date', 'customer_id', 'sku', 'order_id']].rename(columns={'order_id': 'fb_order'}),
        left_on='created_at',
        right_on='order_date',
        left_by=['customer_id', 'product_sku'],
        right_by=['customer_id', 'sku'],
        direction='backward'
    )
    
    match_rate = (fallback_test['order_id'] == fallback_test['fb_order']).mean() * 100
    print(f"When order_id is present, the fallback logic matches it exactly: {match_rate:.1f}% of the time.")

if __name__ == "__main__":
    main()