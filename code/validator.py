"""
Phase 7: Output Validation Layer for Buy or Wait challenge.

Validates:
1. Exact column names and order
2. Exactly one row per request (no missing or duplicate requests)
3. Allowed affordability_status values
4. Allowed recommended_payment_method values
5. Safe amount bounds: [0, requested_amount]
6. Payment plan syntax, chronological order, and sum feasibility
7. Spending change syntax (stop/reduce_to) and limit (<= 3 changes)
8. Deadline compliance (completion on or before desired_completion_date)
9. Strict preservation of deterministic PlannerDecision
10. Grounded, safe decision explanations
"""

from datetime import datetime
from decimal import Decimal
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from models import RequestItem
from planner import PlannerDecision


REQUIRED_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

PREDICTION_COLUMNS = [
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

ALLOWED_STATUSES = {
    "affordable_now",
    "affordable_with_plan",
    "affordable_later",
    "not_affordable",
}

ALLOWED_METHODS = {
    "full_payment",
    "partial_payment",
    "installments",
    "wait",
    "not_recommended",
}

FORBIDDEN_WORDS = [
    "python",
    "planner.py",
    "phase 1",
    "phase 2",
    "phase 3",
    "phase 4",
    "phase 5",
    "phase 6",
    "phase 7",
    "benchmark",
    "ground truth",
    "hidden test",
    "antigravity",
]


class ValidationError(Exception):
    """Raised when output validation fails."""
    pass


class OutputValidator:
    """Validates predictions and exported CSVs against all contest constraints."""

    @staticmethod
    def validate_headers(headers: List[str]) -> bool:
        """Verify exact columns and order."""
        if headers == REQUIRED_COLUMNS:
            return True
        if headers == PREDICTION_COLUMNS:
            return True
        return False

    @staticmethod
    def validate_row(
        row: Dict[str, Any],
        request: Optional[RequestItem] = None,
        decision: Optional[PlannerDecision] = None,
    ) -> List[str]:
        """Validate a single prediction row. Returns list of error strings."""
        errors: List[str] = []
        rid = row.get("request_id", "unknown")

        # 1. Status check
        status = str(row.get("affordability_status", "")).strip()
        if status not in ALLOWED_STATUSES:
            errors.append(f"[{rid}] Invalid status '{status}'. Must be one of {ALLOWED_STATUSES}")

        # 2. Method check
        method = str(row.get("recommended_payment_method", "")).strip()
        if method not in ALLOWED_METHODS:
            errors.append(f"[{rid}] Invalid method '{method}'. Must be one of {ALLOWED_METHODS}")

        # 3. Safe amount check
        try:
            safe_amt = Decimal(str(row.get("amount_safe_to_pay", "0")))
            if safe_amt < Decimal("0.0"):
                errors.append(f"[{rid}] Negative amount_safe_to_pay: {safe_amt}")
            if request is not None:
                req_amt = Decimal(str(request.requested_amount))
                if safe_amt > req_amt + Decimal("0.01"):
                    errors.append(f"[{rid}] amount_safe_to_pay ({safe_amt}) exceeds requested_amount ({req_amt})")
        except Exception as e:
            errors.append(f"[{rid}] Unparseable amount_safe_to_pay: {e}")

        # 4. Payment plan formatting and total check
        plan_str = str(row.get("payment_plan", "")).strip()
        if not plan_str:
            errors.append(f"[{rid}] Empty payment_plan string")
        elif plan_str == "none":
            if status in {"affordable_now", "affordable_later"} or (status == "affordable_with_plan" and method != "not_recommended"):
                errors.append(f"[{rid}] payment_plan cannot be 'none' when status is '{status}' and method is '{method}'")
        else:
            # Parse plan payments
            parts = plan_str.split("|")
            plan_total = Decimal("0.0")
            prev_date: Optional[datetime] = None
            for p in parts:
                p = p.strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}:[0-9]+(\.[0-9]{1,2})?$", p):
                    errors.append(f"[{rid}] Invalid payment plan entry format '{p}'")
                    continue
                d_str, a_str = p.split(":")
                try:
                    p_date = datetime.strptime(d_str, "%Y-%m-%d")
                    p_amt = Decimal(a_str)
                    if p_amt <= Decimal("0.0"):
                        errors.append(f"[{rid}] Payment amount must be positive: '{p}'")
                    plan_total += p_amt
                    if prev_date and p_date < prev_date:
                        errors.append(f"[{rid}] Payment dates not in chronological order: {prev_date} -> {p_date}")
                    prev_date = p_date
                except Exception as e:
                    errors.append(f"[{rid}] Error parsing payment entry '{p}': {e}")

            # Check plan total against requested amount / options
            if request is not None and method in {"full_payment", "wait", "partial_payment"}:
                req_amt = Decimal(str(request.requested_amount))
                if abs(plan_total - req_amt) > Decimal("0.10"):
                    errors.append(f"[{rid}] Plan total {plan_total} does not match requested amount {req_amt}")

        # 5. Earliest date for full payment & deadline compliance
        date_str = str(row.get("earliest_date_for_full_payment", "")).strip()
        if date_str and date_str != "none":
            try:
                full_date = datetime.strptime(date_str, "%Y-%m-%d")
                if request is not None:
                    # For affordable_now, date should be request_date
                    req_date = datetime.strptime(request.request_date, "%Y-%m-%d")
                    if status == "affordable_now" and full_date != req_date:
                        errors.append(f"[{rid}] affordable_now earliest_date ({date_str}) != request_date ({request.request_date})")

                    # Deadline compliance
                    deadline = datetime.strptime(request.desired_completion_date, "%Y-%m-%d")
                    if method in {"wait", "full_payment"} and status in {"affordable_now", "affordable_later"}:
                        if full_date > deadline:
                            errors.append(f"[{rid}] Full payment date {date_str} exceeds desired_completion_date {request.desired_completion_date}")
            except Exception as e:
                errors.append(f"[{rid}] Unparseable earliest_date_for_full_payment '{date_str}': {e}")

        # 6. Spending changes formatting and count
        sc_str = str(row.get("spending_changes_needed", "")).strip()
        if not sc_str:
            errors.append(f"[{rid}] Empty spending_changes_needed string")
        elif sc_str != "none":
            sc_parts = sc_str.split("|")
            if len(sc_parts) > 3:
                errors.append(f"[{rid}] Exceeded maximum 3 spending changes: {len(sc_parts)} changes found")
            for sc in sc_parts:
                sc = sc.strip()
                if not (re.match(r"^stop:[a-zA-Z0-9_]+$", sc) or re.match(r"^reduce_to:[a-zA-Z0-9_]+:[0-9]+(\.[0-9]{1,2})?$", sc)):
                    errors.append(f"[{rid}] Invalid spending change syntax '{sc}'")

        # 7. Decision explanation quality & safety
        exp = str(row.get("decision_explanation", "")).strip()
        if not exp:
            errors.append(f"[{rid}] decision_explanation cannot be empty")
        elif len(exp) < 10:
            errors.append(f"[{rid}] decision_explanation too short: '{exp}'")
        else:
            exp_lower = exp.lower()
            for forbidden in FORBIDDEN_WORDS:
                if forbidden in exp_lower:
                    errors.append(f"[{rid}] decision_explanation contains forbidden term '{forbidden}'")

        # 8. Deterministic fidelity check (if decision object supplied)
        if decision is not None:
            if str(decision.amount_safe_to_pay) != str(row.get("amount_safe_to_pay")):
                # Check numeric equivalence
                if Decimal(str(decision.amount_safe_to_pay)) != Decimal(str(row.get("amount_safe_to_pay"))):
                    errors.append(f"[{rid}] amount_safe_to_pay does not match deterministic decision ({decision.amount_safe_to_pay} vs {row.get('amount_safe_to_pay')})")
            if decision.affordability_status != str(row.get("affordability_status")):
                errors.append(f"[{rid}] affordability_status does not match deterministic decision ({decision.affordability_status} vs {row.get('affordability_status')})")
            if decision.recommended_payment_method != str(row.get("recommended_payment_method")):
                errors.append(f"[{rid}] recommended_payment_method does not match deterministic decision ({decision.recommended_payment_method} vs {row.get('recommended_payment_method')})")
            if decision.payment_plan != str(row.get("payment_plan")):
                errors.append(f"[{rid}] payment_plan does not match deterministic decision ({decision.payment_plan} vs {row.get('payment_plan')})")
            if (decision.earliest_date_for_full_payment or "") != (str(row.get("earliest_date_for_full_payment") or "")).strip():
                errors.append(f"[{rid}] earliest_date_for_full_payment does not match deterministic decision")
            if decision.spending_changes_needed != str(row.get("spending_changes_needed")):
                errors.append(f"[{rid}] spending_changes_needed does not match deterministic decision")

        return errors

    @classmethod
    def validate_dataset(
        cls,
        rows: List[Dict[str, Any]],
        requests: Optional[Dict[str, RequestItem]] = None,
        decisions: Optional[Dict[str, PlannerDecision]] = None,
        expected_count: Optional[int] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate an entire prediction dataset.
        Returns (is_valid, error_list).
        """
        all_errors: List[str] = []

        # 1. Total row count
        if expected_count is not None and len(rows) != expected_count:
            all_errors.append(f"Row count mismatch: expected {expected_count}, got {len(rows)}")

        # 2. Unique request IDs
        seen_ids: Set[str] = set()
        for i, row in enumerate(rows):
            rid = row.get("request_id")
            if rid:
                if rid in seen_ids:
                    all_errors.append(f"Duplicate request_id found: '{rid}' at row {i+1}")
                seen_ids.add(rid)

        # 3. Verify all expected requests are present
        if requests:
            missing_ids = set(requests.keys()) - seen_ids
            if missing_ids:
                all_errors.append(f"Missing {len(missing_ids)} request IDs: {sorted(list(missing_ids))[:5]}...")

        # 4. Validate each row
        for row in rows:
            rid = row.get("request_id", "")
            req = requests.get(rid) if requests else None
            dec = decisions.get(rid) if decisions else None
            row_errors = cls.validate_row(row, request=req, decision=dec)
            all_errors.extend(row_errors)

        return len(all_errors) == 0, all_errors
