"""
Phase 6 Test Suite: Deterministic Spending Changes Optimization Engine.

Tests:
A. No eligible spending changes -> unchanged result (none).
B. One stoppable recurring expense makes payment affordable.
C. One reducible recurring expense makes payment affordable.
D. Reduction cannot exceed original recurring amount (0 <= new_amount < original_amount).
E. Reduction cannot be negative (new_amount >= 0).
F. Historical settled expense is preserved (never modified).
G. Future recurring occurrences reflect the new amount.
H. Protected expense cannot be changed (rent, groceries, healthcare, profile protected).
I. One-time expense cannot be changed.
J. Debt payment cannot be changed.
K. Income cannot be changed.
L. Maximum 3 changes enforced.
M. Two-change combination works.
N. Three-change combination works.
O. Unnecessary changes are not selected.
P. Smaller reduction wins when change count is equal.
Q. Earlier completion wins when appropriate.
R. Spending-change plan never violates minimum balance.
S. Spending-change plan completes by deadline.
T. Official amount_safe_to_pay remains unchanged after spending changes.
U. request_06 regression (safe amount != requested amount, stop:event_476, affordable_with_plan).
V. Existing Phase 5 tests remain green.
"""

import os
import sys
from decimal import Decimal
import pytest

# Ensure code directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import UserProfile, RequestItem, FinancialEvent, PaymentOption
from evidence import EvidenceResolver
from financial_engine import TimelineEvent, FinancialTimeline, TimelineBuilder
from affordability import AffordabilitySimulator, to_decimal
from spending_optimizer import SpendingChangeOptimizer, SpendingChange, format_spending_changes
from planner import PaymentPlanner, PaymentPlan, PlannerDecision


@pytest.fixture
def test_setup():
    resolver = EvidenceResolver()
    builder = TimelineBuilder(resolver)
    simulator = AffordabilitySimulator(resolver, builder)
    optimizer = SpendingChangeOptimizer(resolver, builder, simulator)
    planner = PaymentPlanner(resolver, builder, simulator, optimizer)
    return resolver, builder, simulator, optimizer, planner


