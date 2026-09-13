import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = {r['event_id']: r for r in csv.DictReader(f)}

for eid in ['event_8575', 'event_21101', 'event_23306', 'event_23855']:
    print(eid, events.get(eid))
