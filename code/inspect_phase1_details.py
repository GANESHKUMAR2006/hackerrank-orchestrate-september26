import csv
from collections import Counter

# Check exchange rates
with open('dataset/exchange_rates.csv', encoding='utf-8') as f:
    er = list(csv.DictReader(f))
print('Exchange rate count:', len(er))
pairs = Counter(f"{r['from_currency']}->{r['to_currency']}" for r in er)
print('Currency pairs:', pairs)

# Check linked events
with open('dataset/financial_events.csv', encoding='utf-8') as f:
    fe = list(csv.DictReader(f))
linked = [r for r in fe if r['linked_event_id']]
print('Linked events count:', len(linked))
print('Linked event types:', Counter(r['event_type'] for r in linked))
print('Linked statuses:', Counter(r['status'] for r in linked))
for le in linked[:10]:
    orig_id = le['linked_event_id']
    orig = [x for x in fe if x['event_id'] == orig_id]
    orig_info = f"{orig[0]['event_type']}:{orig[0]['status']}:{orig[0]['amount']}" if orig else "None"
    print(f"  {le['event_id']} ({le['event_type']}:{le['status']}:{le['amount']}) -> linked to {orig_id} ({orig_info})")

# Check payment options
with open('dataset/request_payment_options.csv', encoding='utf-8') as f:
    po = list(csv.DictReader(f))
print('\nPayment options count:', len(po))
print('Payment methods in options:', Counter(r['payment_method'] for r in po))
print('Number of payments values:', Counter(r['number_of_payments'] for r in po))
print('Payment frequencies:', Counter(r['payment_frequency_days'] for r in po))

# Check foreign currency events in financial_events.csv
foreign_events = []
with open('dataset/financial_profiles.csv', encoding='utf-8') as f:
    profiles = {r['user_id']: r['home_currency'] for r in csv.DictReader(f)}

for e in fe:
    u = e['user_id']
    h_curr = profiles[u]
    if e['currency'] and e['currency'] != h_curr:
        foreign_events.append((e, h_curr))

print(f"\nForeign currency events: {len(foreign_events)}")
for e, h_curr in foreign_events[:5]:
    print(f"  Event {e['event_id']} ({u}): {e['currency']} -> Home: {h_curr}, Date: {e['settlement_date']}, Amount: {e['amount']}")
