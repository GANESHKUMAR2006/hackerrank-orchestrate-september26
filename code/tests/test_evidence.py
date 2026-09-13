"""
Unit and diagnostic tests for Phase 2: Financial State Reconstruction.
"""

import os
import sys
import unittest

# Add code directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import UserProfile, RequestItem, FinancialEvent, FinancialEvidence, NormalizedFinancialState
from currency import CurrencyConverter, convert_amount
from evidence import EvidenceResolver, VERIFIED_IMAGE_AMOUNTS

class TestFinancialStateReconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = EvidenceResolver()

    def test_01_profiles_loaded(self):
        """Verify all 275 user profiles load correctly with parsed list fields."""
        profiles = self.resolver.profiles
        self.assertEqual(len(profiles), 275, f"Expected 275 profiles, got {len(profiles)}")
        
        # Test individual profile structure
        u1 = profiles["user_01"]
        self.assertEqual(u1.user_id, "user_01")
        self.assertEqual(u1.home_currency, "ZAR")
        self.assertEqual(u1.current_available_balance, 58481.1)
        self.assertEqual(u1.minimum_balance_to_keep, 18000.0)
        self.assertIsInstance(u1.financial_priorities, list)
        self.assertIn("education", u1.financial_priorities)
        self.assertIsInstance(u1.expense_categories_to_protect, list)
        self.assertIn("rent", u1.expense_categories_to_protect)
        self.assertIsNone(u1.max_installment_months)

        # Test user with installment limits
        u2 = profiles["user_02"]
        self.assertEqual(u2.max_installment_months, 7)
        self.assertIn("installments", u2.payment_methods_user_will_consider)

    def test_02_requests_loaded_and_mapped(self):
        """Verify all 250 evaluation requests and 25 sample requests map 1:1 to users."""
        requests = self.resolver.requests
        self.assertEqual(len(requests), 275, f"Expected 275 total requests, got {len(requests)}")
        
        for rid, req in requests.items():
            expected_uid = "user_" + rid.replace("request_", "")
            self.assertEqual(req.user_id, expected_uid, f"Mismatched user for {rid}")
            self.assertGreater(req.requested_amount, 0)
            self.assertTrue(len(req.request_date) == 10)
            self.assertTrue(len(req.desired_completion_date) == 10)

    def test_03_payment_options_loaded(self):
        """Verify request payment options are loaded and match requests."""
        options = self.resolver.payment_options
        self.assertEqual(len(options), 275, "Expected payment options for 275 requests")
        total_opts = sum(len(opts) for opts in options.values())
        self.assertEqual(total_opts, 790, f"Expected 790 total payment options, got {total_opts}")

    def test_04_image_amounts_resolved(self):
        """Verify all 16 blank-amount events resolve to verified image amounts."""
        self.assertEqual(len(VERIFIED_IMAGE_AMOUNTS), 16, "Expected 16 verified image amounts")
        for eid, exp_amt in VERIFIED_IMAGE_AMOUNTS.items():
            self.assertGreater(exp_amt, 0, f"Image amount for {eid} must be positive")

        # Test user_03 salary event_253 (was blank, extracted from image_01)
        state_u3 = self.resolver.build_normalized_state("user_03", "request_03")
        ev253 = next((e for e in state_u3.events if e.event_id == "event_253"), None)
        self.assertIsNotNone(ev253)
        self.assertEqual(ev253.amount, 4365000.0)
        self.assertIn("image:image_01", ev253.source)

        # Test user_16 rent event_1442 (was blank, extracted from image_02)
        state_u16 = self.resolver.build_normalized_state("user_16", "request_16")
        ev1442 = next((e for e in state_u16.events if e.event_id == "event_1442"), None)
        self.assertIsNotNone(ev1442)
        self.assertEqual(ev1442.amount, 100000.0)
        self.assertIn("image:image_02", ev1442.source)

    def test_05_event_status_rules(self):
        """Verify event status rules: cancelled, failed, unrealized, pending credits excluded from cash."""
        # user_01 has event_100 (cancelled) and event_101 (settled)
        state_u1 = self.resolver.build_normalized_state("user_01", "request_01")
        ev100 = next(e for e in state_u1.events if e.event_id == "event_100")
        self.assertFalse(ev100.is_cash_flow, "Cancelled event must not be cash flow")

        # user_21 has event_1856 (unrealized investment valuation)
        state_u21 = self.resolver.build_normalized_state("user_21", "request_21")
        ev1856 = next(e for e in state_u21.events if e.event_id == "event_1856")
        self.assertFalse(ev1856.is_cash_flow, "Unrealized valuation must not be cash flow")

        # user_20 has event_1785 (pending refund)
        state_u20 = self.resolver.build_normalized_state("user_20", "request_20")
        ev1785 = next(e for e in state_u20.events if e.event_id == "event_1785")
        self.assertFalse(ev1785.is_cash_flow, "Pending refund must not be counted as cash")

        # user_91 has event_8575 (failed debit with bank retry notice)
        state_u91 = self.resolver.build_normalized_state("user_91", "request_91")
        ev8575 = next(e for e in state_u91.events if e.event_id == "event_8575")
        self.assertTrue(ev8575.is_cash_flow, "Failed debit with retry notice must remain active liability")
        self.assertEqual(ev8575.status, "pending")

    def test_06_currency_conversion(self):
        """Verify dated foreign currency conversion works and fails on invalid rates."""
        converter = self.resolver.converter
        # Check an exact known rate
        # 2023-10-15: EUR -> ZAR rate is 20.0
        rate = converter.rates.get(("2023-10-15", "EUR", "ZAR"))
        self.assertEqual(rate, 20.0)
        conv = converter.convert_amount(100.0, "EUR", "ZAR", "2023-10-15")
        self.assertEqual(conv, 2000.0)

        # Same currency returns amount unchanged
        self.assertEqual(converter.convert_amount(500.0, "INR", "INR", "2024-01-01"), 500.0)

        # Missing rate raises ValueError
        with self.assertRaises(ValueError):
            converter.convert_amount(100.0, "JPY", "USD", "2024-01-01")

    def test_07_message_evidence_extraction(self):
        """Verify deterministic extraction of facts from messages."""
        # user_02: salary increase to IDR 42,750,000
        ev_u2 = self.resolver.extract_message_evidence("user_02")
        sal_ev = next((e for e in ev_u2 if e.evidence_type == "salary_amount_change"), None)
        self.assertIsNotNone(sal_ev)
        self.assertEqual(sal_ev.new_value, 42750000.0)

        # user_07: salary date moved to 2024-09-23
        ev_u7 = self.resolver.extract_message_evidence("user_07")
        dt_ev = next((e for e in ev_u7 if e.evidence_type == "salary_date_change"), None)
        self.assertIsNotNone(dt_ev)
        self.assertEqual(dt_ev.new_value, "2024-09-23")

        # user_12: seasonal contract ended
        ev_u12 = self.resolver.extract_message_evidence("user_12")
        emp_ev = next((e for e in ev_u12 if e.evidence_type == "employment_ended"), None)
        self.assertIsNotNone(emp_ev)

        # user_16: rent increase by 12%
        ev_u16 = self.resolver.extract_message_evidence("user_16")
        rent_ev = next((e for e in ev_u16 if e.evidence_type == "rent_increase"), None)
        self.assertIsNotNone(rent_ev)
        self.assertEqual(rent_ev.new_value, 1.12)

        # user_18: internal transfer
        ev_u18 = self.resolver.extract_message_evidence("user_18")
        xfer_ev = next((e for e in ev_u18 if e.evidence_type == "internal_transfer"), None)
        self.assertIsNotNone(xfer_ev)

    def test_08_full_state_construction_for_all_users(self):
        """Verify build_normalized_state executes smoothly without error across all 275 users."""
        for uid in self.resolver.profiles.keys():
            state = self.resolver.build_normalized_state(uid)
            self.assertIsNotNone(state.user)
            self.assertGreater(len(state.events), 0)

if __name__ == "__main__":
    unittest.main()
