import csv
import os
from datetime import datetime, timedelta

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

# Let's inspect each user's salary and average monthly expense
print(f"{'ReqID':<11} {'ReqDate':<11} {'EarliestFull':<13} {'ReqAmt':<12} {'Salary':<10} {'Payday':<8}")
print("-" * 75)

for s in samples:
    u = s['user_id']
    u_evs = events_by_user[u]
    salaries = [e for e in u_evs if e['category'] == 'salary' and e['amount']]
    sal_amt = salaries[-1]['amount'] if salaries else 'N/A'
    sal_date = salaries[-1]['settlement_date'] if salaries else 'N/A'
    payday = sal_date.split('-')[2] if sal_date != 'N/A' else 'N/A'
    print(f"{s['request_id']:<11} {s['request_date']:<11} {s['earliest_date_for_full_payment']:<13} {s['requested_amount']:<12} {sal_amt:<10} {payday:<8}")
