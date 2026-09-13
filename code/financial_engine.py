"""
Financial Engine - Recurrence Detection and 90-Day Timeline Preparation Module.
"""

import calendar
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from models import (
    UserProfile,
    RequestItem,
    FinancialEvent,
    FinancialEvidence,
    NormalizedFinancialState
)
from evidence import EvidenceResolver

@dataclass
class TimelineEvent:
    date: str                          # YYYY-MM-DD
    event_id: str                      # Unique identifier in timeline
    source_event_id: str               # Original event_id in financial_events.csv
    user_id: str
    event_type: str                    # income, expense, subscription, debt_payment, etc.
    category: str
    description: str
    amount_home: float
    direction: str                     # credit, debit, non_cash
    status: str                        # settled, pending, scheduled, inferred_recurring
    is_cash_flow: bool
    is_recurring: bool
    recurrence_freq: str               # monthly, weekly, biweekly, quarterly, one_time
    flexibility: str                   # fixed, reducible, stoppable, reducible_or_stoppable
    minimum_allowed_amount: Optional[float] = None
    is_essential: bool = False
    source: str = "explicit"
    original_currency: str = ""
    original_amount: float = 0.0

@dataclass
class RecurringPattern:
    pattern_id: str
    user_id: str
    category: str
    description: str
    event_type: str
    direction: str
    frequency: str                     # monthly, weekly, biweekly, quarterly
    interval_days: float
    day_of_month: Optional[int] = None
    day_of_week: Optional[int] = None
    amount_home: float = 0.0
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None
    last_historical_date: str = ""
    source_event_id: str = ""
    is_essential: bool = False

@dataclass
class FinancialTimeline:
    user_id: str
    request_id: str
    request_date: str
    timeline_start: str                # request_date
    timeline_end: str                  # request_date + 90 days (inclusive)
    starting_balance: float
    minimum_balance_to_keep: float
    home_currency: str
    events: List[TimelineEvent] = field(default_factory=list)
    detected_patterns: List[RecurringPattern] = field(default_factory=list)
    explicit_future_events: List[TimelineEvent] = field(default_factory=list)
    inferred_future_events: List[TimelineEvent] = field(default_factory=list)
    active_pending_debits: List[TimelineEvent] = field(default_factory=list)
    confirmed_future_income: List[TimelineEvent] = field(default_factory=list)

def _clamp_day(year: int, month: int, day: int) -> int:
    """Clamp day of month to maximum valid day for the given month/year."""
    max_days = calendar.monthrange(year, month)[1]
    return min(day, max_days)

def _add_months(dt: datetime, months: int, target_day: int) -> datetime:
    """Add N months preserving the target day of month, clamped to valid month days."""
    new_month = dt.month + months
    new_year = dt.year + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1
    valid_day = _clamp_day(new_year, new_month, target_day)
    return datetime(new_year, new_month, valid_day)

