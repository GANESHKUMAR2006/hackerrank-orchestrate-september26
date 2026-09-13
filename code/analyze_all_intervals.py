import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evidence import EvidenceResolver
from collections import defaultdict
from datetime import datetime

resolver = EvidenceResolver()
print(f"Loaded {len(resolver.profiles)} profiles.")

# Analyze historical intervals for all user series
intervals_by_cat = defaultdict(list)
series_counts = defaultdict(int)

for uid, user in resolver.profiles.items():
    raw_evs = resolver.raw_events.get(uid, [])
    # group by (category, description)
    groups = defaultdict(list)
    for r in raw_evs:
        if r['status'].strip().lower() == 'settled':
            groups[(r['category'].strip(), r['description'].strip())].append(r)
            
    for (cat, desc), ev_list in groups.items():
        if len(ev_list) >= 2:
            dates = sorted([datetime.strptime(e['settlement_date'].strip(), '%Y-%m-%d') for e in ev_list])
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_diff = sum(diffs) / len(diffs)
            series_counts[cat] += 1
            intervals_by_cat[cat].append(avg_diff)

print("\nSeries count and average interval (days) by category:")
for cat, cnt in sorted(series_counts.items(), key=lambda x: -x[1]):
    avg_ivl = sum(intervals_by_cat[cat]) / len(intervals_by_cat[cat])
    min_ivl = min(intervals_by_cat[cat])
    max_ivl = max(intervals_by_cat[cat])
    print(f"  {cat:<22}: count={cnt:<4}, avg={avg_ivl:<5.1f} days (min={min_ivl:<4.1f}, max={max_ivl:<5.1f})")
