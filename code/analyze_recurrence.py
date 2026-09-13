import csv
import os
from collections import defaultdict
from datetime import datetime

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = list(csv.DictReader(f))

# Group events by (user_id, category, description) or (user_id, event_type, category)
user_events = defaultdict(lambda: defaultdict(list))
for e in events:
    user_events[e['user_id']][(e['event_type'], e['category'], e['description'])].append(e)

print(f"Total user-group series: {sum(len(v) for v in user_events.values())}")

# Let's inspect user_01 series
print("\n--- User 01 recurring series ---")
for (etype, cat, desc), ev_list in user_events['user_01'].items():
    if len(ev_list) > 1:
        dates = [e['settlement_date'] for e in ev_list]
        amounts = [e['amount'] for e in ev_list]
        print(f"  {etype} | {cat} | {desc} | Count: {len(ev_list)} | Dates: {dates[-3:]} | Amounts: {amounts[-3:]}")

print("\n--- User 06 recurring series ---")
for (etype, cat, desc), ev_list in user_events['user_06'].items():
    if len(ev_list) > 1:
        dates = [e['settlement_date'] for e in ev_list]
        amounts = [e['amount'] for e in ev_list]
        print(f"  {etype} | {cat} | {desc} | Count: {len(ev_list)} | Dates: {dates[-3:]} | Amounts: {amounts[-3:]}")

