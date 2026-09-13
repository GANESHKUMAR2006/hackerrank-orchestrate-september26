"""
Phase 7 Unit Tests: Output Schema, Field Constraints & Deterministic Fidelity.

Tests:
L. Exact output columns.
M. Correct column order.
N. One row per request.
O. No duplicate requests.
P. Allowed statuses.
Q. Allowed methods.
R. Safe amount bounds.
S. Valid payment-plan formatting.
T. Valid spending-change formatting.
U. Maximum 3 changes.
V. Deadline compliance.
W. Deterministic decision preserved.
"""

from decimal import Decimal
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import RequestItem
from planner import PlannerDecision
from validator import (
    OutputValidator,
    REQUIRED_COLUMNS,
    PREDICTION_COLUMNS,
    ALLOWED_STATUSES,
    ALLOWED_METHODS,
)


@pytest.fixture
def valid_row():
    return {
        "request_id": "request_100",
        "amount_safe_to_pay": "1200",
        "affordability_status": "affordable_now",
        "recommended_payment_method": "full_payment",
        "payment_plan": "2026-05-10:1200",
        "earliest_date_for_full_payment": "2026-05-10",
        "spending_changes_needed": "none",
        "decision_explanation": "Pay EUR 1,200 today. This leaves at least EUR 500 available over the next 90 days.",
    }


@pytest.fixture
def sample_req():
    return RequestItem(
        request_id="request_100",
        user_id="user_10",
        request_date="2026-05-10",
        request_type="purchase",
        requested_amount=1200.0,
        desired_completion_date="2026-05-31",
        allows_partial_payment=True,
        request_text="Can I buy tools?",
    )


@pytest.fixture
def sample_dec():
    return PlannerDecision(
        request_id="request_100",
        user_id="user_10",
        amount_safe_to_pay=Decimal("1200.00"),
        affordability_status="affordable_now",
        recommended_payment_method="full_payment",
        payment_plan="2026-05-10:1200",
        earliest_date_for_full_payment="2026-05-10",
        spending_changes_needed="none",
    )


# Test L: Exact output columns
def test_l_exact_output_columns():
    assert OutputValidator.validate_headers(REQUIRED_COLUMNS) is True
    assert OutputValidator.validate_headers(PREDICTION_COLUMNS) is True
    
    # Extra column rejected
    bad_headers = REQUIRED_COLUMNS + ["extra_column"]
    assert OutputValidator.validate_headers(bad_headers) is False
    
    # Missing column rejected
    missing_headers = REQUIRED_COLUMNS[:-1]
    assert OutputValidator.validate_headers(missing_headers) is False


# Test M: Correct column order
def test_m_correct_column_order():
    reversed_headers = list(reversed(REQUIRED_COLUMNS))
    assert OutputValidator.validate_headers(reversed_headers) is False
    
    shuffled = REQUIRED_COLUMNS.copy()
    shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
    assert OutputValidator.validate_headers(shuffled) is False


# Test N: One row per request
def test_n_one_row_per_request(valid_row, sample_req):
    rows = [valid_row]
    requests = {sample_req.request_id: sample_req}
    
    # Matching counts pass
    is_valid, errors = OutputValidator.validate_dataset(rows, requests=requests, expected_count=1)
    assert is_valid is True
    assert len(errors) == 0
    
    # Mismatched row count fails
    is_valid2, errors2 = OutputValidator.validate_dataset(rows, requests=requests, expected_count=2)
    assert is_valid2 is False
    assert any("Row count mismatch" in e for e in errors2)


# Test O: No duplicate requests
def test_o_no_duplicate_requests(valid_row, sample_req):
    duplicate_rows = [valid_row, valid_row.copy()]
    requests = {sample_req.request_id: sample_req}
    
    is_valid, errors = OutputValidator.validate_dataset(duplicate_rows, requests=requests, expected_count=2)
    assert is_valid is False
    assert any("Duplicate request_id found" in e for e in errors)


# Test P: Allowed statuses
def test_p_allowed_statuses(valid_row, sample_req):
    # Valid statuses all pass
    for status in ALLOWED_STATUSES:
        row = valid_row.copy()
        row["affordability_status"] = status
        if status == "not_affordable":
            row["recommended_payment_method"] = "not_recommended"
            row["payment_plan"] = "none"
        errors = OutputValidator.validate_row(row, request=sample_req)
        assert len(errors) == 0, f"Status {status} failed validation: {errors}"
        
    # Invalid status fails
    bad_row = valid_row.copy()
    bad_row["affordability_status"] = "maybe_affordable"
    errors = OutputValidator.validate_row(bad_row, request=sample_req)
    assert any("Invalid status" in e for e in errors)


# Test Q: Allowed methods
def test_q_allowed_methods(valid_row, sample_req):
    # Valid methods pass
    for method in ALLOWED_METHODS:
        row = valid_row.copy()
        row["recommended_payment_method"] = method
        if method == "not_recommended":
            row["affordability_status"] = "not_affordable"
            row["payment_plan"] = "none"
        errors = OutputValidator.validate_row(row, request=sample_req)
        assert len(errors) == 0, f"Method {method} failed validation: {errors}"
        
    # Invalid method fails
    bad_row = valid_row.copy()
    bad_row["recommended_payment_method"] = "crypto_transfer"
    errors = OutputValidator.validate_row(bad_row, request=sample_req)
    assert any("Invalid method" in e for e in errors)


