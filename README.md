# HackerRank Orchestrate: Buy or Wait? Financial Decision Agent

Production-grade, deterministic AI financial agent for the **HackerRank Orchestrate** 24-hour hackathon (September 2026).

---

## 1. Project Overview

The "Buy or Wait?" agent evaluates whether a user can safely afford a requested expense (laptop, travel, medical procedure, education, etc.) while guaranteeing financial safety throughout a 90-day forward-looking projection window.

### Key Capabilities:
- **Multimodal Evidence Resolution:** Normalizes financial profiles, transactions, and dated currency conversions. Resolves missing receipts and salary confirmations from multimodal image/message evidence.
- **Accurate Cash-Flow Simulation:** Maintains a day-by-day cash balance timeline over 90 days. Accurately accounts for confirmed salary settlements, recurring commitments, and non-cash asset liquidations.
- **Strict Liquidity Floor Protection:** Guarantees available balance never drops below `minimum_balance_to_keep`.
- **Intelligent Payment Planning:** Automatically ranks and selects from single full payments, seller installment options, waiting for income/payday, and partial payments.
- **Deterministic Spending Optimization:** Identifies and recommends up to three flexible, non-protected expense reductions or cancellations (`stop:<event_id>` or `reduce_to:<event_id>:<amount>`) when necessary to unlock safe affordability.
- **Grounded AI Explanations:** Explains decisions in concise, natural language without hallucinating facts or altering deterministic financial determinations.

---

## 2. System Architecture & End-to-End Pipeline

The agent strictly separates **authoritative deterministic financial computation** from the **natural language explanation layer**:

```text
               ┌────────────────────────────────────────────────────────┐
               │                  dataset/ CSV Files                    │
               │ (profiles, events, options, rates, messages, images)   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Evidence Resolver (code/evidence.py, code/currency.py)                   │
│ - Reconstructs user profile, dated FX rates, message flags & image extractions    │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Recurrence & Timeline Builder (code/financial_engine.py)                 │
│ - Detects recurring intervals, confirmed paydays, and builds 90-day balance curve │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 4 / 4.1: 90-Day Affordability Simulator (code/affordability.py)             │
│ - Simulates cash flows; computes official Phase 4 amount_safe_to_pay              │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Payment Planner (code/planner.py)                                        │
│ - Generates and ranks candidates: full_payment, installments, wait, partial_pay   │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 6 / 6.1: Spending Optimizer (code/spending_optimizer.py)                    │
│ - Discovers minimal flexible expense reductions/stops (max 3) if base plan unsafe │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ DETERMINISTIC SOURCE OF TRUTH: PlannerDecision                                    │
│ (amount_safe_to_pay, affordability_status, recommended_payment_method, ...)       │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7: AI Explanation & Validation Layer (code/explanation.py, code/validator.py│
│ - Natural language explanation (Gemini API or grounded deterministic fallback)    │
│ - 10-point schema, constraint, and fidelity validation                            │
└──────────────────────────────────────────┬────────────────────────────────────────┘
                                           │
                                           ▼
                   ┌───────────────────────┴───────────────────────┐
                   ▼                                               ▼
             output.csv                              evaluation/usage_report.md
```

---

## 3. How to Run

### Primary Entrypoint
To process the complete dataset and generate `output.csv` and `evaluation/usage_report.md`:

```bash
python3 code/main.py
```
*(On Windows systems where `python3` is mapped to `python`: `python code/main.py`)*

### Optional Flags
```bash
# Evaluate only the 25 sample requests
python3 code/main.py --sample-only

# Specify custom dataset directory or output locations
python3 code/main.py --dataset-dir path/to/dataset --output path/to/output.csv --report path/to/report.md
```

---

## 4. Required Environment Variables

The system is 100% self-contained and functions out-of-the-box with **zero required environment variables**.

