"""
03_categorise.py - Rule-based categorisation engine.
Run from the project root:  python src/03_categorise.py
"""
import pandas as pd
import numpy as np
import re
from pathlib import Path
from collections import Counter

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 250)

def extract_target_text(text):
    if not isinstance(text, str): return ""
    text = re.sub(r'\s+', ' ', str(text).lower()).strip()
    if 'issue:' in text:
        match = re.search(r'issue:(.*?)(?:tried:|$)', text)
        if match: text = match.group(1).strip()
    return text

def apply_rules(text):
    if not text: return "FALLBACK", "OTHER"
    
    rules = [
        (r'not delivered|doorstep|courier|awb|shipment|haven\'t received my order|has not been delivered|delayed|tracking|where is my order|transit|paid.*confirmed.*then nothing|transaction done.*where is my stuff|nothing in hand|waiting for something to show up|status stuck on shipped|days and counting|still waiting.*(order|ship|parcel|delivery|arrive)|change delivery address|going to the old flat|days since payment.*no idea where', 'del_not_recv', 'DELIVERY_NOT_RECEIVED'),
        (r'damaged|wrong product|wrong item|got something else|what\'s inside is not what i paid for|box says.*but inside is not|reshipment|ordered black.*got white|completely differen|parcel looked like it was kicked|has a crack|screen has a crack', 'damaged_wrong', 'DAMAGED_OR_WRONG_ITEM'),
        (r'one of them is just decoration|(left|right).*(one|bud|side).*(does not wake up|not working|dead)|not responding to touch|stopped working|dead|no led|doa|rma|defect|warranty|not working at all|won\'t turn on|metal pin fell out|no light comes on.*plug it in|tap ten times for one swipe|screen lights up but does nothin|screen is u.*responsive|no power on', 'hw_dead_wty', 'HARDWARE_FAULT_WARRANTY'),
        (r'reverse pickup|pickup|return request|packed the box|ordered this without asking.*please reverse', 'return_pickup', 'RETURN_PICKUP'),
        (r'where is the money for the return|money for the return|refund.*(pending|not|waiting|where)|refund not (received|credited)|waiting for my refund|amount is nowhere|no money|refund status|refund pending|refund of rs|picked up the item.*my account|sent the unit in.*heard nothing', 'refund_status', 'REFUND_STATUS'),
        (r'ordered the wrong colour.*don\'t ship|don\'t ship it|cancel.*dispatch|cancel', 'cancellation', 'CANCELLATION'),
        (r'paid once.*statement disagrees|charged more than once|charged twice|twice|duplicate', 'dup_charge', 'DUPLICATE_CHARGE'),
        (r'invoice.*(404|pdf|link|missing)|bill with.*gst|gstin|offer vanished|festive offer|promo code.*(invalid|not working)|invoice|discount|price|coupon', 'inv_price', 'INVOICE_PRICE_COUPON'),
        (r'payment (deducted|debited)|no order|payment failed|money deducted|payment page said success|money debited but order not', 'pay_fail_deduct', 'PAYMENT_FAILED_OR_DEBITED'),
        (r'phone doesn[\' ]?t see it|not in the list|doesn[\' ]?t show up in bluetooth|bluetooth|pairing|connect|disconnect|cannot pair', 'connectivity', 'CONNECTIVITY'),
        (r'dies by lunchtime|drains|battery.*(fast|quick|light)|charg|battery|never gets the green li', 'charging_bat', 'CHARGING_BATTERY'),
        (r'sounds like it is coming from one direction|one direction|one ear|crackling|volume|mute|sound|audio|static noise|mic not working', 'audio_qual', 'AUDIO_QUALITY'),
        (r'spinning circle|stuck loading|app|firmware|update', 'app_fw', 'APP_FIRMWARE'),
        (r'locked out|login|password|account', 'account_login', 'ACCOUNT_LOGIN'),
        (r'does.*work with.*(iphone|android|samsung)|compatible|compatibility|waterproof|shower|talk to a|before i buy|spec sheet', 'product_enq', 'PRODUCT_ENQUIRY')
    ]
    
    for pattern, rule_name, label in rules:
        if re.search(pattern, text):
            return rule_name, label
    return "FALLBACK", "OTHER"

def get_owner(row):
    label, ch = row['issue_label'], row['channel']
    if label == 'OTHER': return 'Unclassified'
    if label in ['PAYMENT_FAILED_OR_DEBITED', 'DUPLICATE_CHARGE', 'INVOICE_PRICE_COUPON']: return 'Billing'
    if label in ['REFUND_STATUS', 'RETURN_PICKUP', 'CANCELLATION']: return 'Returns Desk'
    if label in ['DELIVERY_NOT_RECEIVED', 'DAMAGED_OR_WRONG_ITEM']: return 'Logistics'
    if label == 'HARDWARE_FAULT_WARRANTY': return 'Escalations & Warranty'
    
    if ch in ['chat', 'social']: return 'Chat Frontline'
    if ch == 'email': return 'Email Frontline'
    return 'Voice Frontline'

def get_bigrams(text):
    stopwords = {'the','is','to','and','my','for','it','on','in','of','i','a','with','that','this','not','but','have','as','at','be','was','me','so','just','out'}
    words = [w for w in re.findall(r'[a-z]+', str(text).lower()) if w not in stopwords]
    return [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]

def main():
    DATA = Path(__file__).resolve().parent.parent / "outputs"
    df = pd.read_csv(DATA / "tickets_clean.csv")
    
    df['msg_ext'] = df['customer_message'].apply(extract_target_text)
    df['note_ext'] = df['agent_notes'].apply(extract_target_text)
    
    rules_applied = df['msg_ext'].apply(apply_rules)
    df['rule_name'] = rules_applied.apply(lambda x: x[0])
    df['issue_label'] = rules_applied.apply(lambda x: x[1])
    df['notes_label'] = df['note_ext'].apply(lambda x: apply_rules(x)[1])
    df['owner_team'] = df.apply(get_owner, axis=1)
    
    df.drop(columns=['msg_ext', 'note_ext'], inplace=True)
    df.to_csv(DATA / "tickets_labelled.csv", index=False)
    
    in_win = df[df['in_window']].copy()
    in_win['month'] = pd.to_datetime(in_win['created_at']).dt.to_period('M')
    in_win.groupby(['month', 'issue_label']).size().reset_index(name='tickets').to_csv(DATA / "monthly_tickets_by_issue.csv", index=False)
    in_win.groupby(['month', 'owner_team']).size().reset_index(name='tickets').to_csv(DATA / "monthly_tickets_by_owner.csv", index=False)
    
    # Only generate the random label sample if it does not already exist
    sample_path = DATA / "label_sample.csv"
    if not sample_path.exists():
        sample = in_win[['ticket_id', 'channel', 'customer_message', 'agent_notes']].sample(100, random_state=42).copy()
        sample['human_label'] = ""
        sample.to_csv(sample_path, index=False)
    
    other_df = in_win[in_win['issue_label'] == 'OTHER']
    print(f"1. % OTHER: {(len(other_df) / len(in_win)) * 100:.1f}%")
    print("\n2. Billing-Assigned True Owners:")
    print(in_win[in_win['assigned_team'] == 'Billing']['owner_team'].value_counts().to_string())

if __name__ == "__main__":
    main()