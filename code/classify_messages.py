import csv
import os
import re

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'messages.csv'), encoding='utf-8') as f:
    messages = list(csv.DictReader(f))

patterns = set()
for m in messages:
    txt = m['message_text']
    # classify message intent
    t_lower = txt.lower()
    if 'gaji' in t_lower or 'salary' in t_lower or 'pay' in t_lower or 'payroll' in t_lower:
        patterns.add('salary/payroll')
    elif 'rent' in t_lower or 'sewa' in t_lower or 'lease' in t_lower:
        patterns.add('rent/lease')
    elif 'refund' in t_lower or 'pengembalian' in t_lower:
        patterns.add('refund')
    elif 'portfolio' in t_lower or 'investment' in t_lower or 'market value' in t_lower or 'investasi' in t_lower:
        patterns.add('investment')
    elif 'prize' in t_lower or 'hadiah' in t_lower or 'bonus' in t_lower:
        patterns.add('prize/bonus')
    elif 'transfer' in t_lower:
        patterns.add('internal_transfer')
    elif 'cancel' in t_lower or 'batal' in t_lower:
        patterns.add('cancellation')
    else:
        patterns.add('other: ' + txt[:40])

print("Detected pattern categories:")
for p in sorted(patterns):
    print(" -", p)
