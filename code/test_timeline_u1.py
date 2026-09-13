import csv
import os
from datetime import datetime, timedelta

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = {r['request_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    all_events = list(csv.DictReader(f))

# Let's inspect user_01
req = samples['request_01']
prof = profiles['user_01']
req_date = req['request_date']
events_u1 = [e for e in all_events if e['user_id'] == 'user_01']

print("User 01 Profile:", prof)
print("Request 01:", req)
print("\nUser 01 Events on or after request date (2024-03-03):")
future_u1 = [e for e in events_u1 if e['settlement_date'] >= req_date]
for e in sorted(future_u1, key=lambda x: x['settlement_date']):
    print(f"  {e['settlement_date']} | {e['event_type']} | {e['category']} | {e['direction']} | {e['amount']} | {e['status']} | {e['description']}")

