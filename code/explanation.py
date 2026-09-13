"""
Phase 7: AI Decision Explanation and Token/Cost Accounting Engine.

Architecture & Strict Boundary:
- The deterministic PlannerDecision is the authoritative source of truth.
- The AI layer acts solely as an explanation generator.
- The AI NEVER calculates or overrides:
  * amount_safe_to_pay
  * affordability_status
  * recommended_payment_method
  * payment_plan
  * earliest_date_for_full_payment
  * spending_changes_needed
- If an LLM is unavailable, fails, or produces invalid output, the deterministic
  fallback explanation generator immediately provides a grounded, accurate explanation.
- Comprehensive token usage and cost accounting is tracked for all evaluations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from models import UserProfile, RequestItem, FinancialEvent
from planner import PlannerDecision, format_money


# Model pricing per 1M tokens (Standard Gemini 1.5 Flash rates)
PRICING_PER_MILLION = {
    "gemini-1.5-flash": {"input": Decimal("0.075"), "output": Decimal("0.30")},
    "gemini-2.5-flash": {"input": Decimal("0.075"), "output": Decimal("0.30")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
    "fallback": {"input": Decimal("0.00"), "output": Decimal("0.00")},
    "deterministic-fallback": {"input": Decimal("0.00"), "output": Decimal("0.00")},
}

FORBIDDEN_WORDS = [
    "python",
    "planner.py",
    "phase 1",
    "phase 2",
    "phase 3",
    "phase 4",
    "phase 5",
    "phase 6",
    "phase 7",
    "benchmark",
    "ground truth",
    "hidden test",
    "antigravity",
    "system prompt",
    "developer instruction",
]


def format_currency_amount(amount: Any, currency: str) -> str:
    """Format an amount with commas and appropriate decimal places for natural explanation."""
    if amount is None:
        return f"{currency} 0"
    if isinstance(amount, (int, float, Decimal)):
        val = float(amount)
        if abs(val - round(val)) < 1e-4:
            val_str = f"{int(round(val)):,}"
        else:
            val_str = f"{val:,.2f}"
    else:
        try:
            val = float(str(amount))
            if abs(val - round(val)) < 1e-4:
                val_str = f"{int(round(val)):,}"
            else:
                val_str = f"{val:,.2f}"
        except Exception:
            val_str = str(amount)
    return f"{currency} {val_str}"


def format_date_natural(date_str: str) -> str:
    """Format YYYY-MM-DD into a natural string like '15 September 2026'."""
    if not date_str or date_str == "none":
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')} {dt.year}"
    except Exception:
        return date_str


@dataclass
class UsageRecord:
    """Detailed record of one explanation generation request."""
    request_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: Decimal
    is_fallback: bool
    status: str = "success"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TokenAccountant:
    """
    Tracks token usage, API calls, and estimated financial costs across all requests.
    Generates compliant markdown reports for evaluation/usage_report.md.
    """

    def __init__(self):
        self.records: List[UsageRecord] = []

    def record(
        self,
        request_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        is_fallback: bool,
        status: str = "success",
    ):
        total_tokens = input_tokens + output_tokens
        pricing = PRICING_PER_MILLION.get(model, PRICING_PER_MILLION.get("gemini-1.5-flash"))
        cost = (
            (Decimal(input_tokens) / Decimal(1_000_000)) * pricing["input"]
            + (Decimal(output_tokens) / Decimal(1_000_000)) * pricing["output"]
        )
        rec = UsageRecord(
            request_id=request_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost.quantize(Decimal("0.000001")),
            is_fallback=is_fallback,
            status=status,
        )
        self.records.append(rec)

    @property
    def total_requests(self) -> int:
        return len(self.records)

    @property
    def total_calls(self) -> int:
        return len([r for r in self.records if not r.is_fallback])

    @property
    def fallback_calls(self) -> int:
        return len([r for r in self.records if r.is_fallback])

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    @property
    def avg_tokens_per_request(self) -> float:
        if not self.records:
            return 0.0
        return self.total_tokens / len(self.records)

    @property
    def total_estimated_cost(self) -> Decimal:
        return sum((r.estimated_cost for r in self.records), Decimal("0.000000"))

    @property
    def avg_cost_per_request(self) -> Decimal:
        if not self.records:
            return Decimal("0.000000")
        return self.total_estimated_cost / Decimal(len(self.records))

    def generate_report_markdown(self) -> str:
        """Generate markdown summary conforming to evaluation/usage_report.md."""
        has_llm = any(r.provider == "gemini" for r in self.records)
        primary_provider = "Google Gemini" if has_llm else "Deterministic Fallback"
        primary_model = "gemini-1.5-flash" if has_llm else "deterministic-rule-engine"
        is_estimated = any(r.is_fallback for r in self.records)
        est_label = " (estimated)" if is_estimated else ""

        lines = [
            "# LLM Usage and Cost Report",
            "",
            "## Summary",
            "",
            f"- **Primary Provider:** {primary_provider}",
            f"- **Primary Model:** {primary_model}",
            f"- **Total Requests Processed:** {self.total_requests}",
            f"- **Successful External LLM API Calls:** {self.total_calls}",
            f"- **Fallback Explanations Used:** {self.fallback_calls}",
            f"- **Total Input Tokens:** {self.total_input_tokens:,}{est_label}",
            f"- **Total Output Tokens:** {self.total_output_tokens:,}{est_label}",
            f"- **Total Tokens:** {self.total_tokens:,}{est_label}",
            f"- **Average Tokens / Request:** {self.avg_tokens_per_request:.1f}{est_label}",
            f"- **Total Estimated Cost:** ${self.total_estimated_cost:.6f} USD",
            f"- **Average Cost / Request:** ${self.avg_cost_per_request:.6f} USD",
            "",
            "## Architectural Boundary Note",
            "",
            "- The deterministic financial engine is solely responsible for all financial decisions: `amount_safe_to_pay`, `affordability_status`, `recommended_payment_method`, `payment_plan`, `earliest_date_for_full_payment`, and `spending_changes_needed`.",
            "- The LLM is strictly constrained to generating natural-language explanations from the precomputed decision facts.",
            "- In the absence of an API key or during network unavailability, the deterministic fallback explanation generator creates fully grounded, consistent explanations with 0 external API cost.",
            "- When running in deterministic fallback mode, exactly 0 external API calls occur and external API cost is $0.000000 USD. Reported token counts represent estimated token equivalents (approx. 4 characters/token) for computational footprint analysis.",
            "",
            "## Detailed Breakdown by Status",
            "",
            "| Provider | Model | Requests | Input Tokens (est.) | Output Tokens (est.) | Total Tokens (est.) | Estimated Cost (USD) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        # Group by provider and model
        groups: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for r in self.records:
            key = (r.provider, r.model)
            if key not in groups:
                groups[key] = {
                    "count": 0,
                    "input": 0,
                    "output": 0,
                    "total": 0,
                    "cost": Decimal("0.000000"),
                }
            groups[key]["count"] += 1
            groups[key]["input"] += r.input_tokens
            groups[key]["output"] += r.output_tokens
            groups[key]["total"] += r.total_tokens
            groups[key]["cost"] += r.estimated_cost

        for (prov, mdl), data in sorted(groups.items()):
            lines.append(
                f"| {prov} | {mdl} | {data['count']:,} | {data['input']:,} | {data['output']:,} | {data['total']:,} | ${data['cost']:.6f} |"
            )

        lines.extend([
            "",
            "## Cost Rates Applied",
            "",
            "- **Gemini 1.5 Flash:** $0.075 / 1M input tokens, $0.30 / 1M output tokens.",
            "- **Deterministic Fallback:** $0.00 / 1M tokens (local evaluation).",
            "",
            f"*Report generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*",
        ])
        return "\n".join(lines)


class ExplanationGenerator:
    """
    Generates concise, grounded explanations for financial decisions.
    
    Adheres strictly to the architectural boundary:
    1. Deterministic PlannerDecision is immutable and authoritative.
    2. Explanations never modify or contradict financial predictions.
    3. Safe deterministic fallback is always available.
    """

    def __init__(
        self,
        accountant: Optional[TokenAccountant] = None,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        timeout_seconds: float = 8.0,
    ):
        self.accountant = accountant or TokenAccountant()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def build_structured_prompt(
        self,
        decision: PlannerDecision,
        profile: UserProfile,
        request: RequestItem,
        events: Optional[Dict[str, FinancialEvent]] = None,
    ) -> str:
        """Construct a prompt strictly framing the LLM as an explanation generator."""
        curr = profile.home_currency
        return f"""You are an explanation generator for a financial advisory system.
