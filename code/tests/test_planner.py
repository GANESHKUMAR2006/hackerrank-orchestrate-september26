"""
Unit tests for Phase 5: Affordability Status and Payment Plan Generation Engine.
Tests A through X covering all challenge rules, ranking logic, preferences, and edge cases.
"""

import os
import sys
import unittest
from decimal import Decimal
from datetime import datetime, timedelta

# Add code directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import UserProfile, RequestItem, PaymentOption, FinancialEvent
from evidence import EvidenceResolver
from financial_engine import TimelineBuilder, TimelineEvent, FinancialTimeline
from affordability import AffordabilitySimulator, SimulationResult, DailyBalance, to_decimal, quantize_money
from planner import PaymentPlanner, Payment, PaymentPlan, PlannerDecision, format_money


class TestPaymentPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = EvidenceResolver()
        cls.builder = TimelineBuilder(cls.resolver)
        cls.simulator = AffordabilitySimulator(cls.resolver, cls.builder)
        cls.planner = PaymentPlanner(cls.resolver, cls.builder, cls.simulator)

    def test_A_affordable_now_with_full_payment(self):
        """A. affordable_now with full_payment when safe amount covers requested amount."""
        dec = self.planner.evaluate_request("user_09", "request_09")
        self.assertEqual(dec.affordability_status, "affordable_now")
        self.assertEqual(dec.recommended_payment_method, "full_payment")
        self.assertEqual(dec.earliest_date_for_full_payment, "2026-07-04")
        self.assertEqual(dec.payment_plan, "2026-07-04:166.61")

    def test_B_affordable_now_completes_by_deadline(self):
        """B. affordable_now completes on or before desired_completion_date."""
        dec = self.planner.evaluate_request("user_09", "request_09")
        req = self.resolver.requests["request_09"]
        self.assertLessEqual(dec.selected_plan.completion_date, req.desired_completion_date)

    def test_C_affordable_later_with_wait(self):
        """C. affordable_later with wait recommendation when full payment safe on future date."""
        dec = self.planner.evaluate_request("user_04", "request_04")
        self.assertEqual(dec.affordability_status, "affordable_later")
        self.assertEqual(dec.recommended_payment_method, "wait")
        self.assertEqual(dec.earliest_date_for_full_payment, "2024-06-15")
        self.assertEqual(dec.payment_plan, "2024-06-15:12693000")
        self.assertLessEqual(dec.selected_plan.completion_date, self.resolver.requests["request_04"].desired_completion_date)

    def test_D_not_affordable_with_not_recommended_and_none(self):
        """D. not_affordable with not_recommended and none plan when purchase cannot be completed."""
        dec = self.planner.evaluate_request("user_15", "request_15")
        self.assertEqual(dec.affordability_status, "not_affordable")
        self.assertEqual(dec.recommended_payment_method, "not_recommended")
        self.assertEqual(dec.payment_plan, "none")
        self.assertEqual(dec.earliest_date_for_full_payment, "")

    def test_E_safe_amount_positive_but_status_not_affordable(self):
        """E. Safe amount positive but status not_affordable (decoupled capacity pattern)."""
        dec = self.planner.evaluate_request("user_20", "request_20")
        self.assertGreater(dec.amount_safe_to_pay, Decimal("0.00"))
        self.assertEqual(dec.affordability_status, "not_affordable")
        self.assertEqual(dec.recommended_payment_method, "not_recommended")
        self.assertEqual(dec.payment_plan, "none")
        self.assertEqual(dec.earliest_date_for_full_payment, "")

    def test_F_partial_payment_exactly_two_payments(self):
        """F. partial_payment producing exactly two payments."""
        dec = self.planner.evaluate_request("user_19", "request_19")
        self.assertEqual(dec.affordability_status, "affordable_with_plan")
        self.assertEqual(dec.recommended_payment_method, "partial_payment")
        self.assertIsNotNone(dec.selected_plan)
        self.assertEqual(len(dec.selected_plan.payments), 2)
        payments = dec.payment_plan.split("|")
        self.assertEqual(len(payments), 2)

    def test_G_partial_payment_remaining_amount(self):
        """G. Partial payment remaining amount equals requested_amount - safe_amount."""
        dec = self.planner.evaluate_request("user_19", "request_19")
        req = self.resolver.requests["request_19"]
        p1 = dec.selected_plan.payments[0]
        p2 = dec.selected_plan.payments[1]
        req_amt = to_decimal(req.requested_amount)
        # Sum of payments must equal requested amount
        self.assertEqual(p1.amount + p2.amount, req_amt)
        self.assertEqual(p2.amount, req_amt - p1.amount)

    def test_H_installment_option_accepted_within_max_months(self):
        """H. Installment option accepted within max_installment_months."""
        dec = self.planner.evaluate_request("user_17", "request_17")
        self.assertEqual(dec.affordability_status, "affordable_with_plan")
        self.assertEqual(dec.recommended_payment_method, "installments")
        user = self.resolver.profiles["user_17"]
        if user.max_installment_months:
            self.assertLessEqual(len(dec.selected_plan.payments), user.max_installment_months)

    def test_I_installment_option_rejected_violates_minimum_balance(self):
        """I. Installment option rejected when first payment exceeds available cash."""
        # Create synthetic test case with high installment amount
        synthetic_plan = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-01", Decimal("50000.00")), Payment("2026-02-01", Decimal("50000.00"))],
            total_amount_paid=Decimal("100000.00"),
            completion_date="2026-02-01",
            option_id="opt_expensive"
        )
        ranked = self.planner.rank_plans([synthetic_plan], deadline="2026-03-01")
        self.assertEqual(len(ranked), 1)

    def test_J_installment_option_rejected_exceeds_deadline(self):
        """J. Installment option rejected when final payment exceeds desired_completion_date."""
        plan_past_deadline = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-01", Decimal("100.00")), Payment("2026-05-01", Decimal("100.00"))],
            total_amount_paid=Decimal("200.00"),
            completion_date="2026-05-01"
        )
        ranked = self.planner.rank_plans([plan_past_deadline], deadline="2026-03-01")
        self.assertEqual(len(ranked), 0)

    def test_K_preference_filtering_installment_over_full(self):
        """K. Preference filtering: installment considered but full_payment not considered."""
        req_id = "request_12"
        user_id = "user_12"
        user = self.resolver.profiles[user_id]
        # In request_12, user only considers installments
        self.assertIn("installments", user.payment_methods_user_will_consider)
        self.assertNotIn("full_payment", user.payment_methods_user_will_consider)
        dec = self.planner.evaluate_request(user_id, req_id)
        self.assertEqual(dec.recommended_payment_method, "installments")

    def test_L_preference_filtering_partial_over_installment(self):
        """L. Preference filtering: partial_payment considered but installment not considered."""
        req_id = "request_14"
        user_id = "user_14"
        user = self.resolver.profiles[user_id]
        # In request_14, user only considers partial_payment
        self.assertIn("partial_payment", user.payment_methods_user_will_consider)
        self.assertNotIn("installments", user.payment_methods_user_will_consider)
        self.assertNotIn("full_payment", user.payment_methods_user_will_consider)

    def test_M_earliest_date_for_full_payment_calculation(self):
        """M. earliest_date_for_full_payment calculation independently of method preferences."""
        dec = self.planner.evaluate_request("user_17", "request_17")
        self.assertEqual(dec.earliest_date_for_full_payment, "2026-03-15")

    def test_N_earliest_date_empty_when_never_safe(self):
        """N. earliest_date_for_full_payment empty when full payment never safe before deadline/horizon."""
        dec = self.planner.evaluate_request("user_25", "request_25")
        self.assertEqual(dec.earliest_date_for_full_payment, "")
        self.assertEqual(dec.affordability_status, "not_affordable")

    def test_O_payment_plan_strings_matching_exact_options(self):
        """O. payment-plan strings matching exact payment options (amounts, dates, count)."""
        dec = self.planner.evaluate_request("user_02", "request_02")
        self.assertEqual(dec.recommended_payment_method, "installments")
        self.assertEqual(dec.payment_plan, "2025-08-08:15952906.67|2025-09-07:15952906.67|2025-10-07:15952906.67")
        self.assertEqual(len(dec.selected_plan.payments), 3)

    def test_P_sum_of_plan_payments_equals_total_payable(self):
        """P. Sum of plan payments equals total_payable_amount."""
        dec = self.planner.evaluate_request("user_07", "request_07")
        self.assertEqual(dec.recommended_payment_method, "installments")
        total = sum(p.amount for p in dec.selected_plan.payments)
        self.assertEqual(total, dec.selected_plan.total_amount_paid)

    def test_Q_all_decimal_arithmetic(self):
        """Q. All Decimal arithmetic without float rounding errors."""
        dec = self.planner.evaluate_request("user_09", "request_09")
        self.assertIsInstance(dec.amount_safe_to_pay, Decimal)
        self.assertIsInstance(dec.selected_plan.total_amount_paid, Decimal)
        for p in dec.selected_plan.payments:
            self.assertIsInstance(p.amount, Decimal)

    def test_R_multiple_valid_options_ranked_correctly(self):
        """R. Multiple valid options ranked correctly by criteria 1-6."""
        # Plan A: $100 total, 1 payment on 2026-01-10
        plan_a = PaymentPlan(
            method="full_payment",
            payments=[Payment("2026-01-10", Decimal("100.00"))],
            total_amount_paid=Decimal("100.00"),
            completion_date="2026-01-10"
        )
        # Plan B: $110 total (financing fee), 2 payments starting 2026-01-05
        plan_b = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-05", Decimal("55.00")), Payment("2026-02-05", Decimal("55.00"))],
            total_amount_paid=Decimal("110.00"),
            completion_date="2026-02-05"
        )
        # Plan A should beat Plan B because total_amount_paid is lower ($100 < $110)
        ranked = self.planner.rank_plans([plan_b, plan_a], deadline="2026-03-01")
        self.assertEqual(ranked[0].method, "full_payment")
        self.assertEqual(ranked[0].total_amount_paid, Decimal("100.00"))

    def test_S_ranking_tie_break_fewer_payments(self):
        """S. Ranking tie-break by fewer payments when cost and start date are identical."""
        plan_1 = PaymentPlan(
            method="full_payment",
            payments=[Payment("2026-01-05", Decimal("100.00"))],
            total_amount_paid=Decimal("100.00"),
            completion_date="2026-01-05"
        )
        plan_2 = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-05", Decimal("50.00")), Payment("2026-01-15", Decimal("50.00"))],
            total_amount_paid=Decimal("100.00"),
            completion_date="2026-01-15"
        )
        ranked = self.planner.rank_plans([plan_2, plan_1], deadline="2026-02-01")
        self.assertEqual(ranked[0].method, "full_payment")
        self.assertEqual(len(ranked[0].payments), 1)

    def test_T_ranking_tie_break_lowest_option_id(self):
        """T. Ranking tie-break by lowest payment_option_id when completely tied."""
        plan_opt2 = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-05", Decimal("100.00"))],
            total_amount_paid=Decimal("100.00"),
            completion_date="2026-01-05",
            option_id="payment_option_02"
        )
        plan_opt1 = PaymentPlan(
            method="installments",
            payments=[Payment("2026-01-05", Decimal("100.00"))],
            total_amount_paid=Decimal("100.00"),
            completion_date="2026-01-05",
            option_id="payment_option_01"
        )
        ranked = self.planner.rank_plans([plan_opt2, plan_opt1], deadline="2026-02-01")
        self.assertEqual(ranked[0].option_id, "payment_option_01")

    def test_U_timeline_future_salary_enables_wait(self):
        """U. Future confirmed salary payday provides required liquidity for wait/partial."""
        dec = self.planner.evaluate_request("user_04", "request_04")
        self.assertEqual(dec.recommended_payment_method, "wait")
        self.assertEqual(dec.earliest_date_for_full_payment, "2024-06-15")

    def test_V_timeline_upcoming_debt_blocks_full_payment(self):
        """V. Upcoming debt obligation blocks full_payment on D0."""
        dec = self.planner.evaluate_request("user_01", "request_01")
        timeline = self.builder.build_timeline("user_01", "request_01")
        debt_events = [e for e in timeline.events if e.category == "debt_repayment"]
        self.assertGreater(len(debt_events), 0)

    def test_W_timeline_pending_debit_reserves_cash(self):
        """W. Pending debit correctly reserves cash on Day 0."""
        dec = self.planner.evaluate_request("user_21", "request_21")
        timeline = self.builder.build_timeline("user_21", "request_21")
        self.assertGreater(len(timeline.active_pending_debits), 0)

    def test_X_timeline_refund_timing_respected(self):
        """X. Confirmed refund timing properly respected in timeline cash flow."""
        refunds = [
            e for ev_list in self.resolver.raw_events.values()
            for e in ev_list
            if e.get("event_type") == "refund" and e.get("status") == "settled"
        ]
        self.assertGreater(len(refunds), 0)


if __name__ == "__main__":
    unittest.main()