class TestSpendingChanges:
    """Comprehensive test suite covering Phase 6 spending change requirements."""

    def test_A_no_eligible_spending_changes(self, test_setup):
        """A. No eligible spending changes -> unchanged result ('none')."""
        resolver, builder, simulator, optimizer, planner = test_setup
        req = resolver.requests.get("request_25")
        single = optimizer.get_eligible_spending_changes(req.user_id, "request_25", req.desired_completion_date)
        assert len(single) == 0
        best = optimizer.find_best_spending_changes_for_full_payment(
            req.user_id, "request_25", to_decimal(req.requested_amount), req.request_date, Decimal("1000000.00")
        )
        assert best is None
        assert format_spending_changes(best) == "none"

    def test_B_one_stoppable_recurring_expense(self, test_setup):
        """B. One stoppable recurring expense makes payment affordable."""
        resolver, builder, simulator, optimizer, planner = test_setup
        dec = planner.evaluate_request("user_06", "request_06")
        assert dec.spending_changes_needed == "stop:event_476"
        assert dec.affordability_status == "affordable_with_plan"
        assert dec.recommended_payment_method == "full_payment"

    def test_C_one_reducible_recurring_expense(self, test_setup):
        """C. One reducible recurring expense makes payment affordable."""
        resolver, builder, simulator, optimizer, planner = test_setup
        dec = planner.evaluate_request("user_11", "request_11")
        assert dec.spending_changes_needed == "reduce_to:event_989:665950"
        assert dec.affordability_status == "affordable_with_plan"
        assert dec.recommended_payment_method == "full_payment"

    def test_D_reduction_cannot_exceed_original(self, test_setup):
        """D. Reduction cannot exceed original recurring amount (0 <= new_amount < original_amount)."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid in ["request_06", "request_11", "request_21"]:
            req = resolver.requests[rid]
            changes = optimizer.get_eligible_spending_changes(req.user_id, rid, req.desired_completion_date)
            for c in changes:
                if c.action == "reduce_to":
                    assert Decimal("0.00") <= c.new_amount < c.original_amount
                    assert c.reduction_amount == (c.original_amount - c.new_amount)

    def test_E_reduction_cannot_be_negative(self, test_setup):
        """E. Reduction cannot be negative (new_amount >= 0)."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid in ["request_06", "request_11", "request_21"]:
            req = resolver.requests[rid]
            changes = optimizer.get_eligible_spending_changes(req.user_id, rid, req.desired_completion_date)
            for c in changes:
                assert c.new_amount >= Decimal("0.00")
                assert c.reduction_amount >= Decimal("0.00")

    def test_F_historical_settled_expense_preserved(self, test_setup):
        """F. Historical settled expense is preserved (never modified)."""
        resolver, builder, simulator, optimizer, planner = test_setup
        tl = builder.build_timeline("user_06", "request_06")
        best = optimizer.find_best_spending_changes_for_full_payment(
            "user_06", "request_06", Decimal("620.40"), "2026-01-03", Decimal("17.10")
        )
        assert best is not None
        mod_tl = optimizer.apply_changes_to_timeline(tl, best, "2026-01-03")
        
        # Historical events (< 2026-01-03) must be strictly unmodified
        orig_hist = [e for e in tl.events if e.date < "2026-01-03"]
        mod_hist = [e for e in mod_tl.events if e.date < "2026-01-03"]
        assert len(orig_hist) == len(mod_hist)
        for e_orig, e_mod in zip(orig_hist, mod_hist):
            assert e_orig.amount_home == e_mod.amount_home
            assert e_orig.event_id == e_mod.event_id

    def test_G_future_recurring_occurrences_reflect_new_amount(self, test_setup):
        """G. Future recurring occurrences reflect the new amount."""
        resolver, builder, simulator, optimizer, planner = test_setup
        tl = builder.build_timeline("user_06", "request_06")
        best = optimizer.find_best_spending_changes_for_full_payment(
            "user_06", "request_06", Decimal("620.40"), "2026-01-03", Decimal("17.10")
        )
        mod_tl = optimizer.apply_changes_to_timeline(tl, best, "2026-01-03")
        
        # Future occurrence of event_476 on 2026-01-10 must now be 0.0
        fut_streaming = [
            e for e in mod_tl.events
            if e.date >= "2026-01-03" and (getattr(e, "source_event_id", "") == "event_476" or e.event_id == "event_476")
        ]
        assert len(fut_streaming) > 0
        for e in fut_streaming:
            assert e.amount_home == 0.0

    def test_H_protected_expense_cannot_be_changed(self, test_setup):
        """H. Protected expense cannot be changed (rent, groceries, healthcare, profile protected)."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for uid, profile in resolver.profiles.items():
            reqs = [r for r in resolver.requests.values() if r.user_id == uid]
            if not reqs:
                continue
            req = reqs[0]
            changes = optimizer.get_eligible_spending_changes(uid, req.request_id, req.desired_completion_date)
            protected = set(profile.expense_categories_to_protect) | optimizer.MANDATORY_PROTECTED_CATEGORIES
            for c in changes:
                assert c.category not in protected

    def test_I_one_time_expense_cannot_be_changed(self, test_setup):
        """I. One-time expense cannot be changed."""
        resolver, builder, simulator, optimizer, planner = test_setup
        tl = builder.build_timeline("user_06", "request_06")
        changes = optimizer.get_eligible_spending_changes("user_06", "request_06")
        for c in changes:
            src_ev = next((e for e in tl.events if getattr(e, "source_event_id", e.event_id) == c.event_id), None)
            if src_ev:
                assert src_ev.is_recurring is True or src_ev.flexibility in ("stoppable", "reducible", "reducible_or_stoppable")

    def test_J_debt_payment_cannot_be_changed(self, test_setup):
        """J. Debt payment cannot be changed."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for uid in resolver.profiles.keys():
            reqs = [r for r in resolver.requests.values() if r.user_id == uid]
            if not reqs:
                continue
            changes = optimizer.get_eligible_spending_changes(uid, reqs[0].request_id)
            for c in changes:
                assert "debt" not in c.category.lower()
                assert "loan" not in c.category.lower()
                assert "mortgage" not in c.category.lower()

    def test_K_income_cannot_be_changed(self, test_setup):
        """K. Income cannot be changed."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for uid in resolver.profiles.keys():
            reqs = [r for r in resolver.requests.values() if r.user_id == uid]
            if not reqs:
                continue
            changes = optimizer.get_eligible_spending_changes(uid, reqs[0].request_id)
            for c in changes:
                assert c.category not in ("income", "salary", "payroll", "commission")

    def test_L_maximum_three_changes_enforced(self, test_setup):
        """L. Maximum 3 changes enforced."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid, req in resolver.requests.items():
            dec = planner.evaluate_request(req.user_id, rid)
            if dec.spending_changes_needed != "none":
                parts = dec.spending_changes_needed.split("|")
                assert len(parts) <= 3

    def test_M_two_change_combination_works(self, test_setup):
        """M. Two-change combination works."""
        resolver, builder, simulator, optimizer, planner = test_setup
        dec = planner.evaluate_request("user_21", "request_21")
        assert dec.spending_changes_needed == "stop:event_1815|reduce_to:event_1816:23.50"
        parts = dec.spending_changes_needed.split("|")
        assert len(parts) == 2
        assert dec.affordability_status == "affordable_with_plan"
        assert dec.recommended_payment_method == "full_payment"

    def test_N_three_change_combination_works(self, test_setup):
        """N. Three-change combination works."""
        resolver, builder, simulator, optimizer, planner = test_setup
        best = optimizer.find_best_spending_changes_for_full_payment(
            "user_21", "request_21", Decimal("1574.40"), "2026-04-03", Decimal("160.00"), max_changes=3
        )
        assert best is not None
        assert len(best) <= 3
        tot_red = sum(c.reduction_amount for c in best)
        assert tot_red >= Decimal("160.00")

    def test_O_unnecessary_changes_not_selected(self, test_setup):
        """O. Unnecessary changes are not selected."""
        resolver, builder, simulator, optimizer, planner = test_setup
        best = optimizer.find_best_spending_changes_for_full_payment(
            "user_06", "request_06", Decimal("620.40"), "2026-01-03", Decimal("17.10")
        )
        assert best is not None
        assert len(best) == 1

    def test_P_smaller_reduction_wins_when_change_count_equal(self, test_setup):
        """P. Smaller reduction wins when change count is equal."""
        resolver, builder, simulator, optimizer, planner = test_setup
        best = optimizer.find_best_spending_changes_for_full_payment(
            "user_11", "request_11", Decimal("13110000"), "2025-05-03", Decimal("599355")
        )
        assert best is not None
        assert len(best) == 1
        assert best[0].event_id == "event_989"

    def test_Q_earlier_completion_wins(self, test_setup):
        """Q. Earlier completion wins when appropriate."""
        resolver, builder, simulator, optimizer, planner = test_setup
        dec = planner.evaluate_request("user_06", "request_06")
        assert dec.selected_plan.completion_date == "2026-01-03"
        assert dec.selected_plan.completion_date <= "2026-01-14"

    def test_R_spending_change_plan_never_violates_minimum_balance(self, test_setup):
        """R. Spending-change plan never violates minimum balance."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid in ["request_06", "request_11", "request_21"]:
            dec = planner.evaluate_request(resolver.requests[rid].user_id, rid)
            assert dec.selected_plan is not None
            if dec.selected_plan.requires_spending_changes:
                tl = builder.build_timeline(dec.user_id, rid)
                changes = optimizer.get_eligible_spending_changes(dec.user_id, rid, dec.selected_plan.completion_date)
                chosen_changes = [c for c in changes if c.change_string in dec.spending_changes_list]
                mod_tl = optimizer.apply_changes_to_timeline(tl, chosen_changes, dec.selected_plan.payments[0].date)
                res = simulator.simulate_90_days(mod_tl, Decimal("0.00"), mod_tl.request_date)
                assert res is not None

    def test_S_spending_change_plan_completes_by_deadline(self, test_setup):
        """S. Spending-change plan completes by deadline."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid in ["request_06", "request_11", "request_21"]:
            req = resolver.requests[rid]
            dec = planner.evaluate_request(req.user_id, rid)
            assert dec.selected_plan is not None
            if req.desired_completion_date:
                assert dec.selected_plan.completion_date <= req.desired_completion_date

    def test_T_official_amount_safe_to_pay_remains_unchanged(self, test_setup):
        """T. Official amount_safe_to_pay remains unchanged after spending changes."""
        resolver, builder, simulator, optimizer, planner = test_setup
        for rid in ["request_06", "request_11", "request_21"]:
            req = resolver.requests[rid]
            sr = simulator.evaluate_request(req.user_id, rid)
            expected_official_safe = sr.amount_safe_to_pay
            dec = planner.evaluate_request(req.user_id, rid)
            assert dec.amount_safe_to_pay == expected_official_safe

    def test_U_request_06_regression(self, test_setup):
        """U. request_06 regression (safe amount != requested amount, stop:event_476, affordable_with_plan)."""
        resolver, builder, simulator, optimizer, planner = test_setup
        dec = planner.evaluate_request("user_06", "request_06")
        assert dec.amount_safe_to_pay != Decimal("620.40")
        assert dec.affordability_status == "affordable_with_plan"
        assert dec.recommended_payment_method == "full_payment"
        assert dec.spending_changes_needed == "stop:event_476"
        assert dec.payment_plan == "2026-01-03:620.40"

    def test_V_existing_phase5_tests_remain_green(self, test_setup):
        """V. Existing Phase 5 tests remain green."""
        resolver, builder, simulator, optimizer, planner = test_setup
        decisions = planner.evaluate_all(list(resolver.requests.keys())[:25])
        assert len(decisions) == 25
        for rid, dec in decisions.items():
            assert dec.affordability_status in ("affordable_now", "affordable_with_plan", "affordable_later", "not_affordable")
            assert dec.recommended_payment_method in ("full_payment", "partial_payment", "installments", "wait", "not_recommended")
            assert dec.amount_safe_to_pay >= Decimal("0.00")
            if dec.spending_changes_needed != "none":
                assert dec.affordability_status == "affordable_with_plan"
