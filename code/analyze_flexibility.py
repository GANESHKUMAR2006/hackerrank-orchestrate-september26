import csv
import os
from collections import Counter

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = list(csv.DictReader(f))

flexible_events = [e for e in events if e['flexibility'] != 'fixed']
print(f"Total non-fixed events: {len(flexible_events)}")
print("Non-fixed event categories:", Counter(e['category'] for e in flexible_events))
print("Non-fixed event types:", Counter(e['event_type'] for e in flexible_events))
print("Non-fixed flexibilities:", Counter(e['flexibility'] for e in flexible_events))

# Let's inspect sample 06 user's flexible events:
u6_flex = [e for e in flexible_events if e['user_id'] == 'user_06']
print(f"\nUser 06 flexible events ({len(u6_flex)}):")
for e in u6_flex:
    print(f"  {e['event_id']} | {e['event_date']} | {e['category']} | {e['description']} | {e['amount']} | {e['flexibility']} | min={e['minimum_allowed_amount']}")
