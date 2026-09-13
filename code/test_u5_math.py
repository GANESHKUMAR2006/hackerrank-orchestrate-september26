import csv
import os
from collections import defaultdict
from datetime import datetime, timedelta

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_05']

# Let's inspect user_05 monthly recurring items
prof = profiles['user_05']
bal = float(prof['current_available_balance'])
min_bal = float(prof['minimum_balance_to_keep'])
print(f"User 05: Bal={bal}, MinBal={min_bal}, Difference={bal - min_bal}")

# Group by category / description to see recurring expenses
monthly_items = defaultdict(list)
for e in events:
    if e['status'] == 'settled' and e['direction'] == 'debit':
        d = datetime.strptime(e['settlement_date'], '%Y-%m-%d')
        # past 3 months: Aug, Sep, Oct
        if d >= datetime(2025, 8, 1) and d < datetime(2025, 11, 1):
            monthly_items[e['category']].append(float(e['amount']))

for cat, vals in sorted(monthly_items.items()):
    print(f"  {cat}: count={len(vals)}, sum={sum(vals):.2f}, avg/mo={sum(vals)/3:.2f}")

total_3mo = sum(sum(vals) for vals in monthly_items.values())
print(f"Total over 3 months (Aug-Oct): {total_3mo:.2f}")
print(f"Bal - MinBal - Total_3mo = {bal - min_bal - total_3mo:.2f}")
