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

with open(os.path.join(dataset_dir, 'messages.csv'), encoding='utf-8') as f:
    all_messages = list(csv.DictReader(f))

# Let's inspect user_22:
# Bal: 1132.46, MinBal: 500, Free: 632.46, Safe: 475.46 -> Reserved = 157.00
# User 22 ReqDate: 2024-12-05
# Pending debit on 2024-12-08: event_1961 shopping = 43.00
# If 43 is pending, 157 - 43 = 114.00!
# What is 114.00 for user_22?
# Let's check all events of user_22!
u22_events = [e for e in all_events if e['user_id'] == 'user_22']
print("User 22 events in Nov/Dec 2024:")
for e in sorted(u22_events, key=lambda x: x['settlement_date']):
    d = e['settlement_date']
    if '2024-11' in d or '2024-12' in d:
        print(f"  {d} | {e['event_type']} | {e['category']} | {e['amount']} | {e['status']} | {e['description']}")
