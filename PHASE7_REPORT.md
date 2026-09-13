# Phase 7 Verification Report: AI Decision Explanations & Final Output Preparation

HackerRank Orchestrate September 2026 — "Buy or Wait?" Financial Decision Agent

---

## 1. AI Architecture

The agent implements a strict **two-tier decoupled architecture**:
1. **Tier 1 — Deterministic Financial Core (Phases 1–6.1):**
   - Ingests raw multi-table data (profiles, events, options, rates, messages, images).
   - Simulates 90-day day-by-day cash flows using `decimal.Decimal` fixed-point arithmetic.
   - Computes conservative `amount_safe_to_pay`, selects optimal `recommended_payment_method`, constructs `payment_plan`, calculates `earliest_date_for_full_payment`, and optimizes up to three `spending_changes_needed`.
   - Produces the immutable `PlannerDecision` object.
2. **Tier 2 — Natural Language Explanation & Validation Layer (Phase 7):**
   - Consumes the immutable `PlannerDecision` and user financial context.
   - Generates natural, grounded explanations without ever recalculating or modifying financial fields.
   - Enforces a 10-point validation suite on output schema, data types, plan formatting, bounds, deadlines, and explanation safety before writing `output.csv`.

```text
+-------------------------------------------------------------+
|               DETERMINISTIC FINANCIAL CORE                  |
| EvidenceResolver -> TimelineBuilder -> AffordabilitySim ->  |
| PaymentPlanner -> SpendingOptimizer                         |
+------------------------------+------------------------------+
                               | Immutable PlannerDecision
                               v
+-------------------------------------------------------------+
|             EXPLANATION & VALIDATION LAYER                  |
| ExplanationGenerator (Gemini API + Grounded Fallback)       |
| TokenAccountant (Usage & Cost Tracking)                     |
| OutputValidator (10-Point Contract & Schema Checks)         |
+------------------------------+------------------------------+
                               | Validated Predictions
                               v
                       output.csv (275 rows)
```

---

## 2. Prompt Design

The LLM prompt is structured to enforce the strict boundary:
- **Authoritative Framing:** Explicitly instructs the model that the precomputed decision is authoritative and must not be recalculated, questioned, or modified.
- **Structured Context:** Supplies exact numbers, dates, methods, statuses, and protected minimum balance reserve.
- **Conciseness & Grounding:** Limits output to 1–2 clear, professional sentences explaining the recommendation.
- **Safety Filters:** Prohibits markdown bolding, code blocks, preambles, and internal implementation terminology.

---

## 3. Model & Provider Configuration

- **Supported Providers:**
  - Google Gemini API (`gemini-1.5-flash` / `gemini-2.5-flash`) via standard REST endpoints (`urllib.request` / `httpx`).
  - Offline Deterministic Fallback Engine (fully offline, 0 dependencies, instant response).
- **Default Behavior:** In the absence of an API key (`GEMINI_API_KEY`), the system seamlessly engages the deterministic fallback generator.
- **Execution Cost:** $0.000000 USD in offline evaluation mode.

---

## 4. Deterministic vs. AI Responsibility Boundary

| Financial Field | Responsible Engine | Role of AI |
| :--- | :--- | :--- |
| `amount_safe_to_pay` | Deterministic Simulator (Phase 4) | **Read-only context** (cannot modify) |
| `affordability_status` | Deterministic Planner (Phase 5/6.1) | **Read-only context** (cannot modify) |
| `recommended_payment_method` | Deterministic Planner (Phase 5/6.1) | **Read-only context** (cannot modify) |
| `payment_plan` | Deterministic Planner (Phase 5/6.1) | **Read-only context** (cannot modify) |
| `earliest_date_for_full_payment` | Deterministic Simulator (Phase 4/5) | **Read-only context** (cannot modify) |
| `spending_changes_needed` | Spending Optimizer (Phase 6/6.1) | **Read-only context** (cannot modify) |
| `decision_explanation` | ExplanationGenerator (Phase 7) | **Sole responsibility of AI/Fallback** |

Every prediction row is validated against the original `PlannerDecision` to assert that zero financial fields were altered by the explanation generation step.

---

## 5. Fallback Mechanism

If the LLM call fails, times out, is offline, or returns text with forbidden implementation artifacts (`python`, `planner.py`, `phase 4`, etc.), the deterministic fallback generator immediately produces grounded natural-language explanations:
- **`affordable_now`:** States the user can pay today and highlights the preserved minimum balance reserve over the next 90 days.
- **`affordable_with_plan` (Installments):** Describes the number of installments, installment amount, and start date.
- **`affordable_with_plan` (Spending Changes):** Discovers event descriptions from evidence and describes the exact actions: e.g. *"Stop the family streaming plan, then pay EUR 620.40 today. This leaves at least EUR 800 available."*
- **`affordable_with_plan` (Partial Payment):** Details the safe payment today and the second payment on the confirmed settlement date.
- **`affordable_later`:** Recommends waiting until the confirmed safe date (e.g. payday) so the minimum balance reserve is never breached.
- **`not_affordable`:** Explains that no available plan preserves the required minimum balance reserve by the deadline.

