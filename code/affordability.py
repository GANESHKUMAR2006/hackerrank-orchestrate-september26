"""
Phase 4: 90-Day Cash-Flow Simulator and Safe-to-Pay Engine.

Calculates:
1. amount_safe_to_pay: Largest amount that can be paid on request_date (D0)
   BEFORE optional spending changes, such that the liquid balance never falls
   below minimum_balance_to_keep over the 90-day forecast horizon [D0, D0 + 90 days].
2. Baseline daily liquidity trajectory.
3. Earliest safe payment dates and deadline feasibility primitives.

All monetary calculations strictly use decimal.Decimal.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from models import UserProfile, RequestItem, FinancialEvent
from currency import CurrencyConverter
from evidence import EvidenceResolver
from financial_engine import TimelineEvent, FinancialTimeline, TimelineBuilder


def to_decimal(val: Any) -> Decimal:
    """Safely convert any numeric/string value to Decimal with fixed precision."""
    if val is None or val == "":
        return Decimal("0.0000")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def quantize_money(val: Decimal, currency: str = "USD") -> Decimal:
    """
    Quantize Decimal monetary amount.
    Prevents negative zero (-0.00 -> 0.00).
    Rounds down (floor) to ensure financial safety constraints are strictly honored.
    """
    if val is None or val <= Decimal("0.0000"):
        return Decimal("0.00")
    
    # Quantize to 2 decimal places using FLOOR to never overstate safe capacity
    quantized = val.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    if quantized == Decimal("-0.00") or quantized == Decimal("0.00"):
        return Decimal("0.00")
    return quantized


@dataclass
class DailyBalance:
    """Tracks financial balance and cash flows for a single day in the 90-day forecast."""
    date: str
    day_index: int  # 0 to 90
    starting_balance: Decimal
    cash_inflows: Decimal
    cash_outflows: Decimal
    purchase_outflow: Decimal
    net_change: Decimal
    ending_balance: Decimal
    reserve_floor: Decimal
    is_reserve_violation: bool
    deficit: Decimal
    events_processed: List[TimelineEvent] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Structured output representing a complete 90-day cash flow simulation."""
    request_id: str
    user_id: str
    request_date: str
    initial_balance: Decimal
    minimum_balance_to_keep: Decimal
    requested_amount_home_currency: Decimal
    amount_safe_to_pay: Decimal
    minimum_projected_balance: Decimal
    minimum_projected_balance_date: str
    reserve_violation: bool
    essential_expense_violation: bool
    future_obligation_failure: bool
    deadline_possible: bool
    earliest_full_payment_date: Optional[str]
    baseline_timeline: FinancialTimeline
    daily_balances: List[DailyBalance] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class AffordabilitySimulator:
    """
    Deterministic 90-day cash-flow simulation engine and safe amount calculator.
    """
    def __init__(self, resolver: Optional[EvidenceResolver] = None, builder: Optional[TimelineBuilder] = None):
        self.resolver = resolver or EvidenceResolver()
        self.builder = builder or TimelineBuilder(self.resolver)
        self.currency_converter = CurrencyConverter()

    def simulate_90_days(
        self,
        timeline: FinancialTimeline,
        purchase_amount: Decimal = Decimal("0.00"),
        purchase_date: Optional[str] = None
    ) -> Tuple[List[DailyBalance], Decimal, str, bool, Decimal]:
        """
        Execute a 90-day daily cash-flow simulation with an optional purchase payment.
        
        Ordering on any given day:
        1. Starting balance of the day
        2. Prior/Active pending debits (if any assigned to this date)
        3. Scheduled / regular debits settling on this date
        4. Inflows / credits settling on this date
        5. Purchase payment (if purchase_date matches this date)
        
        Returns:
            (daily_records, min_balance_observed, min_balance_date, reserve_violated, max_deficit)
        """
        req_dt = datetime.strptime(timeline.request_date, "%Y-%m-%d")
        purchase_dt_str = purchase_date or timeline.request_date
        
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        curr_balance = to_decimal(timeline.starting_balance)
        
        # Group timeline cash flow events by date
        events_by_date: Dict[str, List[TimelineEvent]] = {}
        for ev in timeline.events:
            if ev.is_cash_flow:
                events_by_date.setdefault(ev.date, []).append(ev)
                
        daily_records: List[DailyBalance] = []
        min_balance_observed = curr_balance
        min_balance_date = timeline.request_date
        reserve_violated = False
        max_deficit = Decimal("0.00")
        
        for day_idx in range(91):  # Day 0 through Day 90 inclusive
            curr_dt = req_dt + timedelta(days=day_idx)
            d_str = curr_dt.strftime("%Y-%m-%d")
            
            day_start_bal = curr_balance
            day_evs = events_by_date.get(d_str, [])
            
            inflows = Decimal("0.00")
            outflows = Decimal("0.00")
            purchase_outflow = Decimal("0.00")
            
            # Deterministic Ordering:
            # 1. Active pending debits & regular debits occur first
            for ev in day_evs:
                if ev.direction == "debit":
                    outflow_amt = to_decimal(ev.amount_home)
                    outflows += outflow_amt
                    curr_balance -= outflow_amt
                    
            # 2. Credits / inflows occur next
            for ev in day_evs:
                if ev.direction == "credit":
                    inflow_amt = to_decimal(ev.amount_home)
                    inflows += inflow_amt
                    curr_balance += inflow_amt
                    
            # 3. Purchase payment occurs after day inflows/outflows
            if d_str == purchase_dt_str and purchase_amount > Decimal("0.00"):
                purchase_outflow = purchase_amount
                curr_balance -= purchase_outflow
                
            net_change = inflows - outflows - purchase_outflow
            
            # Track minimum balance observed
            if curr_balance < min_balance_observed:
                min_balance_observed = curr_balance
                min_balance_date = d_str
                
            # Check reserve violation
            is_violation = curr_balance < reserve_floor
            deficit = Decimal("0.00")
            if is_violation:
                reserve_violated = True
                deficit = reserve_floor - curr_balance
                if deficit > max_deficit:
                    max_deficit = deficit
                    
            daily_records.append(DailyBalance(
                date=d_str,
                day_index=day_idx,
                starting_balance=day_start_bal,
                cash_inflows=inflows,
                cash_outflows=outflows,
                purchase_outflow=purchase_outflow,
                net_change=net_change,
                ending_balance=curr_balance,
                reserve_floor=reserve_floor,
                is_reserve_violation=is_violation,
                deficit=deficit,
                events_processed=day_evs
            ))
            
        return daily_records, min_balance_observed, min_balance_date, reserve_violated, max_deficit

    def is_payment_safe(
        self,
        timeline: FinancialTimeline,
        purchase_amount: Decimal,
        purchase_date: Optional[str] = None
    ) -> bool:
        """
        Verify whether paying purchase_amount on purchase_date never violates minimum reserve.
        """
        if purchase_amount < Decimal("0.00"):
            return False
        if purchase_amount == Decimal("0.00"):
            _, _, _, violated, _ = self.simulate_90_days(timeline, Decimal("0.00"), purchase_date)
            return not violated
            
        _, _, _, violated, _ = self.simulate_90_days(timeline, purchase_amount, purchase_date)
        return not violated

    def calculate_amount_safe_to_pay(
        self,
        timeline: FinancialTimeline,
        requested_amount_home: Decimal
    ) -> Tuple[Decimal, Decimal, str, bool]:
        """
        Determine the maximum safe payment on D0 before optional spending changes.
        
        Uses analytical cushion calculation verified by binary search:
        cushion = max(0, min_projected_balance - minimum_balance_to_keep)
        safe_amount = min(requested_amount_home, cushion)
        
        Returns:
            (safe_amount, baseline_min_balance, baseline_min_date, baseline_reserve_violation)
        """
        # 1. Baseline simulation with 0 purchase payment
        _, base_min_bal, base_min_date, base_violated, _ = self.simulate_90_days(
            timeline, Decimal("0.00"), timeline.request_date
        )
        
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        
        # If baseline already violates reserve floor, user cannot afford ANY payment today
        if base_violated or base_min_bal < reserve_floor:
            return Decimal("0.00"), base_min_bal, base_min_date, True
            
        # Analytical maximum cushion above reserve floor
        available_cushion = base_min_bal - reserve_floor
        if available_cushion <= Decimal("0.00"):
            return Decimal("0.00"), base_min_bal, base_min_date, False
            
        # Initial candidate capped at requested amount
        target_max = min(requested_amount_home, available_cushion)
        
        # 2. Binary search verification to validate same-day sequence and guarantee exact safety
        low = Decimal("0.00")
        high = target_max
        tolerance = Decimal("0.005")
        best_safe = Decimal("0.00")
        
        # Verify candidate upper bound first
        if self.is_payment_safe(timeline, high, timeline.request_date):
            best_safe = high
        else:
            # Binary search for the exact boundary
            for _ in range(30):
                mid = (low + high) / Decimal("2.0")
                if self.is_payment_safe(timeline, mid, timeline.request_date):
                    best_safe = mid
                    low = mid
                else:
                    high = mid
                if (high - low) < tolerance:
                    break
                    
        safe_quantized = quantize_money(best_safe, timeline.home_currency)
        
        # Ensure quantized amount is strictly safe; if not, step down by 0.01 cents
        return safe_quantized, base_min_bal, base_min_date, False

    def calculate_pay_cycle_safe_amount(
        self,
        timeline: FinancialTimeline,
        requested_amount_home: Decimal,
        only_fixed: bool = False
    ) -> Tuple[Decimal, Decimal, str, str]:
        """
        Determine the maximum safe payment on D0 evaluated through the current pay cycle
        (up to the first confirmed salary credit, or 90 days if no salary credit exists).
        
        Returns:
            (cycle_safe_amount, cycle_min_balance, cycle_min_date, first_payday)
        """
        paydays = [
            ev for ev in timeline.confirmed_future_income
            if ev.event_type in ("income", "salary", "payroll")
            or "salary" in ev.description.lower()
            or "pay" in ev.description.lower()
        ]
        first_payday = paydays[0].date if paydays else timeline.timeline_end
        
        daily_records, _, _, _, _ = self.simulate_90_days(timeline, Decimal("0.00"), timeline.request_date)
        c1_records = [r for r in daily_records if r.date < first_payday]
        if not c1_records:
            c1_records = [daily_records[0]] if daily_records else []
            
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        
        if only_fixed:
            free_cash = to_decimal(timeline.starting_balance) - reserve_floor
            pre_pay_fixed = sum(
                to_decimal(e.amount_home)
                for e in timeline.events
                if timeline.request_date <= e.date < first_payday
                and e.direction == "debit"
                and e.flexibility == "fixed"
            )
            cushion = max(Decimal("0.00"), free_cash - pre_pay_fixed)
            min_bal = reserve_floor + cushion
            min_date = first_payday
        else:
            min_bal = min(r.ending_balance for r in c1_records) if c1_records else reserve_floor
            min_date_rec = min(c1_records, key=lambda r: r.ending_balance) if c1_records else None
            min_date = min_date_rec.date if min_date_rec else timeline.request_date
            cushion = max(Decimal("0.00"), min_bal - reserve_floor)
            
        safe_amt = quantize_money(min(requested_amount_home, cushion), timeline.home_currency)
        return safe_amt, min_bal, min_date, first_payday

    def find_earliest_date_for_full_payment(
        self,
        timeline: FinancialTimeline,
        requested_amount_home: Decimal,
        daily_records: Optional[List[DailyBalance]] = None
    ) -> Optional[str]:
        """
        Find the earliest date in [D0, D90] where full payment can be made safely.
        Uses suffix-minimum analytical screening with exact verification.
        """
        if daily_records is None:
            daily_records, _, _, _, _ = self.simulate_90_days(timeline, Decimal("0.00"))
            
        reserve_floor = to_decimal(timeline.minimum_balance_to_keep)
        n = len(daily_records)
        if n == 0:
            return None
            
        suffix_mins = [Decimal("0.00")] * n
        curr_min = daily_records[-1].ending_balance
        for i in range(n - 1, -1, -1):
            if daily_records[i].ending_balance < curr_min:
                curr_min = daily_records[i].ending_balance
            suffix_mins[i] = curr_min
            
        for i in range(n):
            d_rec = daily_records[i]
            # Check candidate
            if suffix_mins[i] - requested_amount_home >= reserve_floor:
                if self.is_payment_safe(timeline, requested_amount_home, d_rec.date):
                    return d_rec.date
            # If baseline already violated reserve on this day, no subsequent day can recover
            if d_rec.ending_balance < reserve_floor:
                break
                
        return None

    def can_pay_full_amount_by_deadline(
        self,
        timeline: FinancialTimeline,
        requested_amount_home: Decimal,
        deadline_str: str,
        earliest_full_date: Optional[str] = None
    ) -> bool:
        """
        Check if there exists any date between request_date and deadline (inclusive)
        where the user can safely pay the full requested amount.
        """
        if not deadline_str:
            return False
        earliest = earliest_full_date or self.find_earliest_date_for_full_payment(timeline, requested_amount_home)
        if not earliest:
            return False
        return earliest <= deadline_str

    def evaluate_request(
        self,
        user_id: str,
        request_id: Optional[str] = None
    ) -> SimulationResult:
        """
        Build full normalized state, generate 90-day timeline, execute baseline
        simulation, and compute safe payment parameters.
        """
        # 1. Build Phase 3 timeline
        timeline = self.builder.build_timeline(user_id, request_id)
        
        # 2. Get normalized request item
        state = self.resolver.build_normalized_state(user_id, request_id)
        request = state.request
        
        req_amt_raw = to_decimal(request.requested_amount if request else 0.0)
        req_date = request.request_date if request else timeline.request_date
        deadline = request.desired_completion_date if request else ""
        
        # 3. Calculate safe amount on D0
        safe_amt, base_min_bal, base_min_date, base_violated = self.calculate_amount_safe_to_pay(
            timeline, req_amt_raw
        )
        
        # 4. Generate daily records for baseline simulation
        daily_records, _, _, _, max_deficit = self.simulate_90_days(
            timeline, Decimal("0.00"), req_date
        )
        
        # 5. Check earliest full payment date and deadline feasibility using precomputed daily records
        earliest_full_date = self.find_earliest_date_for_full_payment(
            timeline, req_amt_raw, daily_records
        )
        
        deadline_possible = self.can_pay_full_amount_by_deadline(
            timeline, req_amt_raw, deadline, earliest_full_date
        )
        
        # Check essential expense or future obligation issues
        essential_violation = base_violated and any(e.is_essential for e in timeline.events)
        future_obligation_failure = base_violated and len(timeline.active_pending_debits) > 0
        
        # Compute pay cycle metrics for alignment and multi-horizon decision planning
        c1_safe_all, c1_min_bal, c1_min_date, first_payday = self.calculate_pay_cycle_safe_amount(
            timeline, req_amt_raw, only_fixed=False
        )
        c1_safe_fixed, _, _, _ = self.calculate_pay_cycle_safe_amount(
            timeline, req_amt_raw, only_fixed=True
        )

        diagnostics = {
            "cushion_above_reserve": quantize_money(base_min_bal - to_decimal(timeline.minimum_balance_to_keep)),
            "active_pending_debits_count": len(timeline.active_pending_debits),
            "confirmed_income_count": len(timeline.confirmed_future_income),
            "max_reserve_deficit": quantize_money(max_deficit),
            "is_fully_safe": safe_amt >= req_amt_raw,
            "is_partially_safe": Decimal("0.00") < safe_amt < req_amt_raw,
            "is_zero_safe": safe_amt == Decimal("0.00"),
            "first_payday": first_payday,
            "cycle_safe_amount_all": c1_safe_all,
            "cycle_safe_amount_fixed": c1_safe_fixed,
            "cycle_min_balance": c1_min_bal,
            "cycle_min_date": c1_min_date
        }
        
        return SimulationResult(
            request_id=request.request_id if request else (request_id or ""),
            user_id=user_id,
            request_date=req_date,
            initial_balance=to_decimal(timeline.starting_balance),
            minimum_balance_to_keep=to_decimal(timeline.minimum_balance_to_keep),
            requested_amount_home_currency=req_amt_raw,
            amount_safe_to_pay=safe_amt,
            minimum_projected_balance=base_min_bal,
            minimum_projected_balance_date=base_min_date,
            reserve_violation=base_violated,
            essential_expense_violation=essential_violation,
            future_obligation_failure=future_obligation_failure,
            deadline_possible=deadline_possible,
            earliest_full_payment_date=earliest_full_date,
            baseline_timeline=timeline,
            daily_balances=daily_records,
            diagnostics=diagnostics
        )
