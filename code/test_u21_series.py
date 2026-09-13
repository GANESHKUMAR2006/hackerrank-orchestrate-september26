# Let's inspect all recurring series for user_21:
import csv
from collections import defaultdict

with open('dataset/financial_events.csv', encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_21']

# Group by description
series = defaultdict(list)
for e in events:
    if e['status'] == 'settled':
        series[e['description']].append(e)

print(f"Total series: {len(series)}")
for desc, evs in series.items():
    dates = [e['settlement_date'] for e in evs]
    amts = [float(e['amount']) for e in evs]
    cat = evs[0]['category']
    print(f"  {desc} ({cat}): count={len(evs)}, dates={dates[-3:]}, amts={amts[-3:]}")
