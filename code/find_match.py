import itertools

dec_events = [
    ('rent', 254.1),
    ('transport_fuel', 29.57),
    ('utilities', 51.86),
    ('dining1', 45.39),
    ('insurance', 26.0),
    ('groceries1', 40.91),
    ('transport_taxi', 19.18),
    ('streaming', 19.0),
    ('cloud_storage', 5.0),
    ('shopping', 39.88),
    ('transport_metro', 25.9),
    ('dining2', 36.0),
    ('entertainment', 38.33),
]

target = 539.1
# Let's see if any subset or certain categories sum to target
print("Target:", target)

# Try all combinations of up to len(dec_events)
for r in range(1, len(dec_events) + 1):
    for combo in itertools.combinations(dec_events, r):
        s = sum(x[1] for x in combo)
        if abs(s - target) < 0.05:
            print("MATCH found:", combo)

# Also check sum of all fixed / recurring events
# Rent (254.1) + Utilities (51.86) + Insurance (26.0) + Streaming (19.0) + Cloud (5.0) + Shopping (39.88)
# What about utilities? In the profile or past months?
