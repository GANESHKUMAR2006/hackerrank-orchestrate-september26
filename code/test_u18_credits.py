import csv

with open('dataset/financial_events.csv', encoding='utf-8') as f:
    events = list(csv.DictReader(f))

u18 = [e for e in events if e['user_id'] == 'user_18']
for e in u18:
    if e['direction'] == 'credit' or 'transfer' in e['description'].lower():
        print(e['event_id'], e['event_date'], e['settlement_date'], e['direction'], e['amount'], e['category'], e['description'])
