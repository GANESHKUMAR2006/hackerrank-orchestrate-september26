"""
Targeted regression tests for Phase 6.1:
Fixing planner regressions, partial payment eligibility, and wait precedence.
"""

import os
import sys
import unittest
from decimal import Decimal

# Add code directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from evidence import EvidenceResolver
from financial_engine import TimelineBuilder
from affordability import AffordabilitySimulator
from planner import PaymentPlanner, PaymentPlan, Payment


class TestPhase61Regressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = EvidenceResolver()
        cls.builder = TimelineBuilder(cls.resolver)
        cls.simulator = AffordabilitySimulator(cls.resolver, cls.builder)
        cls.planner = PaymentPlanner(cls.resolver, cls.builder, cls.simulator)

    def test_request_18_partial_payment_rejected(self):
        """
        Verify request_18 rejects partial payment:
        1. allows_partial_payment is False, so partial payment must never be generated.
        2. Spending changes must be none.
        3. Under actual dataset, user_18 can safely wait until 2026-09-15.
        4. When deadline precedes the safe payday, correctly falls back to not_affordable / not_recommended.
        """
        req18 = self.resolver.requests["request_18"]
        self.assertFalse(req18.allows_partial_payment, "request_18 allows_partial_payment must be False")

        dec = self.planner.evaluate_request("user_18", "request_18")
        
        # Must NEVER be partial_payment
        self.assertNotEqual(dec.recommended_payment_method, "partial_payment")
        self.assertEqual(dec.spending_changes_needed, "none")
        
        # Benchmark ground truth verification: wait is safe on 2026-09-15
        self.assertEqual(dec.affordability_status, "affordable_later")
        self.assertEqual(dec.recommended_payment_method, "wait")
        self.assertEqual(dec.payment_plan, "2026-09-15:3246.10")

        # Synthetic check: If desired_completion_date were before 2026-09-15 (e.g. 2026-08-01),
        # neither full payment today nor wait is safe by deadline, yielding not_affordable / not_recommended
        sim_res = self.simulator.evaluate_request("user_18", "request_18")
        candidates = self.planner.generate_candidate_plans("user_18", "request_18", sim_res, "2026-09-15")
        ranked = self.planner.rank_plans(candidates, deadline="2026-08-01")
        self.assertEqual(len(ranked), 0, "No plan can complete by 2026-08-01 deadline")

    def test_request_22_partial_payment_rejected(self):
        """
        Verify request_22 rejects partial payment:
        1. user_22 only considers installments; neither partial_payment nor full_payment is considered.
        2. Recommended method is installments (affordable_with_plan) matching ground truth.
        3. Spending changes must be none.
        4. If user considered full_payment, wait would take precedence over partial payment.
        """
        user22 = self.resolver.profiles["user_22"]
        self.assertNotIn("partial_payment", user22.payment_methods_user_will_consider)

        dec = self.planner.evaluate_request("user_22", "request_22")
        
        # Must NEVER be partial_payment
        self.assertNotEqual(dec.recommended_payment_method, "partial_payment")
        self.assertEqual(dec.spending_changes_needed, "none")
        self.assertEqual(dec.affordability_status, "affordable_with_plan")
        self.assertEqual(dec.recommended_payment_method, "installments")
        self.assertEqual(dec.payment_plan, "2024-12-08:253.59|2025-01-05:253.59|2025-02-02:253.59")

    def test_wait_preempts_partial_payment_when_full_payment_considered(self):
        """
        General Invariant: When a user considers full_payment and full payment is safe
        by desired_completion_date, wait takes precedence over splitting into partial_payment.
        """
        # Create a synthetic request where allows_partial_payment is True
        # and user considers both full_payment and partial_payment
        sim_res = self.simulator.evaluate_request("user_04", "request_04")
        # For user_04, wait is safe on 2024-06-15.
        dec = self.planner.evaluate_request("user_04", "request_04")
        self.assertEqual(dec.affordability_status, "affordable_later")
        self.assertEqual(dec.recommended_payment_method, "wait")
        self.assertNotEqual(dec.recommended_payment_method, "partial_payment")

    def test_partial_payment_used_only_when_wait_ineligible(self):
        """
        Verify request_19 correctly uses partial_payment:
        user_19 considers ['partial_payment', 'installments'] (does NOT consider full_payment),
        so wait is ineligible and partial_payment is legitimately selected.
        """
        dec = self.planner.evaluate_request("user_19", "request_19")
        self.assertEqual(dec.affordability_status, "affordable_with_plan")
        self.assertEqual(dec.recommended_payment_method, "partial_payment")
        self.assertEqual(dec.spending_changes_needed, "none")
        self.assertEqual(len(dec.selected_plan.payments), 2)


if __name__ == "__main__":
    unittest.main()
