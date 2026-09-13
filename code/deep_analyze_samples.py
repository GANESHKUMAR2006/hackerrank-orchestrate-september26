import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'financial_profiles.csv'), encoding='utf-8') as f:
    profiles = {r['user_id']: r for r in csv.DictReader(f)}

with open(os.path.join(dataset_dir, 'sample_requests.csv'), encoding='utf-8') as f:
    samples = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'financial_events.csv'), encoding='utf-8') as f:
    all_events = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'messages.csv'), encoding='utf-8') as f:
    all_messages = list(csv.DictReader(f))

with open(os.path.join(dataset_dir, 'request_payment_options.csv'), encoding='utf-8') as f:
    all_options = list(csv.DictReader(f))

events_by_user = {}
for e in all_events:
    events_by_user.setdefault(e['user_id'], []).append(e)

messages_by_user = {}
for m in all_messages:
    messages_by_user.setdefault(m['user_id'], []).append(m)

options_by_request = {}
for o in all_options:
    options_by_request.setdefault(o['request_id'], []).append(o)

out_file = os.path.join(os.path.dirname(__file__), '..', 'deep_samples.txt')
with open(out_file, 'w', encoding='utf-8') as out:
    for s in samples:
        u = s['user_id']
        rid = s['request_id']
        prof = profiles[u]
        out.write(f"\n==================== {rid} ({u}) ====================\n")
        out.write(f"Req: Date={s['request_date']}, Amt={s['requested_amount']}, Deadline={s['desired_completion_date']}, Partial={s['allows_partial_payment']}\n")
        out.write(f"Result: Safe={s['amount_safe_to_pay']}, Status={s['affordability_status']}, Method={s['recommended_payment_method']}, Earliest={s['earliest_date_for_full_payment']}\n")
        out.write(f"Plan: {s['payment_plan']}\n")
        out.write(f"Changes: {s['spending_changes_needed']}\n")
        out.write(f"Explanation: {s['decision_explanation']}\n")
        out.write(f"Profile: Bal={prof['current_available_balance']}, MinBal={prof['minimum_balance_to_keep']}, Methods={prof['payment_methods_user_will_consider']}, MaxInstalMonths={prof['max_installment_months']}\n")
        out.write(f"Options: {len(options_by_request.get(rid, []))} options\n")
        for opt in options_by_request.get(rid, []):
            out.write(f"  Opt {opt['payment_option_id']}: method={opt['payment_method']}, num={opt['number_of_payments']}, start={opt['first_payment_date']}, freq={opt['payment_frequency_days']}, amt={opt['payment_amount']}, fee={opt['financing_fee']}, total={opt['total_payable_amount']}\n")
        msgs = messages_by_user.get(u, [])
        if msgs:
            out.write(f"Messages ({len(msgs)}):\n")
            for m in msgs:
                out.write(f"  [{m['message_id']}] src={m['source_type']}, ev={m['related_event_id']}, txt={m['message_text'][:120]}\n")
        f_evs = [e for e in events_by_user.get(u, []) if e['settlement_date'] >= s['request_date']]
        out.write(f"Events on/after request_date ({len(f_evs)}):\n")
        for e in sorted(f_evs, key=lambda x: x['settlement_date']):
            out.write(f"  {e['event_id']} | {e['settlement_date']} | {e['event_type']} | {e['category']} | {e['direction']} | {e['amount']} | {e['status']} | {e['description']}\n")