class TimelineBuilder:
    def __init__(self, resolver: Optional[EvidenceResolver] = None):
        self.resolver = resolver or EvidenceResolver()

    def detect_recurring_patterns(
        self,
        user: UserProfile,
        events: List[FinancialEvent],
        request_date_str: str,
        message_evidence: List[FinancialEvidence]
    ) -> List[RecurringPattern]:
        """
        Detect recurring patterns from historical settled events before request_date.
        """
        req_dt = datetime.strptime(request_date_str, "%Y-%m-%d")
        
        # Check user message facts (employment ended, salary amended, rent increase)
        emp_ended = any(e.evidence_type == "employment_ended" for e in message_evidence)
        salary_amended = next(
            (e.new_value for e in reversed(message_evidence) if e.evidence_type == "salary_amount_change"),
            None
        )
        rent_multiplier = next(
            (e.new_value for e in reversed(message_evidence) if e.evidence_type == "rent_increase"),
            1.0
        )

        # Filter settled historical events strictly before request_date
        historical = [
            e for e in events
            if e.status == "settled" and datetime.strptime(e.settlement_date, "%Y-%m-%d") < req_dt
        ]

        # Group historical events by (category, description)
        groups = defaultdict(list)
        for e in historical:
            groups[(e.category, e.description)].append(e)

        patterns: List[RecurringPattern] = []
        pattern_idx = 1

        for (cat, desc), ev_list in groups.items():
            if not ev_list:
                continue

            sorted_evs = sorted(ev_list, key=lambda x: x.settlement_date)
            latest_ev = sorted_evs[-1]
            first_ev = sorted_evs[0]

            # Do not project variable unconfirmed credits into recurring future income per problem statement
            if latest_ev.direction == "credit":
                desc_lower = (latest_ev.description or "").lower()
                if any(w in desc_lower for w in ["commission", "bonus", "refund", "lottery", "gain", "overtime"]):
                    continue

            # Inherent recurring categories / event types
            is_inherent_monthly = (
                latest_ev.event_type in ["subscription", "debt_payment"]
                or cat in ["rent", "utilities", "salary", "insurance", "cloud_storage",
                           "music_subscription", "delivery_membership", "gym", "family_support",
                           "education", "housing"]
            )

            # Do not classify a one-off purchase/dining/shopping as recurring if only 1 occurrence
            if len(sorted_evs) < 2 and not is_inherent_monthly:
                continue

            # Calculate intervals if multiple occurrences exist
            dates = [datetime.strptime(e.settlement_date, "%Y-%m-%d") for e in sorted_evs]
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)] if len(dates) >= 2 else []
            avg_interval = sum(diffs) / len(diffs) if diffs else 30.0

            # Determine frequency
            if is_inherent_monthly or (25 <= avg_interval <= 35):
                freq = "monthly"
                day_of_month = dates[-1].day
                day_of_week = None
            elif 5 <= avg_interval <= 10:
                freq = "weekly"
                day_of_month = None
                day_of_week = dates[-1].weekday()
            elif 11 <= avg_interval <= 18:
                freq = "biweekly"
                day_of_month = None
                day_of_week = dates[-1].weekday()
            elif 75 <= avg_interval <= 105:
                freq = "quarterly"
                day_of_month = dates[-1].day
                day_of_week = None
            else:
                # Default to monthly if inherently recurring or >= 2 occurrences
                freq = "monthly"
                day_of_month = dates[-1].day
                day_of_week = None

            # Determine representative amount (median of historical)
            amounts = sorted([e.amount_home for e in sorted_evs])
            n = len(amounts)
            if n % 2 == 1:
                median_amt = amounts[n // 2]
            else:
                median_amt = round((amounts[n // 2 - 1] + amounts[n // 2]) / 2.0, 2)

            # Apply message adjustments to salary or rent
            if cat == "salary":
                if emp_ended or "final" in latest_ev.description.lower():
                    continue  # Do not project future recurring salary if contract ended or final payroll received
                if salary_amended is not None:
                    median_amt = salary_amended
                else:
                    # Check if there is an upcoming scheduled regular salary that overrides historical prorated salary
                    sched_sal = next((e for e in events if e.category == "salary" and e.status == "scheduled"), None)
                    if sched_sal is not None:
                        median_amt = sched_sal.amount_home
            elif cat == "rent" and rent_multiplier != 1.0:
                median_amt = round(median_amt * rent_multiplier, 2)

            # Essential flag
            is_essential = (
                cat in user.expense_categories_to_protect
                or cat in ["rent", "utilities", "groceries", "healthcare", "debt_repayment"]
            )

            patterns.append(RecurringPattern(
                pattern_id=f"pat_{pattern_idx:03d}",
                user_id=user.user_id,
                category=cat,
                description=desc,
                event_type=latest_ev.event_type,
                direction=latest_ev.direction,
                frequency=freq,
                interval_days=avg_interval,
                day_of_month=day_of_month,
                day_of_week=day_of_week,
                amount_home=median_amt,
                flexibility=latest_ev.flexibility,
                minimum_allowed_amount=latest_ev.minimum_allowed_amount,
                last_historical_date=latest_ev.settlement_date,
                source_event_id=latest_ev.event_id,
                is_essential=is_essential
            ))
            pattern_idx += 1

        return patterns

    def build_timeline(
        self,
        user_id: str,
        request_id: Optional[str] = None
    ) -> FinancialTimeline:
        """
        Build the deterministic 90-day financial timeline for the user/request.
        Timeline horizon: [request_date, request_date + 90 days] (inclusive).
        """
        state = self.resolver.build_normalized_state(user_id, request_id)
        user = state.user
        request = state.request
        req_date_str = request.request_date if request else "2024-01-01"
        req_dt = datetime.strptime(req_date_str, "%Y-%m-%d")
        end_dt = req_dt + timedelta(days=90)
        end_date_str = end_dt.strftime("%Y-%m-%d")

        # 1. Detect recurring patterns from historical events
        patterns = self.detect_recurring_patterns(user, state.events, req_date_str, state.evidence_applied)

        # 2. Collect explicit future events (settlement_date >= req_date)
        explicit_events: List[TimelineEvent] = []
        explicit_keys: Set[Tuple[str, str, str]] = set()  # (category, description, date)

        for e in state.events:
            if not e.is_cash_flow:
                continue
            e_settle_dt = datetime.strptime(e.settlement_date, "%Y-%m-%d")
            # Must fall within the 90-day horizon or be an active pending debit from prior to request_date
            if req_dt <= e_settle_dt <= end_dt:
                eff_date = e.settlement_date
            elif e.status == "pending" and e.direction == "debit" and e_settle_dt < req_dt:
                # Pending debit originating before request date remains active on request date
                eff_date = req_date_str
            else:
                continue

            is_ess = (
                e.category in user.expense_categories_to_protect
                or e.category in ["rent", "utilities", "groceries", "healthcare", "debt_repayment"]
            )
            te = TimelineEvent(
                date=eff_date,
                event_id=e.event_id,
                source_event_id=e.event_id,
                user_id=user.user_id,
                event_type=e.event_type,
                category=e.category,
                description=e.description,
                amount_home=e.amount_home,
                direction=e.direction,
                status=e.status,
                is_cash_flow=e.is_cash_flow,
                is_recurring=e.is_recurring,
                recurrence_freq="one_time" if not e.is_recurring else "monthly",
                flexibility=e.flexibility,
                minimum_allowed_amount=e.minimum_allowed_amount,
                is_essential=is_ess,
                source=e.source,
                original_currency=e.currency,
                original_amount=e.amount
            )
            explicit_events.append(te)
            explicit_keys.add((e.category, e.description, eff_date))
            # Also track salary by category/date
            if e.category == "salary":
                explicit_keys.add(("salary", "*", eff_date))

        # 3. Generate future occurrences for recurring patterns (deduplicated against explicit events)
        inferred_events: List[TimelineEvent] = []
        gen_counter = 1

        for pat in patterns:
            # Generate occurrences within [req_dt, end_dt]
            if pat.frequency == "monthly" and pat.day_of_month is not None:
                # Start generating from the month of request_date up to 4 months forward
                for m_offset in range(0, 5):
                    # Base on request_dt's year/month
                    occ_dt = _add_months(datetime(req_dt.year, req_dt.month, 1), m_offset, pat.day_of_month)
                    if req_dt <= occ_dt <= end_dt:
                        occ_date_str = occ_dt.strftime("%Y-%m-%d")
                        
                        # Deduplication check: does an explicit future event already exist on or within 3 days?
                        is_dup = False
                        for delta in range(-3, 4):
                            near_date = (occ_dt + timedelta(days=delta)).strftime("%Y-%m-%d")
                            if (pat.category, pat.description, near_date) in explicit_keys:
                                is_dup = True
                                break
                            if pat.category == "salary" and ("salary", "*", near_date) in explicit_keys:
                                is_dup = True
                                break
                        if is_dup:
                            continue

                        inferred_events.append(TimelineEvent(
                            date=occ_date_str,
                            event_id=f"inferred_{pat.source_event_id}_{occ_date_str}",
                            source_event_id=pat.source_event_id,
                            user_id=user.user_id,
                            event_type=pat.event_type,
                            category=pat.category,
                            description=pat.description,
                            amount_home=pat.amount_home,
                            direction=pat.direction,
                            status="inferred_recurring",
                            is_cash_flow=True,
                            is_recurring=True,
                            recurrence_freq="monthly",
                            flexibility=pat.flexibility,
                            minimum_allowed_amount=pat.minimum_allowed_amount,
                            is_essential=pat.is_essential,
                            source=f"inferred_from:{pat.source_event_id}",
                            original_currency=user.home_currency,
                            original_amount=pat.amount_home
                        ))
                        gen_counter += 1

            elif pat.frequency == "weekly":
                # Step by 7 days from last_historical_date
                last_dt = datetime.strptime(pat.last_historical_date, "%Y-%m-%d")
                curr_dt = last_dt + timedelta(days=7)
                while curr_dt <= end_dt:
                    if curr_dt >= req_dt:
                        occ_date_str = curr_dt.strftime("%Y-%m-%d")
                        # Check duplicate
                        if (pat.category, pat.description, occ_date_str) not in explicit_keys:
                            inferred_events.append(TimelineEvent(
                                date=occ_date_str,
                                event_id=f"inferred_{pat.source_event_id}_{occ_date_str}",
                                source_event_id=pat.source_event_id,
                                user_id=user.user_id,
                                event_type=pat.event_type,
                                category=pat.category,
                                description=pat.description,
                                amount_home=pat.amount_home,
                                direction=pat.direction,
                                status="inferred_recurring",
                                is_cash_flow=True,
                                is_recurring=True,
                                recurrence_freq="weekly",
                                flexibility=pat.flexibility,
                                minimum_allowed_amount=pat.minimum_allowed_amount,
                                is_essential=pat.is_essential,
                                source=f"inferred_from:{pat.source_event_id}",
                                original_currency=user.home_currency,
                                original_amount=pat.amount_home
                            ))
                    curr_dt += timedelta(days=7)

            elif pat.frequency == "biweekly":
                last_dt = datetime.strptime(pat.last_historical_date, "%Y-%m-%d")
                curr_dt = last_dt + timedelta(days=14)
                while curr_dt <= end_dt:
                    if curr_dt >= req_dt:
                        occ_date_str = curr_dt.strftime("%Y-%m-%d")
                        if (pat.category, pat.description, occ_date_str) not in explicit_keys:
                            inferred_events.append(TimelineEvent(
                                date=occ_date_str,
                                event_id=f"inferred_{pat.source_event_id}_{occ_date_str}",
                                source_event_id=pat.source_event_id,
                                user_id=user.user_id,
                                event_type=pat.event_type,
                                category=pat.category,
                                description=pat.description,
                                amount_home=pat.amount_home,
                                direction=pat.direction,
                                status="inferred_recurring",
                                is_cash_flow=True,
                                is_recurring=True,
                                recurrence_freq="biweekly",
                                flexibility=pat.flexibility,
                                minimum_allowed_amount=pat.minimum_allowed_amount,
                                is_essential=pat.is_essential,
                                source=f"inferred_from:{pat.source_event_id}",
                                original_currency=user.home_currency,
                                original_amount=pat.amount_home
                            ))
                    curr_dt += timedelta(days=14)

        # 4. Merge all future timeline events and sort chronologically
        all_future = explicit_events + inferred_events
        all_future.sort(key=lambda x: (x.date, 0 if x.direction == "credit" else 1, x.event_id))

        # 5. Extract categorized subsets
        active_pending_debits = [
            e for e in explicit_events
            if e.status == "pending" and e.direction == "debit"
        ]
        confirmed_future_income = [
            e for e in all_future
            if e.direction == "credit" and e.category == "salary" and e.is_cash_flow
        ]

        return FinancialTimeline(
            user_id=user.user_id,
            request_id=request.request_id if request else f"request_{user.user_id.replace('user_', '')}",
            request_date=req_date_str,
            timeline_start=req_date_str,
            timeline_end=end_date_str,
            starting_balance=user.current_available_balance,
            minimum_balance_to_keep=user.minimum_balance_to_keep,
            home_currency=user.home_currency,
            events=all_future,
            detected_patterns=patterns,
            explicit_future_events=explicit_events,
            inferred_future_events=inferred_events,
            active_pending_debits=active_pending_debits,
            confirmed_future_income=confirmed_future_income
        )
