"""
Unit tests for Phase 3: Recurrence Detection and 90-Day Timeline Builder.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta

# Add code directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evidence import EvidenceResolver
from financial_engine import TimelineBuilder, TimelineEvent, RecurringPattern, FinancialTimeline

class TestFinancialEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = EvidenceResolver()
        cls.builder = TimelineBuilder(cls.resolver)

    def test_A_monthly_recurrence(self):
        """Verify monthly recurring patterns (e.g. rent, utilities, subscriptions) are detected."""
        timeline_u1 = self.builder.build_timeline("user_01", "request_01")
        # Check detected patterns for user_01
        pats = {p.description: p for p in timeline_u1.detected_patterns}
        self.assertIn("Apartment rent transfer", pats)
        rent_pat = pats["Apartment rent transfer"]
        self.assertEqual(rent_pat.frequency, "monthly")
        self.assertEqual(rent_pat.day_of_month, 2)
        self.assertEqual(rent_pat.amount_home, 5148.0)

    def test_B_weekly_recurrence(self):
        """Verify weekly recurring patterns are detected for high-frequency living expenses."""
        # Find any user with weekly grocery or transport patterns
        timeline = self.builder.build_timeline("user_01", "request_01")
        weekly_pats = [p for p in timeline.detected_patterns if p.frequency == "weekly"]
        self.assertGreater(len(weekly_pats), 0, "Expected at least one weekly pattern")
        self.assertIn(weekly_pats[0].category, ["groceries", "transport", "dining"])

    def test_C_non_recurring_one_time(self):
        """Verify one-off transactions (single historical occurrence) are not classified as recurring."""
        timeline = self.builder.build_timeline("user_01", "request_01")
        # Ensure single one-time expenses are not in detected_patterns
        pat_descs = {p.description for p in timeline.detected_patterns}
        # Check raw events for user_01 that appear only once
        raw_counts = {}
        for e in self.resolver.raw_events["user_01"]:
            raw_counts[e["description"]] = raw_counts.get(e["description"], 0) + 1
        for desc, cnt in raw_counts.items():
            if cnt == 1:
                # Should not be a detected pattern unless inherently monthly
                pat = next((p for p in timeline.detected_patterns if p.description == desc), None)
                if pat:
                    self.assertIn(pat.category, ["rent", "utilities", "salary", "subscription", "debt_repayment"])

    def test_D_explicit_future_event_prevents_duplicate_recurrence(self):
        """Verify explicit scheduled event prevents duplicate inferred occurrence."""
        # user_01 has explicit scheduled salary on 2024-03-15 (event_103)
        timeline = self.builder.build_timeline("user_01", "request_01")
        sal_events = [e for e in timeline.events if e.category == "salary" and e.date == "2024-03-15"]
        # Must be exactly ONE salary event on 2024-03-15
        self.assertEqual(len(sal_events), 1, "Expected exactly 1 salary event on 2024-03-15 (no duplicate)")
        self.assertEqual(sal_events[0].event_id, "event_103")

    def test_E_pending_debit(self):
        """Verify pending debits appear in timeline and reduce available funds."""
        # user_01 has pending fuel authorization on 2024-03-05 (event_102)
        timeline = self.builder.build_timeline("user_01", "request_01")
        fuel = next((e for e in timeline.events if e.event_id == "event_102"), None)
        self.assertIsNotNone(fuel)
        self.assertEqual(fuel.status, "pending")
        self.assertEqual(fuel.direction, "debit")
        self.assertTrue(fuel.is_cash_flow)
        self.assertEqual(fuel.amount_home, 567.6)
        self.assertIn(fuel, timeline.active_pending_debits)

    def test_F_pending_credit(self):
        """Verify pending credits (such as pending refunds) are excluded from timeline cash flows."""
        # user_20 has event_1785 (pending refund)
        timeline = self.builder.build_timeline("user_20", "request_20")
        refund = next((e for e in timeline.events if e.event_id == "event_1785"), None)
        self.assertIsNone(refund, "Pending credit/refund must not enter future timeline cash flows")

    def test_G_failed_event(self):
        """Verify failed events without retry notices are excluded, while those with retries remain."""
        # user_05 has event_398 (failed utility debit) with no retry notice
        timeline_u5 = self.builder.build_timeline("user_05", "request_05")
        ev_failed = next((e for e in timeline_u5.events if e.event_id == "event_398"), None)
        self.assertIsNone(ev_failed, "Failed debit without retry notice must be excluded")

        # user_91 has event_8575 (failed debit with bank retry notice)
        timeline_u91 = self.builder.build_timeline("user_91", "request_91")
        ev_retry = next((e for e in timeline_u91.events if e.event_id == "event_8575"), None)
        self.assertIsNotNone(ev_retry, "Failed debit with retry notice must remain active")
        self.assertTrue(ev_retry.is_cash_flow)

    def test_H_cancelled_event(self):
        """Verify cancelled events are excluded from future cash flow timeline."""
        # user_01 has event_100 (cancelled shopping charge)
        timeline = self.builder.build_timeline("user_01", "request_01")
        ev_canc = next((e for e in timeline.events if e.event_id == "event_100"), None)
        self.assertIsNone(ev_canc, "Cancelled event must not enter timeline")

    def test_I_investment_valuation(self):
        """Verify investment valuation events are non-cash and excluded from liquid timeline."""
        # user_21 has event_1856 (unrealized valuation)
        timeline = self.builder.build_timeline("user_21", "request_21")
        ev_val = next((e for e in timeline.events if e.event_id == "event_1856"), None)
        self.assertIsNone(ev_val, "Investment valuation must not be included in cash timeline")

    def test_J_investment_purchase(self):
        """Verify historical investment purchase was recognized as cash outflow."""
        # user_21 has event_1855 (settled investment purchase)
        state = self.resolver.build_normalized_state("user_21", "request_21")
        ev_pur = next((e for e in state.events if e.event_id == "event_1855"), None)
        self.assertIsNotNone(ev_pur)
        self.assertEqual(ev_pur.direction, "debit")
        self.assertTrue(ev_pur.is_cash_flow)

    def test_K_investment_sale(self):
        """Verify investment sales are recognized as cash inflows when settled."""
        # Find any user with investment_sale
        sale_evs = [
            e for uid, evs in self.resolver.raw_events.items()
            for e in evs if e["event_type"] == "investment_sale"
        ]
        self.assertGreater(len(sale_evs), 0)
        target_uid = sale_evs[0]["user_id"]
        state = self.resolver.build_normalized_state(target_uid)
        ev_sale = next((e for e in state.events if e.event_type == "investment_sale"), None)
        self.assertIsNotNone(ev_sale)
        self.assertEqual(ev_sale.direction, "credit")
        self.assertTrue(ev_sale.is_cash_flow)

    def test_L_refund(self):
        """Verify settled refunds are valid cash flow while pending refunds are ignored."""
        # user_01 has event_99 (settled refund)
        state_u1 = self.resolver.build_normalized_state("user_01", "request_01")
        ref_settled = next((e for e in state_u1.events if e.event_id == "event_99"), None)
        self.assertIsNotNone(ref_settled)
        self.assertTrue(ref_settled.is_cash_flow)

        # user_20 has event_1785 (pending refund)
        state_u20 = self.resolver.build_normalized_state("user_20", "request_20")
        ref_pending = next((e for e in state_u20.events if e.event_id == "event_1785"), None)
        self.assertIsNotNone(ref_pending)
        self.assertFalse(ref_pending.is_cash_flow)

    def test_M_internal_transfer(self):
        """Verify internal transfers are recognized from messages and flagged."""
        ev_u18 = self.resolver.extract_message_evidence("user_18")
        xfer_ev = next((e for e in ev_u18 if e.evidence_type == "internal_transfer"), None)
        self.assertIsNotNone(xfer_ev)
        self.assertEqual(xfer_ev.new_value, False)

    def test_N_salary_recurrence(self):
        """Verify salary is recognized as recurring monthly income on payday."""
        timeline = self.builder.build_timeline("user_01", "request_01")
        sal_events = [e for e in timeline.events if e.category == "salary" and e.direction == "credit"]
        self.assertGreater(len(sal_events), 1, "Expected multiple salary credits across 90-day horizon")
        for s in sal_events:
            self.assertTrue(s.date.endswith("-15"))

    def test_O_salary_message_override(self):
        """Verify salary amount and date modifications from messages are reflected in future salary."""
        # user_02 has message_01 increasing salary to 42,750,000 IDR
        timeline_u2 = self.builder.build_timeline("user_02", "request_02")
        sal_u2 = [e for e in timeline_u2.events if e.category == "salary" and e.direction == "credit"]
        self.assertGreater(len(sal_u2), 0)
        self.assertEqual(sal_u2[0].amount_home, 42750000.0)

        # user_07 has message_05 moving salary date to 23rd
        timeline_u7 = self.builder.build_timeline("user_07", "request_07")
        sal_u7 = [e for e in timeline_u7.events if e.category == "salary" and e.direction == "credit"]
        self.assertGreater(len(sal_u7), 0)
        self.assertTrue(sal_u7[0].date.endswith("-23"))

        # user_12 has message_09 stating contract ended (no future salary)
        timeline_u12 = self.builder.build_timeline("user_12", "request_12")
        sal_u12 = [e for e in timeline_u12.events if e.category == "salary" and e.direction == "credit"]
        self.assertEqual(len(sal_u12), 0, "No salary should be projected when contract ended")

    def test_P_future_scheduled_obligation(self):
        """Verify explicit future scheduled obligations appear on their exact dates."""
        # user_04 has scheduled school fee on 2024-06-11 (event_357)
        timeline = self.builder.build_timeline("user_04", "request_04")
        school_fee = next((e for e in timeline.events if e.event_id == "event_357"), None)
        self.assertIsNotNone(school_fee)
        self.assertEqual(school_fee.date, "2024-06-11")
        self.assertEqual(school_fee.amount_home, 1704300.0)

    def test_Q_90_day_boundary(self):
        """Verify all timeline events fall strictly within [request_date, request_date + 90 days]."""
        for uid in ["user_01", "user_02", "user_03", "user_06", "user_16", "user_21"]:
            timeline = self.builder.build_timeline(uid)
            start_dt = datetime.strptime(timeline.timeline_start, "%Y-%m-%d")
            end_dt = datetime.strptime(timeline.timeline_end, "%Y-%m-%d")
            self.assertEqual((end_dt - start_dt).days, 90)
            for e in timeline.events:
                e_dt = datetime.strptime(e.date, "%Y-%m-%d")
                self.assertGreaterEqual(e_dt, start_dt, f"Event {e.event_id} date {e.date} before start {timeline.timeline_start}")
                self.assertLessEqual(e_dt, end_dt, f"Event {e.event_id} date {e.date} after end {timeline.timeline_end}")

    def test_R_month_end_recurrence(self):
        """Verify month-end recurrence handles February and differing month lengths cleanly."""
        from financial_engine import _add_months
        jan31 = datetime(2024, 1, 31)  # 2024 is leap year
        feb_date = _add_months(jan31, 1, 31)
        self.assertEqual(feb_date.strftime("%Y-%m-%d"), "2024-02-29")
        apr_date = _add_months(jan31, 3, 31)
        self.assertEqual(apr_date.strftime("%Y-%m-%d"), "2024-04-30")

    def test_S_foreign_currency_event(self):
        """Verify foreign currency transactions in timeline are converted to user home currency."""
        # user_78 has taxi fare in USD (image_12, event_7307)
        state_u78 = self.resolver.build_normalized_state("user_78", "request_78")
        ev7307 = next((e for e in state_u78.events if e.event_id == "event_7307"), None)
        self.assertIsNotNone(ev7307)
        self.assertEqual(ev7307.currency, "USD")
        self.assertEqual(ev7307.amount, 33.50)
        # Converted to home currency (EUR)
        self.assertGreater(ev7307.amount_home, 0)

    def test_T_variable_essential_expense_forecast(self):
        """Verify variable essential categories (groceries, utilities, etc.) are projected."""
        timeline = self.builder.build_timeline("user_01", "request_01")
        essential_events = [e for e in timeline.events if e.is_essential]
        self.assertGreater(len(essential_events), 0, "Expected essential expense events in timeline")
        ess_cats = {e.category for e in essential_events}
        self.assertTrue(bool(ess_cats.intersection({"rent", "groceries", "utilities", "education", "debt_repayment"})))

if __name__ == "__main__":
    unittest.main()
