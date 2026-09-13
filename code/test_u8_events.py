import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_08']

for e in sorted(events, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    if '2025-01' in d or '2025-02' in d:
        print(f"  {d} | {e['event_type']} | {e['category']} | {e['amount']} | {e['description']}")
