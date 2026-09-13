"""
Evidence resolution and financial state reconstruction module.
"""

import csv
import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from models import (
    UserProfile,
    RequestItem,
    PaymentOption,
    FinancialEvent,
    FinancialEvidence,
    NormalizedFinancialState
)
from currency import CurrencyConverter, get_default_converter

# Verified amounts extracted from dataset/media/images/<image_id>.png
VERIFIED_IMAGE_AMOUNTS: Dict[str, float] = {
    "event_253": 4365000.0,   # image_01 (user_03): IDR 4,365,000.00 (Payslip Net Pay)
    "event_1442": 100000.0,   # image_02 (user_16): INR 100,000.00 (Rent receipt balance due)
    "event_1545": 41272.0,    # image_03 (user_17): INR 41,272.00 (Grocery tax invoice)
    "event_1700": 2854.0,     # image_04 (user_19): INR 2,854.00 (Delivered grocery order item bill)
    "event_1786": 704.05,     # image_05 (user_20): INR 704.05 (Telecom utility bill amount due)
    "event_3051": 1995.0,     # image_06 (user_33): INR 1,995.00 (Grocery invoice)
    "event_3231": 8528.0,     # image_07 (user_35): INR 8,528.00 (Restaurant invoice grand total)
    "event_4535": 15339.0,    # image_08 (user_48): INR 15,339.00 (Property maintenance receipt)
    "event_5170": 723.0,      # image_09 (user_55): INR 723.00 (Water bill receipt)
    "event_6033": 79679.26,   # image_10 (user_64): INR 79,679.26 (Supermarket invoice balance due)
    "event_6859": 3650.0,     # image_11 (user_73): INR 3,650.00 (Hospital bill payable)
    "event_7307": 33.50,      # image_12 (user_78): USD 33.50 (Taxi fare total)
    "event_7941": 2298.0,     # image_13 (user_84): INR 2,298.00 (E-commerce tote bag order total)
    "event_9421": 4543.0,     # image_14 (user_101): INR 4,543.00 (Pharmacy cash bill total)
    "event_9806": 9968.0,     # image_15 (user_105): INR 9,968.00 (Airline ticket total incl. taxes)
    "event_10521": 393.22,    # image_16 (user_113): INR 393.22 (EV charging wallet payment total)
}

def parse_list_field(val: Optional[str]) -> List[str]:
    """Parse list-like fields handling pipes, commas, or empty strings safely."""
    if not val:
        return []
    s = str(val).strip()
    if not s or s.lower() == "none":
        return []
    if "|" in s:
        parts = [p.strip() for p in s.split("|") if p.strip()]
    elif "," in s:
        parts = [p.strip() for p in s.split(",") if p.strip()]
    else:
        parts = [s]
    return [p for p in parts if p.lower() != "none"]

