import csv
import os
from collections import Counter

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'messages.csv'), encoding='utf-8') as f:
    messages = list(csv.DictReader(f))

print(f"Total messages: {len(messages)}")
print("Source types:", Counter(m['source_type'] for m in messages))
print("Has request_id:", sum(1 for m in messages if m['request_id']))
print("Has related_event_id:", sum(1 for m in messages if m['related_event_id']))

# Let's inspect messages related to sample users (user_01 to user_25)
print("\n--- Messages for sample users (user_01 to user_25) ---")
for m in messages:
    uid = m['user_id']
    if int(uid.replace('user_', '')) <= 25:
        print(f"[{m['message_id']}] {uid} | req={m['request_id']} | ev={m['related_event_id']} | src={m['source_type']}")
        print(f"    Text: {m['message_text']}")
