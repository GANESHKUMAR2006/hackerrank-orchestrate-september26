import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evidence import EvidenceResolver
from collections import defaultdict
from datetime import datetime

resolver = EvidenceResolver()

cat_intervals = defaultdict(list)
for uid in list(resolver.profiles.keys())[:10]:
    raw_evs = resolver.raw_events.get(uid, [])
    # group by category
    by_cat = defaultdict(list)
    for r in raw_evs:
        if r['status'].strip().lower() == 'settled':
            by_cat[r['category'].strip()].append(r)
    for cat in ['groceries', 'transport', 'dining']:
        evs = by_cat.get(cat, [])
        if len(evs) >= 2:
            dates = sorted([datetime.strptime(e['settlement_date'].strip(), '%Y-%m-%d') for e in evs])
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_diff = sum(diffs) / len(diffs)
            cat_intervals[cat].append(avg_diff)

for cat, ivls in cat_intervals.items():
    print(f"{cat} overall interval across users: avg={sum(ivls)/len(ivls):.1f} days")