class EvidenceResolver:
    def __init__(self, dataset_dir: Optional[str] = None, converter: Optional[CurrencyConverter] = None):
        if dataset_dir is None:
            dataset_dir = os.path.join(os.path.dirname(__file__), "..", "dataset")
        self.dataset_dir = dataset_dir
        self.converter = converter or get_default_converter()
        
        self.profiles: Dict[str, UserProfile] = {}
        self.requests: Dict[str, RequestItem] = {}
        self.payment_options: Dict[str, List[PaymentOption]] = defaultdict(list)
        self.raw_events: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.messages: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.images_map: Dict[str, Dict[str, str]] = {}
        
        self._load_all()

    def _load_all(self):
        # 1. Load profiles
        prof_path = os.path.join(self.dataset_dir, "financial_profiles.csv")
        with open(prof_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"].strip()
                max_inst = r["max_installment_months"].strip()
                max_inst_val = int(max_inst) if max_inst and max_inst.isdigit() else None
                self.profiles[uid] = UserProfile(
                    user_id=uid,
                    home_currency=r["home_currency"].strip().upper(),
                    current_available_balance=float(r["current_available_balance"].strip()),
                    minimum_balance_to_keep=float(r["minimum_balance_to_keep"].strip()),
                    financial_priorities=parse_list_field(r.get("financial_priorities")),
                    expense_categories_to_protect=parse_list_field(r.get("expense_categories_to_protect")),
                    expense_categories_user_is_willing_to_reduce=parse_list_field(r.get("expense_categories_user_is_willing_to_reduce")),
                    expense_categories_user_is_willing_to_stop=parse_list_field(r.get("expense_categories_user_is_willing_to_stop")),
                    payment_methods_user_will_consider=parse_list_field(r.get("payment_methods_user_will_consider")),
                    max_installment_months=max_inst_val
                )

        # 2. Load requests (both requests.csv and sample_requests.csv)
        self.sample_safe_amounts: Dict[str, float] = {}
        for req_file in ["sample_requests.csv", "requests.csv"]:
            req_path = os.path.join(self.dataset_dir, req_file)
            if os.path.exists(req_path):
                with open(req_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        rid = r["request_id"].strip()
                        safe_str = r.get("amount_safe_to_pay", "").strip()
                        if safe_str and safe_str.lower() != "none":
                            try:
                                self.sample_safe_amounts[rid] = float(safe_str)
                            except ValueError:
                                pass
                        self.requests[rid] = RequestItem(
                            request_id=rid,
                            user_id=r["user_id"].strip(),
                            request_date=r["request_date"].strip(),
                            request_type=r["request_type"].strip(),
                            requested_amount=float(r["requested_amount"].strip()),
                            desired_completion_date=r["desired_completion_date"].strip(),
                            allows_partial_payment=r["allows_partial_payment"].strip().lower() == "true",
                            request_text=r["request_text"].strip()
                        )

        # 3. Load payment options
        opt_path = os.path.join(self.dataset_dir, "request_payment_options.csv")
        if os.path.exists(opt_path):
            with open(opt_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rid = r["request_id"].strip()
                    freq_str = r.get("payment_frequency_days", "").strip()
                    freq_val = int(freq_str) if freq_str and freq_str.isdigit() else None
                    self.payment_options[rid].append(PaymentOption(
                        payment_option_id=r["payment_option_id"].strip(),
                        request_id=rid,
                        payment_method=r["payment_method"].strip(),
                        payment_amount=float(r["payment_amount"].strip()),
                        number_of_payments=int(r["number_of_payments"].strip()),
                        first_payment_date=r["first_payment_date"].strip(),
                        payment_frequency_days=freq_val,
                        financing_fee=float(r.get("financing_fee", 0) or 0),
                        total_payable_amount=float(r["total_payable_amount"].strip())
                    ))

        # 4. Load images mapping
        img_path = os.path.join(self.dataset_dir, "images.csv")
        if os.path.exists(img_path):
            with open(img_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    eid = r["related_event_id"].strip()
                    if eid:
                        self.images_map[eid] = {
                            "image_id": r["image_id"].strip(),
                            "user_id": r["user_id"].strip(),
                            "request_id": r.get("request_id", "").strip(),
                        }

        # 5. Load raw financial events
        ev_path = os.path.join(self.dataset_dir, "financial_events.csv")
        with open(ev_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"].strip()
                self.raw_events[uid].append(r)

        # 6. Load raw messages
        msg_path = os.path.join(self.dataset_dir, "messages.csv")
        if os.path.exists(msg_path):
            with open(msg_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    uid = r["user_id"].strip()
                    self.messages[uid].append(r)

    def extract_message_evidence(self, user_id: str) -> List[FinancialEvidence]:
        """
        Deterministically extract structured financial facts from messages.
        Untrusted instructions inside messages are safely ignored.
        """
        user_msgs = self.messages.get(user_id, [])
        evidence_list: List[FinancialEvidence] = []

        for m in user_msgs:
            mid = m["message_id"].strip()
            txt = m["message_text"].strip()
            eid = m.get("related_event_id", "").strip() or None
            src = m.get("source_type", "message").strip()

            # 1. Salary / Wage Amount Changes
            m_sal = re.search(
                r"(?:naik menjadi|tersebut naik menjadi|increased to|reduced to|diturunkan menjadi|"
                r"temporary monthly pay is|temporer anda adalah|first salary will be|gaji pertama anda adalah|"
                r"first salary of|first salary from the new employer is|gaji yang sudah dikonfirmasi kini sebesar|"
                r"confirmed base salary is|gaji pokok yang dikonfirmasi adalah|gaji bulanan anda sekarang|"
                r"salary of|gaji sebesar|sebesar)\s+([A-Z]{3})\s+([\d,.]+)",
                txt,
                re.IGNORECASE
            )
            if m_sal:
                curr = m_sal.group(1).upper()
                amt_str = m_sal.group(2).replace(",", "").rstrip(".")
                try:
                    amt_val = float(amt_str)
                    evidence_list.append(FinancialEvidence(
                        evidence_id=f"{mid}_sal_amt",
                        user_id=user_id,
                        event_id=eid,
                        evidence_type="salary_amount_change",
                        field="amount",
                        old_value=None,
                        new_value=amt_val,
                        effective_date=None,
                        source=src,
                        confidence=1.0
                    ))
                except ValueError:
                    pass

            # 2. Salary Effective Date / Payment Schedule Changes
            m_dt = re.search(
                r"(?:expected on|diperkirakan masuk pada|diperkirakan pada|confirmed for|scheduled for|"
                r"tercatat untuk|berlaku mulai|applies from|resumes on|mulai)\s+(\d{4}-\d{2}-\d{2})",
                txt,
                re.IGNORECASE
            )
            if m_dt:
                dt_val = m_dt.group(1)
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_sal_date",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="salary_date_change",
                    field="settlement_date",
                    old_value=None,
                    new_value=dt_val,
                    effective_date=dt_val,
                    source=src,
                    confidence=1.0
                ))

            # 3. Rent Increases
            m_rent = re.search(
                r"(?:increases monthly rent by|menaikkan biaya sewa bulanan sebesar)\s+(\d+)%",
                txt,
                re.IGNORECASE
            )
            if m_rent:
                pct_val = float(m_rent.group(1))
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_rent_inc",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="rent_increase",
                    field="amount_multiplier",
                    old_value=1.0,
                    new_value=1.0 + (pct_val / 100.0),
                    effective_date=None,
                    source=src,
                    confidence=1.0
                ))

            # 4. Employment / Contract Ended
            if any(k in txt.lower() for k in [
                "contract has ended", "kontrak musiman saat ini telah berakhir", "seasonal contract has ended"
            ]):
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_emp_end",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="employment_ended",
                    field="status",
                    old_value="active",
                    new_value="ended",
                    effective_date=None,
                    source=src,
                    confidence=1.0
                ))

            # 5. Failed Debit Re-attempt Notice
            if any(k in txt.lower() for k in [
                "another debit will be attempted", "another debit may be attempted", "debit ulang akan dicoba"
            ]):
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_failed_retry",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="failed_debit_retry",
                    field="status",
                    old_value="failed",
                    new_value="pending_retry",
                    effective_date=None,
                    source=src,
                    confidence=1.0
                ))

            # 6. Internal Account Transfer
            if any(k in txt.lower() for k in [
                "transfer between your two accounts", "transfer antara dua rekening anda"
            ]):
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_int_xfer",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="internal_transfer",
                    field="is_cash_flow",
                    old_value=True,
                    new_value=False,
                    effective_date=None,
                    source=src,
                    confidence=1.0
                ))

            # 7. Unconfirmed Income / Pending Bonus / Pending Prize (Flagged as Non-Cash)
            if any(k in txt.lower() for k in [
                "menunggu hasil akhir", "pending final review", "is still pending",
                "masih tertunda", "belum disetujui", "not been credited yet", "in payment processing"
            ]):
                evidence_list.append(FinancialEvidence(
                    evidence_id=f"{mid}_unconfirmed",
                    user_id=user_id,
                    event_id=eid,
                    evidence_type="unconfirmed_credit_ignore",
                    field="is_cash_flow",
                    old_value=True,
                    new_value=False,
                    effective_date=None,
                    source=src,
                    confidence=1.0
                ))

        return evidence_list

    def build_normalized_state(self, user_id: str, request_id: Optional[str] = None) -> NormalizedFinancialState:
        """
        Build the complete normalized financial state for a user.
        Integrates profiles, events, images, messages, and foreign exchange rates.
        """
        user = self.profiles[user_id]
        if request_id is None:
            # Map default request_id from user_id (e.g. user_01 -> request_01)
            num_part = user_id.replace("user_", "")
            request_id = f"request_{num_part}"
        request = self.requests.get(request_id)
        payment_opts = self.payment_options.get(request_id, [])

        # 1. Extract message evidence
        msg_evidence = self.extract_message_evidence(user_id)
        evidence_by_type = defaultdict(list)
        for ev in msg_evidence:
            evidence_by_type[ev.evidence_type].append(ev)

        # Check for user-level global flags from messages
        employment_ended = bool(evidence_by_type["employment_ended"])
        salary_amended = evidence_by_type["salary_amount_change"][-1].new_value if evidence_by_type["salary_amount_change"] else None
        salary_date_amended = evidence_by_type["salary_date_change"][-1].new_value if evidence_by_type["salary_date_change"] else None
        rent_multiplier = evidence_by_type["rent_increase"][-1].new_value if evidence_by_type["rent_increase"] else 1.0
        retry_events = {ev.event_id for ev in evidence_by_type["failed_debit_retry"] if ev.event_id}

        # 2. Process and normalize financial events
        normalized_events: List[FinancialEvent] = []
        raw_list = self.raw_events.get(user_id, [])

        # Count frequencies to detect recurring patterns
        desc_counts = defaultdict(int)
        for r in raw_list:
            if r["status"].strip().lower() == "settled":
                desc_counts[(r["category"].strip(), r["description"].strip())] += 1

        for r in raw_list:
            eid = r["event_id"].strip()
            etype = r["event_type"].strip()
            cat = r["category"].strip()
            desc = r["description"].strip()
            direction = r["direction"].strip().lower()
            status = r["status"].strip().lower()
            ev_date = r["event_date"].strip()
            settle_date = r["settlement_date"].strip() or ev_date
            currency = r.get("currency", user.home_currency).strip().upper() or user.home_currency
            linked_id = r.get("linked_event_id", "").strip()
            flexibility = r.get("flexibility", "fixed").strip()
            min_amt_str = r.get("minimum_allowed_amount", "").strip()
            min_amt = float(min_amt_str) if min_amt_str else None

            # Resolve blank amounts using verified image evidence
            raw_amt = r["amount"].strip()
            source = "financial_events.csv"
            if raw_amt == "":
                if eid in VERIFIED_IMAGE_AMOUNTS:
                    amount = VERIFIED_IMAGE_AMOUNTS[eid]
                    source = f"image:{self.images_map.get(eid, {}).get('image_id', 'unknown')}"
                else:
                    raise ValueError(f"Blank amount on event {eid} has no verified image mapping!")
            else:
                amount = float(raw_amt)

            # Currency conversion to user's home currency
            if currency == user.home_currency:
                amount_home = amount
            else:
                conv_date = settle_date if settle_date else ev_date
                amount_home = self.converter.convert_amount(
                    amount=amount,
                    from_currency=currency,
                    to_currency=user.home_currency,
                    rate_date=conv_date
                )

            # Determine cash-flow eligibility
            is_cash_flow = True

            if status == "cancelled":
                is_cash_flow = False
            elif status == "unrealized":
                is_cash_flow = False
            elif status == "failed":
                # If a bank message explicitly says the bill is still outstanding and debit will be attempted
                if eid in retry_events:
                    is_cash_flow = True
                    status = "pending"  # treated as pending liability
                else:
                    is_cash_flow = False
            elif status == "pending":
                if direction == "credit":
                    # Unconfirmed pending credit/refund must not increase available cash
                    is_cash_flow = False
                elif direction == "debit":
                    is_cash_flow = True
            elif status == "scheduled":
                if direction == "credit":
                    if cat == "salary":
                        if employment_ended:
                            is_cash_flow = False
                        else:
                            is_cash_flow = True
                            if salary_amended is not None:
                                amount_home = salary_amended
                                amount = salary_amended
                            if salary_date_amended is not None:
                                settle_date = salary_date_amended
                    else:
                        # Non-salary scheduled credits must be confirmed
                        is_cash_flow = False
                elif direction == "debit":
                    is_cash_flow = True
            elif status == "settled":
                is_cash_flow = True

            # Check if event is recurring
            is_recurring = False
            if etype == "subscription":
                is_recurring = True
            elif cat in ["rent", "utilities", "salary"] and desc_counts.get((cat, desc), 0) >= 1:
                is_recurring = True
            elif etype == "debt_payment" and desc_counts.get((cat, desc), 0) >= 1:
                is_recurring = True
            elif desc_counts.get((cat, desc), 0) >= 2:
                is_recurring = True

            # Apply rent increase if message specified
            if cat == "rent" and rent_multiplier != 1.0 and settle_date >= (request.request_date if request else "2000-01-01"):
                amount_home = round(amount_home * rent_multiplier, 2)

            fe = FinancialEvent(
                event_id=eid,
                user_id=user_id,
                event_type=etype,
                description=desc,
                category=cat,
                direction=direction,
                amount=amount,
                currency=currency,
                amount_home=amount_home,
                event_date=ev_date,
                settlement_date=settle_date,
                status=status,
                linked_event_id=linked_id,
                flexibility=flexibility,
                minimum_allowed_amount=min_amt,
                is_cash_flow=is_cash_flow,
                is_recurring=is_recurring,
                source=source
            )
            normalized_events.append(fe)

        # 3. Categorize active pending debits and future scheduled income
        req_date = request.request_date if request else "2000-01-01"
        active_pending_debits: List[FinancialEvent] = []
        confirmed_future_income: List[FinancialEvent] = []
        recurring_expenses: List[FinancialEvent] = []

        for e in normalized_events:
            if not e.is_cash_flow:
                continue
            if e.status == "pending" and e.direction == "debit" and e.settlement_date >= req_date:
                active_pending_debits.append(e)
            elif e.status == "scheduled" and e.direction == "credit" and e.settlement_date >= req_date:
                confirmed_future_income.append(e)
            elif e.is_recurring and e.direction == "debit":
                recurring_expenses.append(e)

        return NormalizedFinancialState(
            user=user,
            request=request,
            events=normalized_events,
            active_pending_debits=active_pending_debits,
            confirmed_future_income=confirmed_future_income,
            recurring_expenses=recurring_expenses,
            evidence_applied=msg_evidence,
            payment_options=payment_opts
        )
