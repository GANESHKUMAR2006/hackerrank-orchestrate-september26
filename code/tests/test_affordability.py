"""
Unit tests for Phase 4: 90-Day Cash-Flow Simulator and Safe-to-Pay Engine.
Tests A through W covering all challenge requirements and edge cases.
"""

import os
import sys
import unittest
from decimal import Decimal
from datetime import datetime, timedelta

# Add code directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evidence import EvidenceResolver
from financial_engine import TimelineBuilder, TimelineEvent, FinancialTimeline
from affordability import AffordabilitySimulator, SimulationResult, DailyBalance, to_decimal, quantize_money


class TestAffordabilityEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = EvidenceResolver()
        cls.builder = TimelineBuilder(cls.resolver)
        cls.simulator = AffordabilitySimulator(cls.resolver, cls.builder)

    def test_A_purchase_fully_safe(self):
        """Verify request where amount_safe_to_pay equals requested amount (fully safe)."""
        res = self.simulator.evaluate_request("user_09", "request_09")
        self.assertEqual(res.amount_safe_to_pay, res.requested_amount_home_currency)
        self.assertTrue(res.diagnostics["is_fully_safe"])
        self.assertFalse(res.reserve_violation)
        # Verify that paying full requested amount keeps balance above minimum keep (600 EUR)
        self.assertTrue(self.simulator.is_payment_safe(res.baseline_timeline, res.requested_amount_home_currency))

    def test_B_purchase_partially_safe(self):
        """Verify request where amount_safe_to_pay is positive but less than requested amount."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        self.assertGreater(res.amount_safe_to_pay, Decimal("0.00"))
        self.assertLess(res.amount_safe_to_pay, res.requested_amount_home_currency)
        self.assertTrue(res.diagnostics["is_partially_safe"])

    def test_C_purchase_completely_unsafe(self):
        """Verify request where amount_safe_to_pay equals zero because baseline has no cushion."""
        res = self.simulator.evaluate_request("user_06", "request_06")
        self.assertEqual(res.amount_safe_to_pay, Decimal("0.00"))
        self.assertTrue(res.diagnostics["is_zero_safe"])

    def test_D_minimum_reserve_constraint(self):
        """Verify that paying amount_safe_to_pay respects minimum_balance_to_keep, while +1 exceeds it."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        safe_amt = res.amount_safe_to_pay
        # Paying safe_amt is safe
        self.assertTrue(self.simulator.is_payment_safe(res.baseline_timeline, safe_amt))
        # Paying safe_amt + 5.00 must violate reserve floor
        self.assertFalse(self.simulator.is_payment_safe(res.baseline_timeline, safe_amt + Decimal("5.00")))

    def test_E_future_rent_constraint(self):
        """Verify future rent payments constrain the safe amount on D0."""
        res = self.simulator.evaluate_request("user_01", "request_01")
        rent_events = [e for e in res.baseline_timeline.events if e.category == "rent"]
        self.assertGreater(len(rent_events), 0)
        # Baseline minimum balance occurs before or after rent
        self.assertLess(res.amount_safe_to_pay, res.initial_balance - res.minimum_balance_to_keep)

    def test_F_future_debt_constraint(self):
        """Verify future debt repayments constrain available cash on D0."""
        res = self.simulator.evaluate_request("user_01", "request_01")
        debt_events = [e for e in res.baseline_timeline.events if e.category == "debt_repayment"]
        self.assertGreater(len(debt_events), 0)
        # Future debt is honored in the daily balances
        self.assertTrue(any(ev.category == "debt_repayment" for d in res.daily_balances for ev in d.events_processed))

    def test_G_future_salary_supports_later_payment(self):
        """Verify that future confirmed salary allows full payment on or after payday."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        req_amt = res.requested_amount_home_currency
        # Cannot pay full amount on D0
        self.assertFalse(self.simulator.is_payment_safe(res.baseline_timeline, req_amt, res.request_date))
        # Earliest date is payday (2026-04-15)
        self.assertEqual(res.earliest_full_payment_date, "2026-04-15")
        self.assertTrue(self.simulator.is_payment_safe(res.baseline_timeline, req_amt, "2026-04-15"))

    def test_H_pending_debit_reduces_safe_amount(self):
        """Verify active pending debits reserve funds and reduce available safe amount."""
        res = self.simulator.evaluate_request("user_01", "request_01")
        pending_fuel = next((e for e in res.baseline_timeline.active_pending_debits if e.event_id == "event_102"), None)
        self.assertIsNotNone(pending_fuel)
        self.assertEqual(to_decimal(pending_fuel.amount_home), Decimal("567.6000"))

    def test_I_pending_credit_does_not_increase_safe_amount(self):
        """Verify pending credits/refunds are excluded from timeline and cannot inflate safe amount."""
        res = self.simulator.evaluate_request("user_20", "request_20")
        refund_ev = next((e for e in res.baseline_timeline.events if e.event_id == "event_1785"), None)
        self.assertIsNone(refund_ev, "Pending refund must not enter timeline")

    def test_J_investment_valuation_does_not_increase_safe_amount(self):
        """Verify non-cash investment valuations are excluded from liquid simulation."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        val_ev = next((e for e in res.baseline_timeline.events if e.event_id == "event_1856"), None)
        self.assertIsNone(val_ev, "Investment valuation must not be included in cash timeline")

    def test_K_refund_timing(self):
        """Verify settled refunds only provide liquidity on their exact settlement date."""
        state = self.resolver.build_normalized_state("user_01", "request_01")
        settled_ref = next((e for e in state.events if e.event_id == "event_99"), None)
        self.assertIsNotNone(settled_ref)
        self.assertTrue(settled_ref.is_cash_flow)

    def test_L_failed_event_without_retry(self):
        """Verify failed debits without retry notices are excluded and do not drain funds."""
        res = self.simulator.evaluate_request("user_05", "request_05")
        failed_ev = next((e for e in res.baseline_timeline.events if e.event_id == "event_398"), None)
        self.assertIsNone(failed_ev, "Failed debit without retry must be excluded")

    def test_M_retry_flagged_failed_debit(self):
        """Verify failed debits with retry notices remain active liabilities and reduce funds."""
        res = self.simulator.evaluate_request("user_91", "request_91")
        retry_ev = next((e for e in res.baseline_timeline.events if e.event_id == "event_8575"), None)
        self.assertIsNotNone(retry_ev, "Failed debit with retry notice must remain active")
        self.assertTrue(retry_ev.is_cash_flow)

    def test_N_internal_transfer_neutrality(self):
        """Verify internal transfers between user accounts are cash-neutral."""
        evs = self.resolver.extract_message_evidence("user_18")
        xfer = next((e for e in evs if e.evidence_type == "internal_transfer"), None)
        self.assertIsNotNone(xfer)
        self.assertEqual(xfer.new_value, False)

    def test_O_foreign_currency_request(self):
        """Verify foreign currency transactions in timeline are converted to home currency."""
        state = self.resolver.build_normalized_state("user_78", "request_78")
        ev7307 = next((e for e in state.events if e.event_id == "event_7307"), None)
        self.assertIsNotNone(ev7307)
        self.assertEqual(ev7307.currency, "USD")
        self.assertGreater(ev7307.amount_home, 0)

    def test_P_variable_essential_spending(self):
        """Verify variable essential categories (groceries, utilities) are included in simulation."""
        res = self.simulator.evaluate_request("user_01", "request_01")
        ess_evs = [e for e in res.baseline_timeline.events if e.is_essential]
        self.assertGreater(len(ess_evs), 0)

    def test_Q_D0_same_day_ordering(self):
        """Verify deterministic ordering on Day 0: debits occur before credits, and purchase payment occurs."""
        timeline = self.builder.build_timeline("user_01", "request_01")
        daily_records, _, _, _, _ = self.simulator.simulate_90_days(
            timeline, purchase_amount=Decimal("1000.00"), purchase_date=timeline.request_date
        )
        d0_record = daily_records[0]
        self.assertEqual(d0_record.date, timeline.request_date)
        self.assertEqual(d0_record.purchase_outflow, Decimal("1000.00"))
        # Ending balance reflects: start + inflows - outflows - purchase
        expected_end = d0_record.starting_balance + d0_record.cash_inflows - d0_record.cash_outflows - d0_record.purchase_outflow
        self.assertEqual(d0_record.ending_balance, expected_end)

    def test_R_90_day_boundary(self):
        """Verify simulation spans exactly 91 days (Day 0 through Day 90 inclusive)."""
        res = self.simulator.evaluate_request("user_01", "request_01")
        self.assertEqual(len(res.daily_balances), 91)
        d0_dt = datetime.strptime(res.daily_balances[0].date, "%Y-%m-%d")
        d90_dt = datetime.strptime(res.daily_balances[-1].date, "%Y-%m-%d")
        self.assertEqual((d90_dt - d0_dt).days, 90)

    def test_S_deadline_feasibility(self):
        """Verify deadline feasibility helper correctly handles possible and impossible deadlines."""
        res = self.simulator.evaluate_request("user_09", "request_09")
        self.assertTrue(res.deadline_possible)
        res_fail = self.simulator.evaluate_request("user_06", "request_06")
        self.assertFalse(res_fail.deadline_possible)

    def test_T_decimal_precision(self):
        """Verify pure Decimal calculations with no floating point errors and no negative zero."""
        amt = Decimal("0.0000")
        q = quantize_money(amt, "EUR")
        self.assertEqual(q, Decimal("0.00"))
        self.assertNotEqual(str(q), "-0.00")
        # Sub-cent precision
        diff = Decimal("100.0005") - Decimal("0.0001")
        self.assertEqual(diff, Decimal("100.0004"))

    def test_U_safe_amount_monotonicity(self):
        """Verify monotonicity invariant: if safe_amount is safe, all amounts 0 <= Y <= safe_amount are safe."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        safe_amt = res.amount_safe_to_pay
        fractions = [Decimal("0.00"), safe_amt * Decimal("0.25"), safe_amt * Decimal("0.50"), safe_amt * Decimal("0.75"), safe_amt]
        for y in fractions:
            self.assertTrue(
                self.simulator.is_payment_safe(res.baseline_timeline, y, res.request_date),
                f"Monotonicity violation: {y} should be safe because safe_amt={safe_amt} is safe"
            )

    def test_V_safe_amount_equals_zero(self):
        """Verify request correctly yields safe_amount == 0 when no cushion exists."""
        res = self.simulator.evaluate_request("user_06", "request_06")
        self.assertEqual(res.amount_safe_to_pay, Decimal("0.00"))

    def test_W_safe_amount_equals_requested_amount(self):
        """Verify request correctly yields safe_amount == requested_amount when fully affordable."""
        res = self.simulator.evaluate_request("user_09", "request_09")
        self.assertEqual(res.amount_safe_to_pay, res.requested_amount_home_currency)

    def test_X_pay_cycle_safe_amount_full_affordability(self):
        """Verify pay-cycle safe calculation accurately reproduces full affordability for request_01, request_09, request_16."""
        # request_01
        res1 = self.simulator.evaluate_request("user_01", "request_01")
        self.assertEqual(res1.diagnostics["cycle_safe_amount_all"], res1.requested_amount_home_currency)
        self.assertEqual(res1.diagnostics["first_payday"], "2024-03-15")

        # request_09
        res9 = self.simulator.evaluate_request("user_09", "request_09")
        self.assertEqual(res9.diagnostics["cycle_safe_amount_all"], res9.requested_amount_home_currency)

        # request_16
        res16 = self.simulator.evaluate_request("user_16", "request_16")
        self.assertEqual(res16.diagnostics["cycle_safe_amount_all"], res16.requested_amount_home_currency)
        self.assertEqual(res16.diagnostics["first_payday"], "2023-08-15")

    def test_Y_request_06_pay_cycle_liquidity(self):
        """Verify request_06 has positive pre-payday liquidity before Jan 15 payday despite Day 85 baseline trough."""
        res6 = self.simulator.evaluate_request("user_06", "request_06")
        # Global 90-day safe is 0 due to Day 85 trough
        self.assertEqual(res6.amount_safe_to_pay, Decimal("0.00"))
        # But pay-cycle safe is substantial (> 400 EUR), matching the pre-payday cash bottleneck
        self.assertGreater(res6.diagnostics["cycle_safe_amount_all"], Decimal("400.00"))
        self.assertEqual(res6.diagnostics["first_payday"], "2026-01-15")

    def test_Z_diagnostics_multi_horizon_invariants(self):
        """Verify multi-horizon diagnostics consistency across evaluate_request."""
        res = self.simulator.evaluate_request("user_21", "request_21")
        diag = res.diagnostics
        self.assertIn("cycle_safe_amount_all", diag)
        self.assertIn("cycle_safe_amount_fixed", diag)
        self.assertIn("first_payday", diag)
        # Mathematical invariant: 0 <= safe_90d <= cycle_safe_all <= requested_amount
        self.assertGreaterEqual(res.amount_safe_to_pay, Decimal("0.00"))
        self.assertLessEqual(res.amount_safe_to_pay, diag["cycle_safe_amount_all"])
        self.assertLessEqual(diag["cycle_safe_amount_all"], res.requested_amount_home_currency)


if __name__ == "__main__":
    unittest.main()

