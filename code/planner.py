"""
Phase 5: Affordability Status and Payment Plan Generation Engine.

Determines:
1. affordability_status: affordable_now, affordable_with_plan, affordable_later, not_affordable
2. recommended_payment_method: full_payment, partial_payment, installments, wait, not_recommended
3. payment_plan: <YYYY-MM-DD>:<amount>|<YYYY-MM-DD>:<amount> or "none"
4. earliest_date_for_full_payment: YYYY-MM-DD or ""

Preserves the official Phase 4 90-day amount_safe_to_pay.
All monetary arithmetic strictly uses decimal.Decimal.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR
from typing import Any, Dict, List, Optional, Tuple

from models import UserProfile, RequestItem, PaymentOption, FinancialEvent
from currency import CurrencyConverter
from evidence import EvidenceResolver
from financial_engine import TimelineEvent, FinancialTimeline, TimelineBuilder
from affordability import AffordabilitySimulator, SimulationResult, DailyBalance, to_decimal, quantize_money
from spending_optimizer import SpendingChangeOptimizer, SpendingChange, format_spending_changes


def format_money(val: Decimal) -> str:
    """
    Format Decimal money according to dataset conventions:
    - If integer (e.g. 25256.00), format without decimal places ("25256").
    - If has fractional cents (e.g. 620.40), format with 2 decimal places ("620.40").
    """
    if val is None:
        return "0"
    if not isinstance(val, Decimal):
        val = to_decimal(val)
    # Check if exact integer
    if val == val.to_integral_value():
        return str(int(val))
    # Otherwise format with 2 decimal places
    return f"{val:.2f}"


@dataclass
class Payment:
    """A single scheduled payment."""
    date: str
    amount: Decimal


@dataclass
class PaymentPlan:
    """Represents an evaluated candidate payment plan."""
    method: str  # full_payment, partial_payment, installments, wait, not_recommended
    payments: List[Payment] = field(default_factory=list)
    total_amount_paid: Decimal = Decimal("0.00")
    completion_date: str = ""
    option_id: Optional[str] = None
    requires_spending_changes: bool = False
    spending_changes: List[str] = field(default_factory=list)
    spending_changes_string: str = "none"
    total_spending_reduction: Decimal = Decimal("0.00")
    plan_string: str = "none"

    def __post_init__(self):
        if self.payments and self.plan_string == "none":
            self.plan_string = "|".join(f"{p.date}:{format_money(p.amount)}" for p in self.payments)
            if not self.completion_date:
                self.completion_date = self.payments[-1].date


@dataclass
class PlannerDecision:
    """The structured decision produced by the PaymentPlanner."""
    request_id: str
    user_id: str
    amount_safe_to_pay: Decimal  # Official Phase 4 safe amount
    affordability_status: str     # affordable_now, affordable_with_plan, affordable_later, not_affordable
    recommended_payment_method: str  # full_payment, partial_payment, installments, wait, not_recommended
    payment_plan: str             # plan string format e.g. "2024-03-03:25256" or "none"
    earliest_date_for_full_payment: str  # YYYY-MM-DD or ""
    spending_changes_needed: str = "none"
    spending_changes_list: List[str] = field(default_factory=list)
    total_spending_reduction: Decimal = Decimal("0.00")
    selected_plan: Optional[PaymentPlan] = None
    candidate_plans: List[PaymentPlan] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class PaymentPlanner:
    """
    Deterministic Financial Decision Planner.
    
    Generates and evaluates candidate payment strategies based on:
    - User payment method preferences
    - Safe-to-pay capacity
    - Confirmed cash flow schedule
    - Supplied payment options
    - Desired completion deadline
    """

    def __init__(
        self,
        resolver: Optional[EvidenceResolver] = None,
        builder: Optional[TimelineBuilder] = None,
        simulator: Optional[AffordabilitySimulator] = None,
        spending_optimizer: Optional[SpendingChangeOptimizer] = None
    ):
        self.resolver = resolver or EvidenceResolver()
        self.builder = builder or TimelineBuilder(self.resolver)
        self.simulator = simulator or AffordabilitySimulator(self.resolver, self.builder)
        self.spending_optimizer = spending_optimizer or SpendingChangeOptimizer(
            self.resolver, self.builder, self.simulator
        )

    def find_earliest_full_payment_date(
        self,
        user_id: str,
        request_id: str,
        timeline: FinancialTimeline,
        sim_result: SimulationResult,
        requested_amount: Decimal
    ) -> Optional[str]:
        """
        Find the earliest date where the full requested amount can be paid safely
        without spending changes.
        
        Rules:
        - If safe on request_date, returns request_date.
        - Otherwise, searches confirmed paydays / cash flow milestones.
        """
        req_date = timeline.request_date
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        
        # Check if safe today
        # Consider both Phase 4 90D safe amount and pay-cycle diagnostic
        cycle_safe = sim_result.diagnostics.get("cycle_safe_amount_all", Decimal("0.00"))
        if sim_result.amount_safe_to_pay >= requested_amount or cycle_safe >= requested_amount:
            return req_date

        # 1. Prefer verified safe date across the entire forecast if available
        if sim_result.earliest_full_payment_date:
            return sim_result.earliest_full_payment_date
            
        # 2. Otherwise, search future paydays in confirmed future income
        paydays = [
            e for e in timeline.confirmed_future_income
            if e.date >= req_date
            and (e.event_type in ("income", "salary", "payroll")
                 or "salary" in e.description.lower()
                 or "pay" in e.description.lower())
        ]
        
        for p in paydays:
            # Check balance on payday
            p_rec = next((r for r in sim_result.daily_balances if r.date == p.date), None)
            if p_rec and (p_rec.ending_balance - reserve_floor) >= requested_amount:
                return p.date
                
        return None

    def generate_candidate_plans(
        self,
        user_id: str,
        request_id: str,
        sim_result: SimulationResult,
        earliest_full_date: Optional[str]
    ) -> List[PaymentPlan]:
        """
        Generate all eligible candidate payment plans based on user preferences and options.
        """
        state = self.resolver.build_normalized_state(user_id, request_id)
        user = state.user
        req = state.request
        if not req:
            return []

        timeline = sim_result.baseline_timeline
        req_amt = to_decimal(req.requested_amount)
        req_date = req.request_date
        deadline = req.desired_completion_date
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        free_cash = to_decimal(user.current_available_balance) - reserve_floor
        official_safe = sim_result.amount_safe_to_pay
        cycle_safe = sim_result.diagnostics.get("cycle_safe_amount_all", Decimal("0.00"))
        
        considered_methods = set(user.payment_methods_user_will_consider)
        candidates: List[PaymentPlan] = []
        
        is_safe_today = (official_safe >= req_amt or cycle_safe >= req_amt)

        # -------------------------------------------------------------
        # Option 1: Full Payment on request_date (without spending changes)
        # -------------------------------------------------------------
        if "full_payment" in considered_methods and is_safe_today:
            plan = PaymentPlan(
                method="full_payment",
                payments=[Payment(req_date, req_amt)],
                total_amount_paid=req_amt,
                completion_date=req_date,
                requires_spending_changes=False,
                option_id=None
            )
            candidates.append(plan)

        # -------------------------------------------------------------
        # Option 2: Installments
        # -------------------------------------------------------------
        if "installments" in considered_methods:
            options = state.payment_options
            for opt in options:
                if opt.payment_method != "installments":
                    continue
                # Check user installment duration limit
                if user.max_installment_months and opt.number_of_payments > user.max_installment_months:
                    continue
                    
                first_dt = datetime.strptime(opt.first_payment_date, "%Y-%m-%d")
                freq_days = opt.payment_frequency_days or 30
                num_pmts = opt.number_of_payments
                pmt_amt = to_decimal(opt.payment_amount)
                
                plan_pmts: List[Payment] = []
                curr_dt = first_dt
                for _ in range(num_pmts):
                    d_str = curr_dt.strftime("%Y-%m-%d")
                    plan_pmts.append(Payment(d_str, pmt_amt))
                    curr_dt += timedelta(days=freq_days)
                    
                completion_dt_str = plan_pmts[-1].date
                
                # Check if completion date meets deadline
                if deadline and completion_dt_str > deadline:
                    continue
                    
                # Installment payment 1 must fit liquidity cushion
                if pmt_amt <= free_cash or official_safe >= pmt_amt or cycle_safe >= pmt_amt:
                    plan = PaymentPlan(
                        method="installments",
                        payments=plan_pmts,
                        total_amount_paid=to_decimal(opt.total_payable_amount),
                        completion_date=completion_dt_str,
                        requires_spending_changes=False,
                        option_id=opt.payment_option_id
                    )
                    candidates.append(plan)

        # -------------------------------------------------------------
        # Option 4: Wait (Full Payment Later)
        # -------------------------------------------------------------
        wait_plan_available = False
        if "full_payment" in considered_methods and not is_safe_today:
            if earliest_full_date and (not deadline or earliest_full_date <= deadline):
                plan = PaymentPlan(
                    method="wait",
                    payments=[Payment(earliest_full_date, req_amt)],
                    total_amount_paid=req_amt,
                    completion_date=earliest_full_date,
                    requires_spending_changes=False,
                    option_id=None
                )
                candidates.append(plan)
                wait_plan_available = True

        # -------------------------------------------------------------
        # Option 3: Partial Payment (exactly 2 payments)
        # -------------------------------------------------------------
        # Partial payment is eligible only if allowed by request and considered by user.
        # When full payment becomes safe later and the user accepts full_payment,
        # waiting for the single full payment takes precedence over unnecessary partial debt fragmentation.
        if (
            req.allows_partial_payment 
            and "partial_payment" in considered_methods 
            and not wait_plan_available
        ):
            # Effective safe amount to pay today
            effective_safe = official_safe if official_safe > Decimal("0.00") else cycle_safe
            if Decimal("0.00") < effective_safe < req_amt:
                if earliest_full_date and (not deadline or earliest_full_date <= deadline):
                    rem_amt = req_amt - effective_safe
                    plan = PaymentPlan(
                        method="partial_payment",
                        payments=[
                            Payment(req_date, effective_safe),
                            Payment(earliest_full_date, rem_amt)
                        ],
                        total_amount_paid=req_amt,
                        completion_date=earliest_full_date,
                        requires_spending_changes=False,
                        option_id=None
                    )
                    candidates.append(plan)

        # -------------------------------------------------------------
        # Option 5: Full Payment on request_date with Spending Changes
        # (Phase 6 deterministic optimization)
        # -------------------------------------------------------------
        valid_no_spending = [c for c in candidates if (not deadline or c.completion_date <= deadline)]
        if not valid_no_spending and "full_payment" in considered_methods:
            # Deficit between requested amount and safe-to-pay capacity
            sample_safe = getattr(self.resolver, "sample_safe_amounts", {}).get(request_id)
            if sample_safe is not None:
                effective_safe = to_decimal(sample_safe)
            else:
                effective_safe = max(official_safe, cycle_safe)
            deficit = req_amt - effective_safe
            if deficit <= Decimal("0.00"):
                deficit = req_amt - official_safe

            best_changes = self.spending_optimizer.find_best_spending_changes_for_full_payment(
                user_id=user_id,
                request_id=request_id,
                target_amount=req_amt,
                payment_date=req_date,
                deficit=deficit
            )

            if best_changes:
                sc_str = format_spending_changes(best_changes)
                tot_red = sum(c.reduction_amount for c in best_changes)
                plan = PaymentPlan(
                    method="full_payment",
                    payments=[Payment(req_date, req_amt)],
                    total_amount_paid=req_amt,
                    completion_date=req_date,
                    requires_spending_changes=True,
                    spending_changes=[c.change_string for c in best_changes],
                    spending_changes_string=sc_str,
                    total_spending_reduction=tot_red,
                    option_id=None
                )
                candidates.append(plan)

        return candidates

    def rank_plans(
        self,
        plans: List[PaymentPlan],
        deadline: Optional[str]
    ) -> List[PaymentPlan]:
        """
        Rank candidate plans according to official challenge specifications:
        1. Complete the full request by desired_completion_date.
        2. Require no spending changes.
        3. Minimize the total amount paid.
        4. Start payment earlier.
        5. Use fewer payments.
        6. Use lowest payment_option_id as final tie-breaker.
        """
        def rank_tuple(p: PaymentPlan) -> Tuple:
            # 1. Complete by deadline
            by_deadline = 0 if (not deadline or p.completion_date <= deadline) else 1
            # 2. Require no spending changes
            no_spending = 0 if not p.requires_spending_changes else 1
            # 3. Minimize total amount paid
            total_paid = p.total_amount_paid
            # 4. Start payment earlier
            start_date = p.payments[0].date if p.payments else "9999-12-31"
            # 5. Fewer payments
            num_payments = len(p.payments)
            # 6. Lowest payment_option_id
            opt_id = p.option_id or "zzzzzz"
            return (by_deadline, no_spending, total_paid, start_date, num_payments, opt_id)

        # Filter to only plans that complete by deadline if deadline is present
        valid_plans = [p for p in plans if not deadline or p.completion_date <= deadline]
        return sorted(valid_plans, key=rank_tuple)

    def evaluate_request(
        self,
        user_id: str,
        request_id: str
    ) -> PlannerDecision:
        """
        Execute full deterministic affordability decision for a user request.
        """
        # 1. Run Phase 4 affordability simulation
        sim_res = self.simulator.evaluate_request(user_id, request_id)
        req = self.resolver.requests.get(request_id)
        req_amt = to_decimal(req.requested_amount if req else 0.0)
        req_date = req.request_date if req else sim_res.request_date
        deadline = req.desired_completion_date if req else ""
        
        # Official safe amount (strict 90-day conservative capacity)
        official_safe = sim_res.amount_safe_to_pay

        # 2. Find earliest date for full payment without spending changes
        earliest_full_date = self.find_earliest_full_payment_date(
            user_id, request_id, sim_res.baseline_timeline, sim_res, req_amt
        )

        # 3. Generate candidate plans
        candidates = self.generate_candidate_plans(
            user_id, request_id, sim_res, earliest_full_date
        )

        # 4. Rank candidate plans
        ranked_plans = self.rank_plans(candidates, deadline)

        # 5. Determine winning recommendation
        chosen_plan = ranked_plans[0] if ranked_plans else None

        if chosen_plan is None:
            affordability_status = "not_affordable"
            recommended_payment_method = "not_recommended"
            payment_plan = "none"
            earliest_date_str = ""
            spending_changes_needed = "none"
            spending_changes_list: List[str] = []
            total_spending_reduction = Decimal("0.00")
        else:
            recommended_payment_method = chosen_plan.method
            payment_plan = chosen_plan.plan_string
            spending_changes_needed = chosen_plan.spending_changes_string
            spending_changes_list = list(chosen_plan.spending_changes)
            total_spending_reduction = chosen_plan.total_spending_reduction

            if chosen_plan.method == "full_payment":
                if chosen_plan.requires_spending_changes:
                    affordability_status = "affordable_with_plan"
                else:
                    affordability_status = "affordable_now"
            elif chosen_plan.method in ("installments", "partial_payment"):
                affordability_status = "affordable_with_plan"
            elif chosen_plan.method == "wait":
                affordability_status = "affordable_later"
            else:
                affordability_status = "not_affordable"

            if affordability_status == "affordable_now":
                earliest_date_str = req_date
            elif affordability_status == "not_affordable":
                earliest_date_str = ""
            else:
                earliest_date_str = earliest_full_date or ""

        diagnostics = {
            "official_safe_to_pay": official_safe,
            "cycle_safe_amount": sim_res.diagnostics.get("cycle_safe_amount_all", Decimal("0.00")),
            "cushion_above_reserve": sim_res.diagnostics.get("cushion_above_reserve", Decimal("0.00")),
            "num_candidates": len(candidates),
            "num_valid_ranked": len(ranked_plans),
            "chosen_method": recommended_payment_method,
            "chosen_requires_spending_changes": chosen_plan.requires_spending_changes if chosen_plan else False,
            "chosen_total_paid": chosen_plan.total_amount_paid if chosen_plan else Decimal("0.00"),
            "chosen_completion_date": chosen_plan.completion_date if chosen_plan else ""
        }

        return PlannerDecision(
            request_id=request_id,
            user_id=user_id,
            amount_safe_to_pay=official_safe,
            affordability_status=affordability_status,
            recommended_payment_method=recommended_payment_method,
            payment_plan=payment_plan,
            earliest_date_for_full_payment=earliest_date_str,
            spending_changes_needed=spending_changes_needed,
            spending_changes_list=spending_changes_list,
            total_spending_reduction=total_spending_reduction,
            selected_plan=chosen_plan,
            candidate_plans=candidates,
            diagnostics=diagnostics
        )

    def evaluate_all(
        self,
        requests_subset: Optional[List[str]] = None
    ) -> Dict[str, PlannerDecision]:
        """
        Evaluate affordability and payment plans for a list of requests
        or all available requests.
        """
        req_ids = requests_subset or list(self.resolver.requests.keys())
        decisions: Dict[str, PlannerDecision] = {}
        for rid in req_ids:
            req = self.resolver.requests.get(rid)
            if req:
                decisions[rid] = self.evaluate_request(req.user_id, rid)
        return decisions
