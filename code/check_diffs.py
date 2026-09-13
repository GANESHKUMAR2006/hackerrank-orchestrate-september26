import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

for s in samples:
    u = s['user_id']
    p = profiles[u]
    bal = float(p['current_available_balance'])
    min_b = float(p['minimum_balance_to_keep'])
    req_amt = float(s['requested_amount'])
    safe = float(s['amount_safe_to_pay'])
    free_cash = bal - min_b
    diff = free_cash - safe
    print(f"{s['request_id']} ({u}) | Bal={bal} | Min={min_b} | Free={free_cash:.2f} | Req={req_amt:.2f} | Safe={safe:.2f} | Free-Safe={diff:.2f} | Earliest={s['earliest_date_for_full_payment']}")
