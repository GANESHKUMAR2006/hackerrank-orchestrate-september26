"""
Phase 7 Unit Tests: AI Decision Explanations & Boundary Integrity.

Tests:
A. AI explanation generated from deterministic decision.
B. AI cannot modify deterministic fields.
C. Fallback explanation works when model call fails.
D. Missing/invalid AI response triggers fallback.
E. Explanation does not alter payment plan.
F. Explanation does not alter safe amount.
G. Explanation does not alter status.
H. Explanation does not alter payment method.
I. Spending changes remain unchanged.
J. Token usage is recorded.
K. API keys are not written to usage reports/logs.
"""

from decimal import Decimal
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import UserProfile, RequestItem, FinancialEvent
from planner import PlannerDecision
from explanation import ExplanationGenerator, TokenAccountant, PRICING_PER_MILLION


@pytest.fixture
def sample_profile():
    return UserProfile(
        user_id="user_01",
        home_currency="EUR",
        current_available_balance=5000.0,
        minimum_balance_to_keep=1000.0,
    )


@pytest.fixture
def sample_request():
    return RequestItem(
        request_id="request_test_01",
        user_id="user_01",
        request_date="2026-06-01",
        request_type="purchase",
        requested_amount=1500.0,
        desired_completion_date="2026-06-30",
        allows_partial_payment=True,
        request_text="Can I buy a new laptop?",
    )


@pytest.fixture
def sample_decision():
    return PlannerDecision(
        request_id="request_test_01",
        user_id="user_01",
        amount_safe_to_pay=Decimal("1500.00"),
        affordability_status="affordable_now",
        recommended_payment_method="full_payment",
        payment_plan="2026-06-01:1500",
        earliest_date_for_full_payment="2026-06-01",
        spending_changes_needed="none",
    )


# Test A: AI explanation generated from deterministic decision
def test_a_ai_explanation_generated_from_deterministic_decision(sample_profile, sample_request, sample_decision):
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant)
    
    # Generate explanation
    exp = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert isinstance(exp, str)
    assert len(exp) > 10
    assert "EUR" in exp
    assert "1,500" in exp or "1500" in exp
    assert "1,000" in exp or "1000" in exp


# Test B: AI cannot modify deterministic fields
def test_b_ai_cannot_modify_deterministic_fields(sample_profile, sample_request, sample_decision):
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant)
    
    # Snapshot original fields
    orig_safe = sample_decision.amount_safe_to_pay
    orig_status = sample_decision.affordability_status
    orig_method = sample_decision.recommended_payment_method
    orig_plan = sample_decision.payment_plan
    orig_date = sample_decision.earliest_date_for_full_payment
    orig_changes = sample_decision.spending_changes_needed
    
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    
    assert sample_decision.amount_safe_to_pay == orig_safe
    assert sample_decision.affordability_status == orig_status
    assert sample_decision.recommended_payment_method == orig_method
    assert sample_decision.payment_plan == orig_plan
    assert sample_decision.earliest_date_for_full_payment == orig_date
    assert sample_decision.spending_changes_needed == orig_changes


# Test C: Fallback explanation works when model call fails
def test_c_fallback_explanation_works_when_model_fails(sample_profile, sample_request, sample_decision):
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant, api_key="dummy_key_for_test")
    
    # Mock network failure
    with patch.object(gen, "call_gemini_api", return_value=None):
        exp = gen.generate_explanation(sample_decision, sample_profile, sample_request)
        
    assert isinstance(exp, str)
    assert len(exp) > 10
    assert accountant.fallback_calls == 1
    assert "Pay EUR 1,500 today" in exp


# Test D: Missing or invalid AI response triggers fallback
def test_d_missing_invalid_ai_response_triggers_fallback(sample_profile, sample_request, sample_decision):
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant, api_key="dummy_key_for_test")
    
    # Case 1: Empty response from LLM
    with patch.object(gen, "call_gemini_api", return_value=("", 50, 0)):
        exp1 = gen.generate_explanation(sample_decision, sample_profile, sample_request)
        assert len(exp1) > 10
        assert "Pay EUR 1,500 today" in exp1
        
    # Case 2: Response containing forbidden system implementation words
    forbidden_resp = "Based on planner.py and Phase 4 benchmark, you can afford it."
    with patch.object(gen, "call_gemini_api", return_value=(forbidden_resp, 50, 15)):
        exp2 = gen.generate_explanation(sample_decision, sample_profile, sample_request)
        assert "planner.py" not in exp2
        assert "Phase 4" not in exp2
        assert "Pay EUR 1,500 today" in exp2


# Test E: Explanation does not alter payment plan
def test_e_explanation_does_not_alter_payment_plan(sample_profile, sample_request, sample_decision):
    sample_decision.payment_plan = "2026-06-01:500|2026-06-15:1000"
    gen = ExplanationGenerator()
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert sample_decision.payment_plan == "2026-06-01:500|2026-06-15:1000"


# Test F: Explanation does not alter safe amount
def test_f_explanation_does_not_alter_safe_amount(sample_profile, sample_request, sample_decision):
    sample_decision.amount_safe_to_pay = Decimal("342.50")
    gen = ExplanationGenerator()
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert sample_decision.amount_safe_to_pay == Decimal("342.50")


# Test G: Explanation does not alter status
def test_g_explanation_does_not_alter_status(sample_profile, sample_request, sample_decision):
    sample_decision.affordability_status = "affordable_later"
    sample_decision.earliest_date_for_full_payment = "2026-06-15"
    gen = ExplanationGenerator()
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert sample_decision.affordability_status == "affordable_later"


# Test H: Explanation does not alter payment method
def test_h_explanation_does_not_alter_payment_method(sample_profile, sample_request, sample_decision):
    sample_decision.recommended_payment_method = "installments"
    gen = ExplanationGenerator()
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert sample_decision.recommended_payment_method == "installments"


# Test I: Spending changes remain unchanged
def test_i_spending_changes_remain_unchanged(sample_profile, sample_request, sample_decision):
    sample_decision.spending_changes_needed = "stop:event_476|reduce_to:event_989:500"
    gen = ExplanationGenerator()
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    assert sample_decision.spending_changes_needed == "stop:event_476|reduce_to:event_989:500"


# Test J: Token usage is recorded
def test_j_token_usage_is_recorded(sample_profile, sample_request, sample_decision):
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant)
    
    assert accountant.total_requests == 0
    assert accountant.total_tokens == 0
    
    _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
    
    assert accountant.total_requests == 1
    assert accountant.total_tokens > 0
    assert accountant.avg_tokens_per_request > 0
    assert accountant.records[0].request_id == "request_test_01"


# Test K: API keys are not written to usage reports or logs
def test_k_api_keys_are_not_written_to_usage_reports_or_logs(sample_profile, sample_request, sample_decision):
    secret_key = "TEST_SECRET_KEY_REDACTED"
    accountant = TokenAccountant()
    gen = ExplanationGenerator(accountant=accountant, api_key=secret_key)
    
    with patch.object(gen, "call_gemini_api", return_value=("Valid explanation text.", 80, 20)):
        _ = gen.generate_explanation(sample_decision, sample_profile, sample_request)
        
    report = accountant.generate_report_markdown()
    assert secret_key not in report
    assert "SECRET" not in report
    assert accountant.total_calls == 1
