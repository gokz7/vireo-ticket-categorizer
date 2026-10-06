"""
04_validate.py - Validate categoriser accuracy against human labels.
Run from the project root:  python src/04_validate.py
"""
import pandas as pd
import math
from pathlib import Path

def get_owner(label, ch):
    if label == 'OTHER': return 'Unclassified'
    if label in ['PAYMENT_FAILED_OR_DEBITED', 'DUPLICATE_CHARGE', 'INVOICE_PRICE_COUPON']: return 'Billing'
    if label in ['REFUND_STATUS', 'RETURN_PICKUP', 'CANCELLATION']: return 'Returns Desk'
    if label in ['DELIVERY_NOT_RECEIVED', 'DAMAGED_OR_WRONG_ITEM']: return 'Logistics'
    if label == 'HARDWARE_FAULT_WARRANTY': return 'Escalations & Warranty'
    
    if ch in ['chat', 'social']: return 'Chat Frontline'
    if ch == 'email': return 'Email Frontline'
    return 'Voice Frontline'

def wilson_ci(k, n):
    if n == 0: return 0.0, 0.0
    p, z = k / n, 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return ((center - margin) / denom) * 100, ((center + margin) / denom) * 100

def main():
    ROOT = Path(__file__).resolve().parent.parent
    
    # Read from the validation directory instead of outputs
    sample = pd.read_csv(ROOT / "validation" / "hand_labels.csv")
    labelled = pd.read_csv(ROOT / "outputs" / "tickets_labelled.csv")
    
    df = sample[['ticket_id', 'human_label']].merge(labelled, on='ticket_id')
    
    mask = df['human_label'].notna() & (df['human_label'].str.strip() != "") & (df['human_label'] != "UNSURE")
    dropped = len(df) - mask.sum()
    df = df[mask].copy()
    
    print(f"Dropped {dropped} rows (blank or UNSURE).")
    
    n = len(df)
    if n == 0:
        print("No valid labels to validate.")
        return

    df['human_owner'] = df.apply(lambda x: get_owner(x['human_label'], x['channel']), axis=1)
    df['issue_match'] = df['human_label'] == df['issue_label']
    df['owner_match'] = df['human_owner'] == df['owner_team']
    
    df.to_csv(ROOT / "outputs" / "validation_detail.csv", index=False)
    
    iss_k = df['issue_match'].sum()
    own_k = df['owner_match'].sum()
    iss_ci = wilson_ci(iss_k, n)
    own_ci = wilson_ci(own_k, n)
    
    print(f"1. n={n} | Issue Acc: {iss_k/n*100:.1f}% (95% CI: {iss_ci[0]:.1f}%-{iss_ci[1]:.1f}%)")
    print(f"2. Owner Acc: {own_k/n*100:.1f}% (95% CI: {own_ci[0]:.1f}%-{own_ci[1]:.1f}%)")
    
    bot_b = df[df['category'] == 'Billing & Payments']
    n_bot = len(bot_b)
    if n_bot > 0:
        print(f"3. Bot 'Billing & Payments' (n={n_bot}): Issue {bot_b['issue_match'].mean()*100:.1f}%, Owner {bot_b['owner_match'].mean()*100:.1f}%")
        
    print("\n4. Top 8 Confusions (Human -> Auto):")
    conf = df[~df['issue_match']].groupby(['human_label', 'issue_label']).size().nlargest(8)
    for (h, a), v in conf.items():
        print(f"   {h} -> {a}: {v}")
        
    print("\n5. Accuracy by Channel:")
    for ch, grp in df.groupby('channel'):
        print(f"   {ch} (n={len(grp)}): {grp['issue_match'].mean()*100:.1f}%")
        
    print("\n6. OTHER vs Rest Accuracy:")
    other_mask = df['issue_label'] == 'OTHER'
    for name, m in [("OTHER", other_mask), ("Rest", ~other_mask)]:
        grp = df[m]
        if len(grp) > 0:
            print(f"   {name} (n={len(grp)}): {grp['issue_match'].mean()*100:.1f}%")

if __name__ == "__main__":
    main()