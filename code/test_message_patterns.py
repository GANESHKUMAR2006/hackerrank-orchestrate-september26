import csv
import re
from collections import Counter

with open('dataset/messages.csv', encoding='utf-8') as f:
    messages = list(csv.DictReader(f))

print(f"Total messages: {len(messages)}")

categorized = Counter()
uncategorized = []

for m in messages:
    txt = m['message_text']
    tl = txt.lower()
    cat = None
    
    # Check patterns
    if any(k in tl for k in ['naik menjadi', 'increases monthly rent by', 'tersebut naik menjadi', 'temporer anda adalah', 'temporary monthly pay is', 'reduced to', 'diturunkan menjadi', 'new recurring childcare payment', 'first salary will be', 'gaji pertama anda']):
        cat = 'amount_change'
    elif any(k in tl for k in ['expected on', 'diperkirakan pada', 'is now expected', 'sekarang diperkirakan']):
        cat = 'date_change'
    elif any(k in tl for k in ['contract has ended', 'kontrak musiman saat ini telah berakhir', 'has ended', 'telah berakhir']):
        cat = 'employment_ended'
    elif any(k in tl for k in ['menunggu hasil akhir', 'pending final review', 'is still pending', 'masih tertunda', 'belum disetujui', 'belum tercatat', 'not been credited yet', 'in payment processing']):
        cat = 'unconfirmed_pending_ignore'
    elif any(k in tl for k in ['previous debit attempt failed', 'percobaan debit sebelumnya gagal', 'failed']):
        cat = 'failed_debit_retry'
    elif any(k in tl for k in ['transfer between your two accounts', 'transfer antara dua rekening anda']):
        cat = 'internal_transfer'
    elif any(k in tl for k in ['extra card charge is still being investigated', 'tagihan kartu tambahan masih dalam penyelidikan', 'dispute is open', 'sengketa masih terbuka']):
        cat = 'disputed_charge_no_reversal'
    elif any(k in tl for k in ['prize proceeds have reached', 'dana hadiah telah masuk']):
        cat = 'one_off_prize_settled'
    elif any(k in tl for k in ['tote bag order was paid in inr', 'receipt has the final amount', 'struk memuat jumlah akhir']):
        cat = 'receipt_confirms_amount'
    elif any(k in tl for k in ['foreign currency', 'mata uang asing']):
        cat = 'foreign_currency_notice'
    elif any(k in tl for k in ['gaji rutin', 'regular salary', 'gaji pokok yang dikonfirmasi', 'confirmed base salary']):
        cat = 'salary_confirmation'
    elif any(k in tl for k in ['refund has been initiated', 'pengembalian dana telah dimulai']):
        cat = 'refund_initiated_uncredited'
    elif any(k in tl for k in ['klien menyetujui pembayaran faktur', 'client approved the invoice']):
        cat = 'client_invoice_confirmed'
    
    if cat:
        categorized[cat] += 1
    else:
        uncategorized.append(m)

print("Categorized counts:")
for c, cnt in categorized.most_common():
    print(f"  {c}: {cnt}")

print(f"Uncategorized: {len(uncategorized)}")
for m in uncategorized:
    print(f"  [{m['message_id']}] {m['source_type']}: {m['message_text']}")
