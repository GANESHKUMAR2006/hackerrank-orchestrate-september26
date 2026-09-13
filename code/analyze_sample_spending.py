import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    events = {r['event_id']: r for r in csv.DictReader(f)}

for r in samples:
    if r['spending_changes_needed'] != 'none':
        print(f"\nRequest: {r['request_id']} ({r['user_id']})")
        print(f"  Status: {r['affordability_status']}, Method: {r['recommended_payment_method']}")
        print(f"  Req Date: {r['request_date']}, Req Amt: {r['requested_amount']}, Safe: {r['amount_safe_to_pay']}")
        print(f"  Spending changes: {r['spending_changes_needed']}")
        print(f"  Plan: {r['payment_plan']}")
        print(f"  Explanation: {r['decision_explanation']}")
        # check the event(s)
        for change in r['spending_changes_needed'].split('|'):
            parts = change.split(':')
            action = parts[0]
            eid = parts[1]
            ev = events.get(eid, {})
            print(f"    -> Event {eid}: action={action}, desc={ev.get('description')}, cat={ev.get('category')}, amt={ev.get('amount')}, min_amt={ev.get('minimum_allowed_amount')}, date={ev.get('event_date')}, flex={ev.get('flexibility')}")
            if len(parts) > 2:
                print(f"       target reduce_to amount: {parts[2]}")
