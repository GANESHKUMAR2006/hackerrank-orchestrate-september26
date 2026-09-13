import csv
import re

with open('dataset/messages.csv', encoding='utf-8') as f:
    messages = list(csv.DictReader(f))

salary_amts = []
for m in messages:
    txt = m['message_text']
    uid = m['user_id']
    mid = m['message_id']
    
    # 1. Salary amount
    m_sal = re.search(r'(?:naik menjadi|tersebut naik menjadi|increased to|reduced to|diturunkan menjadi|temporary monthly pay is|temporer anda adalah|first salary will be|gaji pertama anda adalah|first salary of|first salary from the new employer is|gaji yang sudah dikonfirmasi kini sebesar|confirmed base salary is|gaji pokok yang dikonfirmasi adalah|gaji bulanan anda sekarang|salary of|gaji sebesar|sebesar)\s+([A-Z]{3})\s+([\d,.]+)', txt, re.IGNORECASE)
    if m_sal:
        curr = m_sal.group(1).upper()
        amt_str = m_sal.group(2).replace(',', '').rstrip('.')
        salary_amts.append((mid, uid, 'salary_amount', curr, float(amt_str)))

    # 2. Salary date
    m_dt = re.search(r'(?:expected on|diperkirakan masuk pada|diperkirakan pada|confirmed for|scheduled for|tercatat untuk|berlaku mulai|applies from|resumes on|mulai)\s+(\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
    if m_dt:
        dt = m_dt.group(1)
        salary_amts.append((mid, uid, 'effective_date', dt))

    # 3. Rent increase
    m_rent = re.search(r'(?:increases monthly rent by|menaikkan biaya sewa bulanan sebesar)\s+(\d+)%', txt, re.IGNORECASE)
    if m_rent:
        pct = float(m_rent.group(1))
        salary_amts.append((mid, uid, 'rent_increase_pct', pct))

    # 4. Employment ended
    if any(k in txt.lower() for k in ['contract has ended', 'kontrak musiman saat ini telah berakhir', 'seasonal contract has ended']):
        salary_amts.append((mid, uid, 'employment_ended', True))

    # 5. Failed debit retry
    if any(k in txt.lower() for k in ['another debit will be attempted', 'another debit may be attempted', 'debit ulang akan dicoba']):
        salary_amts.append((mid, uid, 'failed_debit_retry', m.get('related_event_id')))

    # 6. Internal transfer
    if any(k in txt.lower() for k in ['transfer between your two accounts', 'transfer antara dua rekening anda']):
        salary_amts.append((mid, uid, 'internal_transfer', True))

print(f"Extracted facts count: {len(salary_amts)}")
for f in salary_amts[:30]:
    print(" ", f)
