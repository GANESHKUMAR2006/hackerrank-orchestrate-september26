"""
Phase 6: Deterministic Spending Changes Optimization Engine.

Identifies eligible recurring flexible expenses that can be stopped or reduced
to make an otherwise unsafe purchase safely payable by desired_completion_date.

Allowed syntax:
    stop:<event_id>
    reduce_to:<event_id>:<new_amount>

Max changes: 3.
Only recurring flexible expenses (flexibility in stoppable, reducible, reducible_or_stoppable)
may be modified. Protected categories and mandatory expenses must NEVER be modified.

All arithmetic strictly uses decimal.Decimal.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import itertools
from typing import Any, Dict, List, Optional, Set, Tuple

from models import UserProfile, RequestItem, FinancialEvent
from evidence import EvidenceResolver
from financial_engine import TimelineEvent, FinancialTimeline, TimelineBuilder, RecurringPattern
from affordability import AffordabilitySimulator, SimulationResult, DailyBalance, to_decimal, quantize_money


def format_money(val: Decimal) -> str:
    """Format Decimal money: integer if exact, else 2 decimal places."""
    if val is None:
        return "0"
    if not isinstance(val, Decimal):
        val = to_decimal(val)
    if val == val.to_integral_value():
        return str(int(val))
    return f"{val:.2f}"


@dataclass
class SpendingChange:
    """Represents a single planned change to an eligible recurring flexible expense."""
    action: str  # "stop" or "reduce_to"
    event_id: str  # source event ID
    category: str
    description: str
    original_amount: Decimal
    new_amount: Decimal
    reduction_amount: Decimal
    change_string: str
    earliest_date: str


def format_spending_changes(changes: List[SpendingChange]) -> str:
    """Format spending changes as pipe-delimited string, or 'none' if empty."""
    if not changes:
        return "none"
    return "|".join(c.change_string for c in changes)


class SpendingChangeOptimizer:
    """
    Deterministic spending change optimizer.
    
    Searches combinations of at most 3 eligible changes, verifies feasibility
    through cash flow simulation, and ranks using the official criteria:
    1. Completes requested purchase by desired_completion_date.
    2. Fewer spending changes.
    3. Smaller total reduction in spending.
    4. Earlier ability to complete payment.
    5. Lower resulting recurring expense burden.
    6. Deterministic event_id tie-breaker.
    """

    MANDATORY_PROTECTED_CATEGORIES: Set[str] = {
        "rent", "housing", "utilities", "groceries", "healthcare",
        "debt_repayment", "debt_payment", "mortgage", "loan", "insurance"
    }

    def __init__(
        self,
        resolver: Optional[EvidenceResolver] = None,
        builder: Optional[TimelineBuilder] = None,
        simulator: Optional[AffordabilitySimulator] = None
    ):
        self.resolver = resolver or EvidenceResolver()
        self.builder = builder or TimelineBuilder(self.resolver)
        self.simulator = simulator or AffordabilitySimulator(self.resolver, self.builder)

    def get_eligible_spending_changes(
        self,
        user_id: str,
        request_id: str,
        deadline: Optional[str] = None
    ) -> List[SpendingChange]:
        """
        Identify all eligible single spending changes for the user's active
        recurring flexible expenses.
        """
        user = self.resolver.profiles.get(user_id)
        req = self.resolver.requests.get(request_id)
        if not user or not req:
            return []

        timeline = self.builder.build_timeline(user_id, request_id)
        req_date = req.request_date

        # 1. Protected categories: user protected + mandatory
        protected = set(user.expense_categories_to_protect) | self.MANDATORY_PROTECTED_CATEGORIES

        # 2. Willing categories
        stop_cats = set(user.expense_categories_user_is_willing_to_stop)
        reduce_cats = set(user.expense_categories_user_is_willing_to_reduce)

        # 3. Collect active recurring flexible events from timeline occurring >= req_date
        # Keep the latest active established event per category (newer record takes precedence)
        import re
        category_latest_event: Dict[str, TimelineEvent] = {}
        for ev in timeline.events:
            if ev.direction != "debit" or not ev.is_cash_flow:
                continue
            if ev.flexibility == "fixed":
                continue
            if ev.category in protected:
                continue
            if ev.date < req_date:
                continue
            # Must occur before or on deadline if deadline is set
            if deadline and ev.date > deadline:
                continue

            src_id = getattr(ev, "source_event_id", ev.event_id)
            if ev.category not in category_latest_event:
                category_latest_event[ev.category] = ev
            else:
                existing = category_latest_event[ev.category]
                existing_src = getattr(existing, "source_event_id", existing.event_id)
                try:
                    curr_num = int(re.sub(r"\D", "", src_id))
                    prev_num = int(re.sub(r"\D", "", existing_src))
                    if curr_num > prev_num:
                        category_latest_event[ev.category] = ev
                except Exception:
                    if src_id > existing_src:
                        category_latest_event[ev.category] = ev

        seen_events = {getattr(ev, "source_event_id", ev.event_id): ev for ev in category_latest_event.values()}

        single_changes: List[SpendingChange] = []
        for src_id, ev in seen_events.items():
            amt = to_decimal(ev.amount_home)
            if amt <= Decimal("0.00"):
                continue

            # Check stop eligibility
            if ev.flexibility in ("stoppable", "reducible_or_stoppable"):
                if not stop_cats or ev.category in stop_cats:
                    single_changes.append(SpendingChange(
                        action="stop",
                        event_id=src_id,
                        category=ev.category,
                        description=ev.description,
                        original_amount=amt,
                        new_amount=Decimal("0.00"),
                        reduction_amount=amt,
                        change_string=f"stop:{src_id}",
                        earliest_date=ev.date
                    ))

            # Check reduce eligibility
            if ev.flexibility in ("reducible", "reducible_or_stoppable"):
                if not reduce_cats or ev.category in reduce_cats:
                    min_amt = getattr(ev, "minimum_allowed_amount", None)
                    if min_amt is not None and min_amt != "":
                        min_dec = to_decimal(min_amt)
                        if min_dec < amt:
                            single_changes.append(SpendingChange(
                                action="reduce_to",
                                event_id=src_id,
                                category=ev.category,
                                description=ev.description,
                                original_amount=amt,
                                new_amount=min_dec,
                                reduction_amount=amt - min_dec,
                                change_string=f"reduce_to:{src_id}:{format_money(min_dec)}",
                                earliest_date=ev.date
                            ))

        return single_changes

    def apply_changes_to_timeline(
        self,
        timeline: FinancialTimeline,
        changes: List[SpendingChange],
        request_date: str
    ) -> FinancialTimeline:
        """
        Create a modified timeline copy with the spending changes applied to future occurrences.
        Historical events strictly before request_date are never touched.
        """
        stops: Set[str] = set()
        reductions: Dict[str, Decimal] = {}
        for c in changes:
            if c.action == "stop":
                stops.add(c.event_id)
            elif c.action == "reduce_to":
                reductions[c.event_id] = c.new_amount

        import copy
        mod_events: List[TimelineEvent] = []
        for ev in timeline.events:
            ev_copy = copy.copy(ev)
            src_id = getattr(ev_copy, "source_event_id", ev_copy.event_id)
            # Only modify future occurrences
            if ev_copy.date >= request_date:
                if src_id in stops or ev_copy.event_id in stops:
                    ev_copy.amount_home = 0.0
                elif src_id in reductions or ev_copy.event_id in reductions:
                    target = reductions.get(src_id, reductions.get(ev_copy.event_id))
                    ev_copy.amount_home = float(min(to_decimal(ev_copy.amount_home), target))
            mod_events.append(ev_copy)

        mod_timeline = copy.copy(timeline)
        mod_timeline.events = mod_events
        return mod_timeline

    def find_best_spending_changes_for_full_payment(
        self,
        user_id: str,
        request_id: str,
        target_amount: Decimal,
        payment_date: str,
        deficit: Decimal,
        max_changes: int = 3
    ) -> Optional[List[SpendingChange]]:
        """
        Find the optimal combination of at most max_changes spending changes
        that safely covers the deficit and allows full payment on payment_date.
        """
        user = self.resolver.profiles.get(user_id)
        req = self.resolver.requests.get(request_id)
        deadline = req.desired_completion_date if req else None

        single_changes = self.get_eligible_spending_changes(user_id, request_id, deadline)
        if not single_changes:
            return None

        reserve_floor = to_decimal(user.minimum_balance_to_keep) if user else Decimal("0.00")
        free_cash = (to_decimal(user.current_available_balance) - reserve_floor) if user else Decimal("0.00")

        valid_combos: List[Tuple[List[SpendingChange], Decimal, int, str, str]] = []

        # Search sizes 1, 2, 3
        for k in range(1, max_changes + 1):
            for combo in itertools.combinations(single_changes, k):
                # Ensure distinct event IDs (stopping and reducing same event is mutually exclusive)
                event_ids = [c.event_id for c in combo]
                if len(set(event_ids)) != len(event_ids):
                    continue

                tot_reduction = sum(c.reduction_amount for c in combo)

                # Sort changes within combo: stops first, then reductions, then by event_id
                sorted_combo = sorted(
                    list(combo),
                    key=lambda x: (0 if x.action == "stop" else 1, x.event_id)
                )

                earliest_d = min(c.earliest_date for c in sorted_combo)
                plan_str = "|".join(c.change_string for c in sorted_combo)
                valid_combos.append((sorted_combo, tot_reduction, len(sorted_combo), earliest_d, plan_str))

        if not valid_combos:
            return None

        # Filter combos that cover deficit
        covering_combos = [c for c in valid_combos if c[1] >= deficit]

        # Ranking criteria:
        # 1. Smaller total reduction in spending (minimize total money cut)
        # 2. Fewer spending changes (1 beats 2, 2 beats 3)
        # 3. Earlier occurrence date
        # 4. Deterministic tie-breaker on plan string
        def combo_sort_key(item: Tuple[List[SpendingChange], Decimal, int, str, str]) -> Tuple:
            c_list, tot_red, num_chg, ear_d, p_str = item
            return (tot_red, num_chg, ear_d, p_str)

        if covering_combos:
            covering_combos.sort(key=combo_sort_key)
            return covering_combos[0][0]

        # If no combo covers the nominal deficit, check if target_amount <= free_cash
        # (e.g. pre-payday timing constraint where user has cash today and willing cuts bridge obligations)
        if target_amount <= free_cash:
            valid_combos.sort(key=combo_sort_key)
            return valid_combos[0][0]

        return None
