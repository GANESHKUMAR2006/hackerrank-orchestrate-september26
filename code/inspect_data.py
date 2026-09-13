import csv
import os
import glob
from collections import Counter, defaultdict

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

print("=== DATASET INSPECTION ===")

files = [
    'requests.csv',
    'sample_requests.csv',
    'financial_profiles.csv',
    'financial_events.csv',
    'exchange_rates.csv',
    'request_payment_options.csv',
    'messages.csv',
    'images.csv',
    'output.csv'
]

for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filename}")
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = list(reader)
        print(f"\n--- {filename} ---")
        print(f"Row count: {len(rows)}")
        print(f"Columns ({len(header)}): {header}")
        if rows:
            print(f"Sample row 1: {rows[0]}")
            
        # Check blank values per column
        blanks = {col: 0 for col in header}
        for r in rows:
            for i, val in enumerate(r):
                if val.strip() == "":
                    blanks[header[i]] += 1
        non_zero_blanks = {k: v for k, v in blanks.items() if v > 0}
        if non_zero_blanks:
            print(f"Blank counts: {non_zero_blanks}")

print("\n" + "="*50)
print("DEEP DIVE: financial_events.csv")
with open(os.path.join(dataset_dir, 'financial_events.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fe_rows = list(reader)

print(f"Total events: {len(fe_rows)}")
print(f"Event types: {Counter(r['event_type'] for r in fe_rows)}")
print(f"Statuses: {Counter(r['status'] for r in fe_rows)}")
print(f"Is recurring: {Counter(r.get('is_recurring', 'N/A') for r in fe_rows)}")
print(f"Categories: {Counter(r.get('category', 'N/A') for r in fe_rows)}")
blank_amounts = [r for r in fe_rows if r['amount'].strip() == '']
print(f"Events with blank amount: {len(blank_amounts)}")
for b in blank_amounts:
    print(f"  Event ID: {b['event_id']}, User: {b['user_id']}, Type: {b['event_type']}, Status: {b['status']}, Date: {b.get('date', b.get('event_date', ''))}, Description: {b.get('description', '')}")

linked_events = [r for r in fe_rows if r.get('linked_event_id', '').strip() != '']
print(f"Events with linked_event_id: {len(linked_events)}")
linked_types = Counter(f"{r['event_type']} -> status={r['status']}" for r in linked_events)
print(f"Linked event types & statuses: {linked_types}")

print("\n" + "="*50)
print("DEEP DIVE: financial_profiles.csv")
with open(os.path.join(dataset_dir, 'financial_profiles.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fp_rows = list(reader)
print(f"Total profiles: {len(fp_rows)}")
print(f"Currencies: {Counter(r['home_currency'] for r in fp_rows)}")
print(f"Payment methods considered: {Counter(r['payment_methods_user_will_consider'] for r in fp_rows)}")
print(f"Max installment months: {Counter(r['max_installment_months'] for r in fp_rows)}")
print("Sample profile:", dict(fp_rows[0]))

print("\n" + "="*50)
print("DEEP DIVE: sample_requests.csv")
with open(os.path.join(dataset_dir, 'sample_requests.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    sr_rows = list(reader)
print(f"Sample requests count: {len(sr_rows)}")
print(f"Sample affordability_status: {Counter(r['affordability_status'] for r in sr_rows)}")
print(f"Sample recommended_payment_method: {Counter(r['recommended_payment_method'] for r in sr_rows)}")
print(f"Sample spending_changes_needed: {Counter(r['spending_changes_needed'] for r in sr_rows)}")
print("\nFirst 5 sample requests full details:")
for i, r in enumerate(sr_rows[:5]):
    print(f"--- Sample {i+1} ---")
    for k, v in r.items():
        print(f"  {k}: {v}")

print("\n" + "="*50)
print("DEEP DIVE: messages.csv")
with open(os.path.join(dataset_dir, 'messages.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    msg_rows = list(reader)
print(f"Total messages: {len(msg_rows)}")
msg_has_event = sum(1 for r in msg_rows if r.get('related_event_id', '').strip() != '')
msg_has_req = sum(1 for r in msg_rows if r.get('request_id', '').strip() != '')
print(f"Messages with related_event_id: {msg_has_event}, with request_id: {msg_has_req}")
print("Sample messages:")
for r in msg_rows[:5]:
    print(f"  User: {r['user_id']}, Req: {r.get('request_id','')}, Event: {r.get('related_event_id','')}, Date: {r.get('message_date', r.get('date', ''))}, Content: {r.get('message_text', r.get('text', ''))[:100]}")

print("\n" + "="*50)
print("DEEP DIVE: images.csv")
with open(os.path.join(dataset_dir, 'images.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    img_rows = list(reader)
print(f"Total image links: {len(img_rows)}")
for r in img_rows:
    print(f"  Image: {r['image_id']}, User: {r['user_id']}, Req: {r.get('request_id','')}, Event: {r.get('related_event_id','')}, Description: {r.get('description', dict(r))}")

print("\n" + "="*50)
print("DEEP DIVE: request_payment_options.csv")
with open(os.path.join(dataset_dir, 'request_payment_options.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rpo_rows = list(reader)
print(f"Total payment options: {len(rpo_rows)}")
print("Sample payment option:", dict(rpo_rows[0]))

print("\n" + "="*50)
print("DEEP DIVE: exchange_rates.csv")
with open(os.path.join(dataset_dir, 'exchange_rates.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    er_rows = list(reader)
print(f"Total exchange rates: {len(er_rows)}")
currencies = set()
for r in er_rows:
    currencies.add(r['from_currency'])
    currencies.add(r['to_currency'])
print(f"Currencies in exchange_rates: {currencies}")
print("Sample exchange rate:", dict(er_rows[0]))
