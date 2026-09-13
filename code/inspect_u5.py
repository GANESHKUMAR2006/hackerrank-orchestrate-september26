import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_05']

print(f"User 05 total events: {len(events)}")
for e in sorted(events, key=lambda x: x['settlement_date']):
    print(f"  {e['settlement_date']} | {e['event_type']} | {e['category']} | {e['direction']} | {e['amount']} | {e['status']} | {e['description']}")
