import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = {r['request_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

targets = [
    ('user_08', 'request_08', 452.0),
    ('user_18', 'request_18', 624.0),
    ('user_21', 'request_21', 568.0),
    ('user_22', 'request_22', 157.0),
    ('user_15', 'request_15', 487.0),
    ('user_14', 'request_14', 1134.0),
]

for uid, rid, target in targets:
    s = samples[rid]
    p = profiles[uid]
    req_date = s['request_date']
    u_events = [e for e in events if e['user_id'] == uid]
    print(f"\n==================== {uid} ({rid}) Target Reserved = {target} (ReqDate: {req_date}) ====================")
    print("Expense categories to protect:", p['expense_categories_to_protect'])
    print("Priorities:", p['financial_priorities'])
    # Check events around req_date or upcoming scheduled/recurring
    # Let's print all events with status != 'settled' or events within 30 days before/after req_date
    for e in u_events:
        if e['status'] in ['scheduled', 'pending', 'failed']:
            print(f"  Unsettled: {e['event_id']} | {e['settlement_date']} | {e['event_type']} | {e['category']} | {e['amount']} | {e['status']} | {e['description']}")
    
    # Also print all distinct monthly recurring debits
    print("  Distinct regular amounts:")
    by_cat = {}
    for e in u_events:
        if e['direction'] == 'debit' and e['status'] == 'settled':
            by_cat.setdefault(f"{e['category']}:{e['description']}", []).append(float(e['amount']))
    for k, v in by_cat.items():
        if len(v) >= 3:
            print(f"    {k}: count={len(v)}, last3={v[-3:]}")
