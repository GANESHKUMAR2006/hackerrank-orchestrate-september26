import csv
import itertools

with open('dataset/financial_events.csv', encoding='utf-8') as f:
    events = [r for r in csv.DictReader(f) if r['user_id'] == 'user_22']

# Look at distinct amounts of debits in user_22
debits = []
for e in events:
    if e['direction'] == 'debit' and e['amount']:
        debits.append((e['category'], e['description'], float(e['amount']), e['settlement_date'], e['flexibility']))

target = 114.0
print("User 22 target:", target)

# Search subsets among the events in November / recent months
unique_items = {}
for cat, desc, amt, dt, flex in debits:
    unique_items[(cat, desc, amt)] = (dt, flex)

print("Unique items count:", len(unique_items))
items_list = list(unique_items.keys())
for r in range(1, 8):
    for combo in itertools.combinations(items_list, r):
        s = sum(x[2] for x in combo)
        if abs(s - target) < 0.01:
            print("MATCH found:")
            for item in combo:
                print(f"  {item} -> {unique_items[item]}")
