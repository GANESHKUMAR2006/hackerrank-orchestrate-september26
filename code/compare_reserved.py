import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    all_events = list(csv.DictReader(f))

events_by_user = {}
for e in all_events:
    events_by_user.setdefault(e['user_id'], []).append(e)

for s in samples:
    u = s['user_id']
    p = profiles[u]
    bal = float(p['current_available_balance'])
    min_b = float(p['minimum_balance_to_keep'])
    req_amt = float(s['requested_amount'])
    safe = float(s['amount_safe_to_pay'])
    free = bal - min_b
    reserved = free - safe
    
    # Check pending debits on or after request date
    future_evs = [e for e in events_by_user[u] if e['settlement_date'] >= s['request_date']]
    pending_debits = sum(float(e['amount']) for e in future_evs if e['direction'] == 'debit' and e['amount'])
    
    print(f"{s['request_id']} ({u}) {p['home_currency']}: Req={req_amt}, Free={free:.2f}, Safe={safe:.2f}, Reserved={reserved:.2f}, PendingDebits={pending_debits:.2f}, Diff={reserved - pending_debits:.2f}")
