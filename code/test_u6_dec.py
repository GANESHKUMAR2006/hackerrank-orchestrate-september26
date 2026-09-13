import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_06']

print("User 06 past events around days 3 to 15:")
for e in sorted(events, key=lambda x: x['settlement_date']):
    day = int(e['settlement_date'].split('-')[2])
    month = int(e['settlement_date'].split('-')[1])
    year = int(e['settlement_date'].split('-')[0])
    if year == 2025 and month == 12:
        print(f"  {e['settlement_date']} | {e['event_type']} | {e['category']} | {e['direction']} | {e['amount']} | {e['status']} | {e['description']}")