---

## 6. Token Accounting

All token usage is tracked per request in memory via `TokenAccountant`:
- Per-request records: input tokens, output tokens, total tokens, provider, model, latency, and status.
- Final summary report generated and exported to `evaluation/usage_report.md` and `code/evaluation/usage_report.md`.

---

## 7. Cost Accounting

- **Cost Model:**
  - Gemini 1.5 Flash: $0.075 / 1M input tokens, $0.30 / 1M output tokens.
  - Deterministic Fallback: $0.00 / 1M tokens.
- **Offline Run Cost:** $0.000000 USD across 275 requests.

---

## 8. 25-Sample Benchmark Verification

All 25 sample requests from `dataset/sample_requests.csv` were evaluated and verified against ground truth:
- **Spending Changes Accuracy:** 25 / 25 (100.0%)
- **Status Accuracy:** 23 / 25 (92.0%)
- **Payment Method Accuracy:** 23 / 25 (92.0%)
- **Key Diagnostic Samples:**
  - `request_06`: `stop:event_476` (Family streaming plan) -> **MATCH**
  - `request_11`: `reduce_to:event_989:665950` (Weekend food delivery) -> **MATCH**
  - `request_18`: `affordable_later` / `wait` on 2026-09-15 payday -> **MATCH**
  - `request_19`: `partial_payment` (safe today + balance on payday) -> **MATCH**
  - `request_21`: `stop:event_1815|reduce_to:event_1816:23.50` -> **MATCH**
  - `request_22`: `affordable_with_plan` / `installments` -> **MATCH**
  - `request_25`: `not_affordable` / `not_recommended` -> **MATCH**

---

## 9. Full 275-Request Population Run

Executing `python3 code/main.py`:
- **Total Requests Evaluated:** 275 (`request_01` to `request_275`)
- **Successful Requests:** 275 (100.0%)
- **Failed Requests:** 0 (0.0%)
- **Runtime:** 15.76 seconds
- **Throughput:** 17.45 requests/second

### Affordability Status Breakdown:
| Status | Count | Percentage |
| :--- | :--- | :--- |
| `affordable_with_plan` | 109 | 39.6% |
| `affordable_now` | 58 | 21.1% |
| `affordable_later` | 58 | 21.1% |
| `not_affordable` | 50 | 18.2% |

### Recommended Payment Method Breakdown:
| Method | Count | Percentage |
| :--- | :--- | :--- |
| `full_payment` | 85 | 30.9% |
| `installments` | 73 | 26.5% |
| `wait` | 58 | 21.1% |
| `not_recommended` | 50 | 18.2% |
| `partial_payment` | 9 | 3.3% |

### Spending Changes Breakdown:
- **No changes needed (`none`):** 248 requests (90.2%)
- **Active spending changes:** 27 requests (9.8%)

---

## 10. Output Validation

`OutputValidator` programmatically verified the final `output.csv`:
- [x] Exact required columns and order:
  `request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation`
- [x] Exactly 275 rows (one row per request).
- [x] Zero duplicate or missing request IDs.
- [x] Every request from `dataset/requests.csv` appears exactly once.
- [x] Safe amount bounds: `0 <= amount_safe_to_pay <= requested_amount`.
- [x] Payment plan syntax and sums match purchase obligations.
- [x] Spending changes syntax valid (`stop:<event_id>` or `reduce_to:<event_id>:<amount>`), max 3 changes.
- [x] Deadline compliance verified.
- [x] Explanations non-empty and free of forbidden system implementation terms.

---

## 11. Security Review

- **Zero Secrets Committed:** No API keys, passwords, private keys, or tokens are committed in code or logs.
- **Sanitized Outputs:** Logs and markdown reports contain only aggregated token counts and costs.
- **Network Resilience:** The agent is completely self-contained and operates without mandatory network access.

---

## 12. Submission Package Contents

The `code.zip` archive contains:
- `code/`: All source modules (`main.py`, `evidence.py`, `currency.py`, `models.py`, `financial_engine.py`, `affordability.py`, `planner.py`, `spending_optimizer.py`, `explanation.py`, `validator.py`)
- `code/tests/`: Complete unit and regression test suite (127 tests)
- `README.md`: System documentation and execution guide
- `evaluation/usage_report.md`: Token usage and cost accounting report
- `output.csv`: The final 275-row predictions file
- `log.txt`: Conversation and tool audit transcript

---

## 13. Known Limitations & Future Work

- **LLM Rate Limits:** When connecting to live cloud LLM APIs for high-volume batch evaluations, rate-limiting or network latency can occur; the deterministic fallback ensures zero interruption.
- **Multimodal Image OCR:** Image-based receipts currently resolve through structured metadata extraction; adding on-device vision models (e.g. Gemini Nano) could enable offline OCR directly on edge devices.
