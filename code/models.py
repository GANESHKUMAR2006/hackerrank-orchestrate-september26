"""
Data models for the Buy or Wait financial decision system.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class UserProfile:
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: List[str] = field(default_factory=list)
    expense_categories_to_protect: List[str] = field(default_factory=list)
    expense_categories_user_is_willing_to_reduce: List[str] = field(default_factory=list)
    expense_categories_user_is_willing_to_stop: List[str] = field(default_factory=list)
    payment_methods_user_will_consider: List[str] = field(default_factory=list)
    max_installment_months: Optional[int] = None

@dataclass
class RequestItem:
    request_id: str
    user_id: str
    request_date: str
    request_type: str
    requested_amount: float
    desired_completion_date: str
    allows_partial_payment: bool
    request_text: str

@dataclass
class PaymentOption:
    payment_option_id: str
    request_id: str
    payment_method: str
    payment_amount: float
    number_of_payments: int
    first_payment_date: str
    payment_frequency_days: Optional[int]
    financing_fee: float
    total_payable_amount: float

@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str
    description: str
    category: str
    direction: str
    amount: float
    currency: str
    amount_home: float
    event_date: str
    settlement_date: str
    status: str
    linked_event_id: str = ""
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None
    is_cash_flow: bool = True
    is_recurring: bool = False
    source: str = "financial_events.csv"

@dataclass
class FinancialEvidence:
    evidence_id: str
    user_id: str
    event_id: Optional[str]
    evidence_type: str
    field: str
    old_value: Any
    new_value: Any
    effective_date: Optional[str]
    source: str
    confidence: float

@dataclass
class NormalizedFinancialState:
    user: UserProfile
    request: Optional[RequestItem]
    events: List[FinancialEvent] = field(default_factory=list)
    active_pending_debits: List[FinancialEvent] = field(default_factory=list)
    confirmed_future_income: List[FinancialEvent] = field(default_factory=list)
    recurring_expenses: List[FinancialEvent] = field(default_factory=list)
    evidence_applied: List[FinancialEvidence] = field(default_factory=list)
    payment_options: List[PaymentOption] = field(default_factory=list)
