import csv

with open('dataset/financial_events.csv', encoding='utf-8') as f:
    events = list(csv.DictReader(f))

for uid in ['user_18', 'user_33', 'user_57', 'user_171', 'user_261', 'user_273']:
    u_evs = [e for e in events if e['user_id'] == uid]
    debits = [e for e in u_evs if e['direction'] == 'debit']
    credits = [e for e in u_evs if e['direction'] == 'credit']
    for d in debits:
        for c in credits:
            if d['amount'] == c['amount'] and d['amount'] and d['settlement_date'] == c['settlement_date']:
                print(f"{uid}: matching amount {d['amount']} on {d['settlement_date']}")
                print(f"  Debit: {d['event_id']}, {d['category']}, {d['description']}")
                print(f"  Credit: {c['event_id']}, {c['category']}, {c['description']}")