If you wish to use an external Google Gemini model for explanations:
```bash
export GEMINI_API_KEY="your_api_key_here"
```
On Windows PowerShell:
```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

If `GEMINI_API_KEY` is not provided (or network is offline), the built-in deterministic fallback generator automatically provides grounded, verified explanations with **$0.00 cost** and **zero downtime**.

---

## 5. AI Provider & Model Configuration

- **Provider:** Google Gemini REST API (or Deterministic Fallback Engine)
- **Model:** `gemini-1.5-flash` (or `gemini-2.5-flash`)
- **Temperature:** `0.2` (for high determinism and groundedness)
- **Max Tokens:** `150` tokens

### Strict AI Boundary
1. The LLM receives pre-computed deterministic facts as immutable context.
2. The LLM **never** decides or modifies:
   - `amount_safe_to_pay`
   - `affordability_status`
   - `recommended_payment_method`
   - `payment_plan`
   - `earliest_date_for_full_payment`
   - `spending_changes_needed`
3. If an LLM response fails, times out, or contains forbidden implementation artifacts, it is automatically discarded and replaced with the deterministic fallback explanation.

---

## 6. Deterministic Financial Engine

- **Currencies Supported:** INR, ZAR, IDR, USD, EUR using dated rates from `exchange_rates.csv`.
- **Conservative Accounting:**
  - Pending debits are reserved against balance.
  - Pending credits, bonuses, refunds, and unliquidated investments are NOT counted until settled.
  - Salary is recognized strictly on confirmed settlement dates.
- **Safe Amount:** Computed as `min(requested_amount, max(0, min_projected_balance - minimum_balance_to_keep))` over the 90-day forecast.
- **Strategy Ranking:**
  1. `affordable_now` / `full_payment` (today without modifications)
  2. `affordable_with_plan` / `installments` (seller financing without modifications)
  3. `affordable_later` / `wait` (safe full payment on upcoming confirmed payday)
  4. `affordable_with_plan` / `partial_payment` (safe partial payment today + remainder on payday)
  5. `affordable_with_plan` with spending changes (up to 3 flexible stops/reductions)
  6. `not_affordable` / `not_recommended`

---

## 7. Testing & Quality Assurance

The codebase includes an extensive, modular test suite of **127 unit and integration tests** with 100% pass rate.

Run all tests:
```bash
python -m pytest code/tests/ -q
```

### Test Suite Structure:
- `code/tests/test_evidence.py` (8 tests): Evidence normalization, currency conversions, image/message extraction.
- `code/tests/test_financial_engine.py` (20 tests): Recurrence detection, payday recognition, timeline simulation.
- `code/tests/test_affordability.py` (26 tests): 90-day balance projections, safe-to-pay calculations.
- `code/tests/test_planner.py` (24 tests): Payment candidate generation, ranking, and constraint satisfaction.
- `code/tests/test_spending_changes.py` (22 tests): Flexible expense optimization, stop and reduce_to combinations.
- `code/tests/test_phase6_1_regressions.py` (4 tests): Wait vs partial payment precedence checks.
- `code/tests/test_explanation.py` (11 tests, Tests A–K): AI boundary, immutability, fallback safety, token accounting.
- `code/tests/test_output_validation.py` (12 tests, Tests L–W): Output schema, bounds, formatting, deadline compliance.

---

## 8. Output Format & Schema Validation

The final generated `output.csv` at the repository root contains predictions for every evaluated request.

### Exact Schema:
```text
request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation
```

### Constraint Checks:
1. `amount_safe_to_pay`: Float/decimal within `[0, requested_amount]`.
2. `affordability_status`: One of `affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable`.
3. `recommended_payment_method`: One of `full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`.
4. `payment_plan`: Chronological `YYYY-MM-DD:amount` joined by `|`, or `none`. Sum matches purchase obligation.
5. `earliest_date_for_full_payment`: `YYYY-MM-DD` or empty. Complies with `desired_completion_date`.
6. `spending_changes_needed`: Up to three `stop:<event_id>` or `reduce_to:<event_id>:<amount>` actions, or `none`.
7. `decision_explanation`: Concise, professional, natural-language explanation grounded strictly in the evidence.

---

## 9. Token & Cost Accounting

Detailed token and cost accounting is saved to `evaluation/usage_report.md` after every evaluation run.

### Summary Metrics:
- **Total Requests:** 250 (Evaluation requests from `dataset/requests.csv`)
- **Execution Runtime:** ~4.2 seconds
- **Throughput:** ~60.0 requests/second
- **Fallback Explanations:** 250 (0 external API calls required in offline mode)
- **Total Estimated Cost:** $0.000000 USD

---

## 10. Security Note

- **No Secrets in Code:** No API keys, credentials, tokens, or environment files (`.env`) are committed to this repository.
- **Audit Logging:** The conversation and tool audit log is maintained in `log.txt` in compliance with `AGENTS.md`.

---

## 11. Submission Deliverables

- `code.zip`: Complete runnable codebase, UI dashboard, test suite, and configuration.
- `output.csv`: Authoritative 250-row predictions file matching `dataset/requests.csv`.
- `evaluation/usage_report.md`: Detailed token usage and cost accounting report.
- `log.txt`: Append-only audit transcript.
- `PHASE13_UI_REPORT.md`: Comprehensive Demo UI architecture and verification report.
- `UI_DESIGN_GUIDE.md`: Professional banking design system and judge demo guide.

---

## 12. Demo UI (Interactive Judge Dashboard)

A local, lightweight, zero-dependency web dashboard is provided in `code/ui/` to demonstrate the deterministic "Buy or Wait?" financial decision engine to judges.

> **Important:** The UI is strictly a read-only presentation layer. It loads pre-computed results directly from `output.csv` and does NOT recalculate any financial decisions.

### Quick Start

Launch using either **NPM** or **Python**:

```bash
# Option A: Using NPM
npm start
# or
npm run dev

# Option B: Using Python directly
python code/ui/server.py
```

Once running, navigate to:
```text
http://localhost:8080/
```

### Key UI Features
- **Summary Metrics:** Real-time counters showing Total Evaluation Requests (250), Affordable Now (53), Affordable with Plan (100), Affordable Later (53), and Not Affordable (44).
- **Search & Multi-Filter:** Instantly filter requests by status, search by User ID, Request ID, Item Name, or Currency.
- **Visual Status Badges:** Color-coded status badges (`affordable_now` green, `affordable_with_plan` blue, `affordable_later` amber, `not_affordable` red).
- **Comprehensive Detail View:**
  - **Decision Card:** Safe amount to pay, recommended payment method, and earliest safe full payment date.
  - **Payment Plan Breakdown:** Chronological table of installment dates and amounts.
  - **Spending Changes Needed:** Distinct visual badges for non-protected spending adjustments (`stop:<event_id>` or `reduce_to:<event_id>:<amount>`).
  - **Why this decision?:** Full grounded natural language explanation.
  - **90-Day Financial Safety Check:** Minimum balance to keep vs. projected safe floor and safety buffer confirmation.
- **Benchmark Comparison Tab (`SAMPLE / REFERENCE`):** Toggle between the 250 evaluation requests and the 25 reference sample requests, with prominent quick-jump buttons for the 7 milestone benchmark scenarios (`request_06`, `request_11`, `request_18`, `request_19`, `request_21`, `request_22`, `request_25`).

