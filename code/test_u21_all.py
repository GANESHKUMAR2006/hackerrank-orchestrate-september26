import itertools

# Let's inspect user_21 all March items:
# 53 is pending fuel on 2026-04-05
# Utilities on 2026-04-06? In March it was 124.08, but what about other months?
# Let's check utilities amount across all months for user_21:
import csv
with open('dataset/financial_events.csv', encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_21']

for e in events:
    if e['category'] in ['utilities', 'shopping', 'streaming', 'cloud_storage', 'dining']:
        print(f"  {e['settlement_date']} | {e['category']} | {e['amount']} | {e['description']}")