The deterministic financial decision below has ALREADY been calculated and is AUTHORITATIVE.
Do NOT recalculate, modify, or question any numbers, dates, payment methods, spending changes, or statuses.
Your sole task is to generate a concise, grounded 1-2 sentence explanation to the user explaining why this decision was reached.

FINANCIAL CONTEXT:
- User Home Currency: {curr}
- Available Balance: {curr} {profile.current_available_balance:,.2f}
- Protected Reserve (Minimum Balance to Keep): {curr} {profile.minimum_balance_to_keep:,.2f}
- Requested Expense: {request.request_type} of {curr} {request.requested_amount:,.2f}
- Desired Completion Date: {request.desired_completion_date}
- Allows Partial Payment: {request.allows_partial_payment}

DETERMINISTIC DECISION (AUTHORITATIVE):
- Affordability Status: {decision.affordability_status}
- Safe to Pay Today: {curr} {decision.amount_safe_to_pay:,.2f}
- Recommended Payment Method: {decision.recommended_payment_method}
- Payment Plan: {decision.payment_plan}
- Earliest Date for Full Payment: {decision.earliest_date_for_full_payment or 'None'}
- Spending Changes Needed: {decision.spending_changes_needed}

INSTRUCTIONS:
1. Write exactly 1 or 2 clear, professional sentences explaining the recommendation.
2. State what action the user should take (e.g. pay today, wait until a date, make installment payments, or avoid paying).
3. Mention that this protects their minimum required balance of {curr} {profile.minimum_balance_to_keep:,.2f}.
4. If spending changes are required, mention stopping or reducing the specific expenses.
5. Do NOT use markdown bolding, code blocks, or preamble. Return ONLY the explanation string.
6. NEVER contradict the deterministic decision.
"""

    def call_gemini_api(self, prompt: str) -> Optional[Tuple[str, int, int]]:
        """Call Gemini REST API without external dependencies."""
        if not self.api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 150,
            },
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        usage = data.get("usageMetadata", {})
                        input_tok = usage.get("promptTokenCount", int(len(prompt) / 4))
                        output_tok = usage.get("candidatesTokenCount", int(len(text) / 4))
                        return text, input_tok, output_tok
        except Exception:
            return None
        return None

    def sanitize_ai_output(self, text: str) -> Optional[str]:
        """Validate and clean AI output to ensure compliance with boundary rules."""
        if not text:
            return None
        cleaned = text.strip().strip('"\'')
        cleaned_lower = cleaned.lower()
        # Reject if forbidden internal implementation words appear
        for forbidden in FORBIDDEN_WORDS:
            if forbidden in cleaned_lower:
                return None
        # Reject if overly long or empty
        if len(cleaned) < 15 or len(cleaned) > 500:
            return None
        return cleaned

    def generate_deterministic_fallback(
        self,
        decision: PlannerDecision,
        profile: UserProfile,
        request: RequestItem,
        events: Optional[Dict[str, FinancialEvent]] = None,
    ) -> str:
        """
        Generate a deterministic, grounded explanation using verified facts.
        
        Adheres to exact dataset patterns:
        - affordable_now: Pay {curr} {amount} today. This leaves at least {curr} {min_balance} available over the next 90 days.
        - affordable_with_plan (installments): Use {N} installments of {curr} {amount}, starting {date}. This leaves at least {curr} {min_balance} available.
        - affordable_with_plan (spending changes): Stop/reduce ..., then pay {curr} {amount} today. This leaves at least {curr} {min_balance} available.
        - affordable_with_plan (partial payment): Pay {curr} {safe} today and the remaining {curr} {rest} on {date}. This completes the full request and keeps the {curr} {min_balance} minimum protected.
        - affordable_later: Pay {curr} {amount} in full on {date}. Paying earlier would take the balance below the {curr} {min_balance} minimum.
        - not_affordable: Do not make this payment by {deadline}. None of the available options keeps the {curr} {min_balance} minimum protected.
        """
        curr = profile.home_currency
        min_bal_str = format_currency_amount(profile.minimum_balance_to_keep, curr)
        req_amt_str = format_currency_amount(request.requested_amount, curr)

        # 1. Affordable Now
        if decision.affordability_status == "affordable_now":
            return f"Pay {req_amt_str} today. This leaves at least {min_bal_str} available over the next 90 days."

        # 2. Affordable Later
        if decision.affordability_status == "affordable_later":
            date_nat = format_date_natural(decision.earliest_date_for_full_payment)
            if date_nat:
                return (
                    f"Pay {req_amt_str} in full on {date_nat}. "
                    f"Paying earlier would take the balance below the {min_bal_str} minimum."
                )
            return (
                f"Wait to pay {req_amt_str} in full. "
                f"Paying earlier would take the balance below the {min_bal_str} minimum."
            )

        # 3. Not Affordable
        if decision.affordability_status == "not_affordable":
            deadline_nat = format_date_natural(request.desired_completion_date)
            deadline_phrase = f" by {deadline_nat}" if deadline_nat else ""
            return (
                f"Do not make this payment{deadline_phrase}. "
                f"None of the available options keeps the {min_bal_str} minimum protected."
            )

        # 4. Affordable With Plan
        if decision.affordability_status == "affordable_with_plan":
            method = decision.recommended_payment_method
            plan_str = decision.payment_plan

            # Case 4a: Partial Payment
            if method == "partial_payment" and plan_str != "none":
                parts = plan_str.split("|")
                if len(parts) == 2:
                    p1_amt = Decimal(parts[0].split(":")[1])
                    p2_date = parts[1].split(":")[0]
                    p2_amt = Decimal(parts[1].split(":")[1])
                    p1_str = format_currency_amount(p1_amt, curr)
                    p2_str = format_currency_amount(p2_amt, curr)
                    p2_date_nat = format_date_natural(p2_date)
                    return (
                        f"Pay {p1_str} today and the remaining {p2_str} on {p2_date_nat}. "
                        f"This completes the full request and keeps the {min_bal_str} minimum protected."
                    )

            # Case 4b: Installments
            if method == "installments" and plan_str != "none":
                parts = plan_str.split("|")
                n_inst = len(parts)
                first_date = parts[0].split(":")[0]
                first_amt = Decimal(parts[0].split(":")[1])
                inst_amt_str = format_currency_amount(first_amt, curr)
                start_date_nat = format_date_natural(first_date)
                
                # Check if spending changes also needed for installments
                if decision.spending_changes_needed != "none":
                    changes_desc = self._describe_spending_changes(decision.spending_changes_needed, curr, events)
                    return (
                        f"{changes_desc}, then use {n_inst} installments of {inst_amt_str}, "
                        f"starting {start_date_nat}. This leaves at least {min_bal_str} available."
                    )
                return (
                    f"Use {n_inst} installments of {inst_amt_str}, starting {start_date_nat}. "
                    f"This leaves at least {min_bal_str} available."
                )

            # Case 4c: Spending Changes with Full Payment
            if decision.spending_changes_needed != "none":
                changes_desc = self._describe_spending_changes(decision.spending_changes_needed, curr, events)
                pay_action = f"pay {req_amt_str} today"
                if plan_str != "none":
                    first_plan_date = plan_str.split("|")[0].split(":")[0]
                    if first_plan_date == request.request_date:
                        pay_action = f"pay {req_amt_str} today"
                    else:
                        date_nat = format_date_natural(first_plan_date)
                        pay_action = f"pay {req_amt_str} on {date_nat}"
                elif decision.earliest_date_for_full_payment and decision.earliest_date_for_full_payment != request.request_date:
                    date_nat = format_date_natural(decision.earliest_date_for_full_payment)
                    pay_action = f"pay {req_amt_str} on {date_nat}"
                return f"{changes_desc}, then {pay_action}. This leaves at least {min_bal_str} available."

            # Default fallback for affordable_with_plan
            return f"Follow the recommended plan for {req_amt_str}. This leaves at least {min_bal_str} available."

        # Generic safe fallback
        return f"Payment of {req_amt_str} preserves the {min_bal_str} minimum reserve."

    def _describe_spending_changes(
        self,
        changes_str: str,
        curr: str,
        events: Optional[Dict[str, FinancialEvent]] = None,
    ) -> str:
        """Convert spending changes into natural language description."""
        if not changes_str or changes_str == "none":
            return ""

        parts = changes_str.split("|")
        descriptions = []
        for part in parts:
            part = part.strip()
            if part.startswith("stop:"):
                eid = part.split(":")[1]
                event = events.get(eid) if events else None
                desc = event.description if event and event.description else eid
                desc_clean = desc.lower()
                if not desc_clean.startswith("the "):
                    desc_clean = f"the {desc_clean}"
                descriptions.append(f"stop {desc_clean}")
            elif part.startswith("reduce_to:"):
                seg = part.split(":")
                eid = seg[1]
                amt_dec = Decimal(seg[2])
                amt_str = format_currency_amount(amt_dec, curr)
                event = events.get(eid) if events else None
                desc = event.description if event and event.description else eid
                desc_clean = desc.lower()
                if not desc_clean.startswith("the "):
                    desc_clean = f"the {desc_clean}"
                descriptions.append(f"reduce {desc_clean} to {amt_str}")

        if not descriptions:
            return "Adjust flexible spending"

        if len(descriptions) == 1:
            res = descriptions[0]
            return res[0].upper() + res[1:]
        elif len(descriptions) == 2:
            res = f"{descriptions[0]} and {descriptions[1]}"
            return res[0].upper() + res[1:]
        else:
            res = f"{', '.join(descriptions[:-1])}, and {descriptions[-1]}"
            return res[0].upper() + res[1:]

    def generate_explanation(
        self,
        decision: PlannerDecision,
        profile: UserProfile,
        request: RequestItem,
        events: Optional[Dict[str, FinancialEvent]] = None,
    ) -> str:
        """
        Generate explanation enforcing strict AI boundary and safe fallback.
        Never modifies decision fields.
        """
        # Snapshot decision fields before generation to ensure immutability
        orig_safe = decision.amount_safe_to_pay
        orig_status = decision.affordability_status
        orig_method = decision.recommended_payment_method
        orig_plan = decision.payment_plan
        orig_date = decision.earliest_date_for_full_payment
        orig_changes = decision.spending_changes_needed

        # 1. If API key is available, attempt LLM call
        if self.api_key:
            try:
                prompt = self.build_structured_prompt(decision, profile, request, events)
                llm_result = self.call_gemini_api(prompt)
                if llm_result:
                    text, in_tok, out_tok = llm_result
                    sanitized = self.sanitize_ai_output(text)
                    if sanitized:
                        self.accountant.record(
                            request_id=request.request_id,
                            provider="gemini",
                            model=self.model_name,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            is_fallback=False,
                        )
                        return sanitized
            except Exception:
                pass  # Cleanly fallback on any unhandled network or parsing exception

        # 2. Deterministic Fallback
        fallback_text = self.generate_deterministic_fallback(decision, profile, request, events)
        # Estimate token footprint for accounting
        est_in_tokens = int(len(f"{request.request_type} {request.requested_amount} {decision.affordability_status}") / 4) + 50
        est_out_tokens = int(len(fallback_text) / 4)

        self.accountant.record(
            request_id=request.request_id,
            provider="fallback",
            model="deterministic-fallback",
            input_tokens=est_in_tokens,
            output_tokens=est_out_tokens,
            is_fallback=True,
        )

        # Enforce boundary: confirm decision fields were not mutated
        assert decision.amount_safe_to_pay == orig_safe, "Deterministic field amount_safe_to_pay was mutated!"
        assert decision.affordability_status == orig_status, "Deterministic field affordability_status was mutated!"
        assert decision.recommended_payment_method == orig_method, "Deterministic field recommended_payment_method was mutated!"
        assert decision.payment_plan == orig_plan, "Deterministic field payment_plan was mutated!"
        assert decision.earliest_date_for_full_payment == orig_date, "Deterministic field earliest_date_for_full_payment was mutated!"
        assert decision.spending_changes_needed == orig_changes, "Deterministic field spending_changes_needed was mutated!"

        return fallback_text
