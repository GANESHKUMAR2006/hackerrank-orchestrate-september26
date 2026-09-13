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

print(f"{'ReqID':<11} {'User':<8} {'Currency':<8} {'ReqDate':<11} {'Balance':<12} {'MinBal':<12} {'Bal-Min':<12} {'ReqAmt':<12} {'SafeAmt':<12} {'EarliestFull':<12} {'Status':<22} {'Method'}")
print("-" * 140)

for s in samples:
    u = profiles[s['user_id']]
    bal = float(u['current_available_balance'])
    min_bal = float(u['minimum_balance_to_keep'])
    req_amt = float(s['requested_amount'])
    safe_amt = float(s['amount_safe_to_pay'])
    diff = bal - min_bal
    earliest = s['earliest_date_for_full_payment']
    status = s['affordability_status']
    method = s['recommended_payment_method']
    print(f"{s['request_id']:<11} {s['user_id']:<8} {u['home_currency']:<8} {s['request_date']:<11} {bal:<12.1f} {min_bal:<12.1f} {diff:<12.1f} {req_amt:<12.1f} {safe_amt:<12.1f} {earliest:<12} {status:<22} {method}")
