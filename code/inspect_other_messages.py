import csv
import os

dataset_dir = os.path.join(os.path.dirname(__file__), '..', 'dataset')

with open(os.path.join(dataset_dir, 'messages.csv'), encoding='utf-8') as f:
    messages = list(csv.DictReader(f))

for m in messages:
    txt = m['message_text']
    t_lower = txt.lower()
    if not any(k in t_lower for k in ['gaji', 'salary', 'pay', 'rent', 'sewa', 'lease', 'refund', 'pengembalian', 'portfolio', 'investment', 'market value', 'investasi', 'prize', 'hadiah', 'bonus', 'transfer', 'cancel', 'batal']):
        print(f"[{m['message_id']}] User: {m['user_id']}, Event: {m['related_event_id']}")
        print(f"  {txt}\n")