# Test R: Safe amount bounds
def test_r_safe_amount_bounds(valid_row, sample_req):
    # Negative safe amount fails
    bad_row1 = valid_row.copy()
    bad_row1["amount_safe_to_pay"] = "-100"
    errors1 = OutputValidator.validate_row(bad_row1, request=sample_req)
    assert any("Negative amount_safe_to_pay" in e for e in errors1)
    
    # Safe amount exceeding requested amount fails
    bad_row2 = valid_row.copy()
    bad_row2["amount_safe_to_pay"] = "2000"  # requested is 1200
    errors2 = OutputValidator.validate_row(bad_row2, request=sample_req)
    assert any("exceeds requested_amount" in e for e in errors2)
    
    # Safe amount within bounds passes
    good_row = valid_row.copy()
    good_row["amount_safe_to_pay"] = "0"
    errors3 = OutputValidator.validate_row(good_row, request=sample_req)
    assert len(errors3) == 0


# Test S: Valid payment plan formatting
def test_s_valid_payment_plan_formatting(valid_row, sample_req):
    # Valid single payment
    row1 = valid_row.copy()
    row1["payment_plan"] = "2026-05-10:1200"
    assert len(OutputValidator.validate_row(row1, request=sample_req)) == 0
    
    # Valid multi-payment (chronological)
    row2 = valid_row.copy()
    row2["recommended_payment_method"] = "partial_payment"
    row2["affordability_status"] = "affordable_with_plan"
    row2["payment_plan"] = "2026-05-10:500|2026-05-20:700"
    assert len(OutputValidator.validate_row(row2, request=sample_req)) == 0
    
    # Invalid non-chronological order fails
    row3 = valid_row.copy()
    row3["payment_plan"] = "2026-05-20:500|2026-05-10:700"
    errors3 = OutputValidator.validate_row(row3, request=sample_req)
    assert any("chronological" in e for e in errors3)
    
    # Invalid syntax fails
    row4 = valid_row.copy()
    row4["payment_plan"] = "May 10: 1200"
    errors4 = OutputValidator.validate_row(row4, request=sample_req)
    assert any("Invalid payment plan entry format" in e for e in errors4)


# Test T: Valid spending change formatting
def test_t_valid_spending_change_formatting(valid_row, sample_req):
    # "none" passes
    row1 = valid_row.copy()
    row1["spending_changes_needed"] = "none"
    assert len(OutputValidator.validate_row(row1, request=sample_req)) == 0
    
    # Valid stop and reduce_to pass
    row2 = valid_row.copy()
    row2["spending_changes_needed"] = "stop:event_476|reduce_to:event_989:500.50"
    assert len(OutputValidator.validate_row(row2, request=sample_req)) == 0
    
    # Malformed spending change fails
    row3 = valid_row.copy()
    row3["spending_changes_needed"] = "cancel_event_476"
    errors3 = OutputValidator.validate_row(row3, request=sample_req)
    assert any("Invalid spending change syntax" in e for e in errors3)


# Test U: Maximum 3 spending changes
def test_u_maximum_3_changes(valid_row, sample_req):
    # 3 changes pass
    row1 = valid_row.copy()
    row1["spending_changes_needed"] = "stop:ev1|stop:ev2|reduce_to:ev3:10"
    assert len(OutputValidator.validate_row(row1, request=sample_req)) == 0
    
    # 4 changes fail
    row2 = valid_row.copy()
    row2["spending_changes_needed"] = "stop:ev1|stop:ev2|stop:ev3|stop:ev4"
    errors2 = OutputValidator.validate_row(row2, request=sample_req)
    assert any("Exceeded maximum 3 spending changes" in e for e in errors2)


# Test V: Deadline compliance
def test_v_deadline_compliance(valid_row, sample_req):
    # Date on or before deadline (2026-05-31) passes
    row1 = valid_row.copy()
    row1["affordability_status"] = "affordable_later"
    row1["recommended_payment_method"] = "wait"
    row1["earliest_date_for_full_payment"] = "2026-05-25"
    row1["payment_plan"] = "2026-05-25:1200"
    assert len(OutputValidator.validate_row(row1, request=sample_req)) == 0
    
    # Date after deadline (2026-06-05 > 2026-05-31) fails
    row2 = valid_row.copy()
    row2["affordability_status"] = "affordable_later"
    row2["recommended_payment_method"] = "wait"
    row2["earliest_date_for_full_payment"] = "2026-06-05"
    row2["payment_plan"] = "2026-06-05:1200"
    errors2 = OutputValidator.validate_row(row2, request=sample_req)
    assert any("exceeds desired_completion_date" in e for e in errors2)


# Test W: Deterministic decision preserved
def test_w_deterministic_decision_preserved(valid_row, sample_req, sample_dec):
    # Exact match passes
    assert len(OutputValidator.validate_row(valid_row, request=sample_req, decision=sample_dec)) == 0
    
    # Modified safe amount fails
    bad_row1 = valid_row.copy()
    bad_row1["amount_safe_to_pay"] = "999"
    errors1 = OutputValidator.validate_row(bad_row1, request=sample_req, decision=sample_dec)
    assert any("amount_safe_to_pay does not match deterministic decision" in e for e in errors1)
    
    # Modified status fails
    bad_row2 = valid_row.copy()
    bad_row2["affordability_status"] = "affordable_with_plan"
    errors2 = OutputValidator.validate_row(bad_row2, request=sample_req, decision=sample_dec)
    assert any("affordability_status does not match deterministic decision" in e for e in errors2)
