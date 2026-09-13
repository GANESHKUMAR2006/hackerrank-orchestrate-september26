# DATASET_ANALYSIS.md — Comprehensive Dataset Specification & Findings

This document provides the complete empirical data analysis for the **HackerRank Orchestrate (September 2026) — Buy or Wait?** hackathon challenge. All statistics, schemas, relationships, patterns, and edge cases are derived from direct inspection of the provided dataset files in `dataset/`.

---

## 1. File Inventory & Exact Schemas

| File | Rows | Columns | Purpose |
|---|---|---|---|
| `requests.csv` | 250 | 8 | Target evaluation requests (`request_26` to `request_275`). One prediction row required per request. |
| `sample_requests.csv` | 25 | 15 | Public ground-truth solved examples (`request_01` to `request_25`). Used for regression and specification calibration. |
| `financial_profiles.csv` | 275 | 10 | User balance, minimum safety floor, priority categories, adjustable spending permissions, payment method allowances. |
| `financial_events.csv` | 25,342 | 14 | Historical, pending, scheduled, cancelled, failed, and non-cash transactions across 22 categories. |
| `request_payment_options.csv` | 790 | 9 | Seller/merchant financing offers per request (full payment, installments, fees, frequencies). |
| `exchange_rates.csv` | 134 | 4 | Dated conversion rates for foreign currency transactions. |
| `messages.csv` | 215 | 7 | Real-world updates from employers, banks, merchants, and service providers modifying financial state. |
| `images.csv` | 16 | 4 | Image metadata linking PNG receipts/invoices to events with missing amounts. |
| `output.csv` (in `dataset/`) | 250 | 8 | Blank submission template matching the required submission output columns. |
| `media/images/` | 16 files | — | PNG receipt, bill, payslip, and invoice images (`image_01.png` to `image_16.png`). |

### Exact Column Definitions and Data Types

#### 1. `requests.csv` & `sample_requests.csv`
- `request_id` (*str*): Unique identifier (`request_01` to `request_275`).
- `user_id` (*str*): Request owner (`user_01` to `user_275`). Strictly 1:1 mapping with `request_id`.
- `request_date` (*date YYYY-MM-DD*): Evaluation date.
- `request_type` (*str*): One of 9 categories: `purchase`, `travel`, `education`, `family_transfer`, `debt_repayment`, `investment`, `housing`, `emergency_expense`, `other`.
- `requested_amount` (*float*): Total proposed commitment in user's home currency.
- `desired_completion_date` (*date YYYY-MM-DD*): User's deadline for completing full payment.
- `allows_partial_payment` (*bool str: 'true'/'false'*): Whether partial payment schedule is allowed by seller.
- `request_text` (*str*): Unstructured natural language query from the user.

*Additional Ground-Truth Columns in `sample_requests.csv` and required in root `output.csv`:*
- `amount_safe_to_pay` (*float*): Largest amount safe to pay on `request_date` before optional spending changes. Satisfies `0 <= amount_safe_to_pay <= requested_amount`.
- `affordability_status` (*str*): One of `affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable`.
- `recommended_payment_method` (*str*): One of `full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`.
- `payment_plan` (*str*): Chronological `<YYYY-MM-DD>:<amount>|<YYYY-MM-DD>:<amount>` or `none`.
- `earliest_date_for_full_payment` (*str*): `YYYY-MM-DD` or empty. Equals `request_date` for `affordable_now`.
- `spending_changes_needed` (*str*): `none` or up to 3 actions (`stop:<event_id>` or `reduce_to:<event_id>:<amount>`).
- `decision_explanation` (*str*): Concise explanation grounded in user balance and safety metrics.

#### 2. `financial_profiles.csv`
- `user_id` (*str*): Unique user identifier (`user_01` to `user_275`).
- `home_currency` (*str*): Home currency code (`INR`, `ZAR`, `IDR`, `USD`, `EUR`).
- `current_available_balance` (*float*): Liquid cash balance on `request_date`.
- `minimum_balance_to_keep` (*float*): Safety reserve threshold that balance must never drop below.
- `financial_priorities` (*str*): Pipe-delimited list of financial priorities (e.g. `education|debt_repayment`).
- `expense_categories_to_protect` (*str*): Categories that can never be stopped or reduced.
- `expense_categories_user_is_willing_to_reduce` (*str*): Categories allowed for `reduce_to`.
- `expense_categories_user_is_willing_to_stop` (*str*): Categories allowed for `stop`.
- `payment_methods_user_will_consider` (*str*): Pipe-delimited considered payment methods (e.g. `full_payment|installments`).
- `max_installment_months` (*str/int*): Maximum allowed financing term in months. Blank if installments rejected.

#### 3. `financial_events.csv`
- `event_id` (*str*): Unique event ID (`event_01` to `event_25342`).
- `user_id` (*str*): User identifier.
- `event_type` (*str*): `expense`, `subscription`, `income`, `debt_payment`, `investment_purchase`, `refund`, `investment_valuation`, `investment_sale`.
- `description` (*str*): Merchant / transaction descriptor.
- `category` (*str*): One of 22 categories: `groceries`, `transport`, `dining`, `salary`, `utilities`, `rent`, `cloud_storage`, `shopping`, `streaming`, `debt_repayment`, `entertainment`, `insurance`, `music_subscription`, `healthcare`, `delivery_membership`, `education`, `housing`, `gym`, `family_support`, `investment`, `work_expense`, `windfall`.
- `direction` (*str*): `debit` (23,609), `credit` (1,723), `non_cash` (10).
- `amount` (*float/blank*): Transaction magnitude. Blank in exactly 16 rows (must be extracted from linked images).
- `currency` (*str*): Transaction currency code.
- `event_date` (*date YYYY-MM-DD*): Authorization / transaction initiation date.
- `settlement_date` (*date YYYY-MM-DD*): Settlement date when cash transfers.
- `status` (*str*): `settled`, `pending`, `scheduled`, `cancelled`, `failed`, `unrealized`.
- `linked_event_id` (*str*): Reference to earlier event in lifecycle (refund, retry, valuation update).
- `flexibility` (*str*): `fixed`, `reducible`, `stoppable`, `reducible_or_stoppable`.
- `minimum_allowed_amount` (*float/blank*): Lower bound floor when applying `reduce_to`.

#### 4. `request_payment_options.csv`
- `payment_option_id` (*str*): Offer ID (`payment_option_01` to `payment_option_790`).
- `request_id` (*str*): Associated request ID.
- `payment_method` (*str*): `full_payment` (275) or `installments` (515).
- `payment_amount` (*float*): Amount per installment or full payment.
- `number_of_payments` (*int*): Number of installments (1 for full_payment; 2, 3, 4, 6, 15, 18, 21, 24 for installments).
- `first_payment_date` (*date YYYY-MM-DD*): Schedule start date.
- `payment_frequency_days` (*int/blank*): Days between consecutive payments (typically 28, 30, or 31). Blank for full payment.
- `financing_fee` (*float*): Extra interest/fee charged for financing.
- `total_payable_amount` (*float*): Total sum paid across all payments (`payment_amount * number_of_payments`).

#### 5. `exchange_rates.csv`
- `rate_date` (*date YYYY-MM-DD*): Date the rate was effective.
- `from_currency` (*str*): Foreign transaction currency.
- `to_currency` (*str*): User's home currency.
- `rate` (*float*): Fixed multiplier (`home_amount = foreign_amount * rate`).

#### 6. `messages.csv`
- `message_id` (*str*): Unique identifier (`message_01` to `message_215`).
- `user_id` (*str*): Associated user.
- `request_id` (*str/blank*): Associated request if context-specific.
- `related_event_id` (*str/blank*): Direct reference to one financial event if applicable.
- `sent_at` (*ISO-8601 timestamp*): Sent time.
- `source_type` (*str*): `employer` (126), `service_provider` (31), `financial_service` (23), `bank` (18), `merchant` (17).
- `message_text` (*str*): Natural language notification text in English or Indonesian.

#### 7. `images.csv`
- `image_id` (*str*): Image filename key (`image_01` to `image_16`).
- `user_id` (*str*): Associated user.
- `request_id` (*str*): Associated request.
- `related_event_id` (*str*): Financial event with blank amount.

---

## 2. Join Relationships & Entity Integrity

```
financial_profiles (user_id) [1]
        │
        ├── [1:1] ── requests (request_id, user_id)
        │                 │
        │                 ├── [1:N] ── request_payment_options (request_id)
        │
        ├── [1:N] ── financial_events (event_id, user_id)
        │                 ▲               │
        │                 │ [linked_id]   └── [1:1 if blank amt] ── images (related_event_id, image_id)
        │                 └───────────────┘                                    │
        │                                                                      ▼
        │                                                           dataset/media/images/<image_id>.png
        │
        └── [1:N] ── messages (user_id, [request_id], [related_event_id])
```

- **User 1:1 Request**: Each user has exactly one evaluation request (`user_01` to `user_25` in `sample_requests.csv`; `user_26` to `user_275` in `requests.csv`).
- **Exchange Rates**: Matched strictly by `settlement_date` (or `event_date`), `from_currency`, and `to_currency`.

---

## 3. Financial Event Types & Status Combinations

Empirical distribution of 25,342 events:

| Event Type | Total Rows | Settled | Pending | Scheduled | Cancelled | Failed | Unrealized |
|---|---|---|---|---|---|---|---|
| `expense` | 20,525 | 20,432 | 41 | 31 | 14 | 7 | 0 |
| `subscription` | 2,488 | 2,488 | 0 | 0 | 0 | 0 | 0 |
| `income` | 1,696 | 1,664 | 0 | 32 | 0 | 0 | 0 |
| `debt_payment` | 567 | 546 | 0 | 7 | 0 | 14 | 0 |
| `investment_purchase` | 29 | 29 | 0 | 0 | 0 | 0 | 0 |
| `refund` | 22 | 14 | 8 | 0 | 0 | 0 | 0 |
| `investment_valuation` | 10 | 0 | 0 | 0 | 0 | 0 | 10 |
| `investment_sale` | 5 | 5 | 0 | 0 | 0 | 0 | 0 |

### Cash Treatment Rules
1. `settled`: Counted in past balances.
2. `pending debit`: Immediate liability; must be reserved from available balance.
3. `pending credit` / `pending refund`: Ignore until settled (never count unconfirmed credits).
4. `scheduled debit`: Fixed future commitment on its settlement date.
5. `scheduled credit` (confirmed salary): Add to balance on its settlement date.
6. `cancelled`: Completely ignored; zero cash effect.
7. `failed debit`:
   - Default: ignored.
   - Exception: When a bank message explicitly states *"The bill is still outstanding and another debit will be attempted"*, the debit must remain reserved as an upcoming liability.
8. `unrealized` (investment valuation increases): Ignored; non-cash asset value changes cannot be spent.

---

## 4. Multimodal Image Analysis (16 Blank-Amount Events)

All 16 blank amounts were located in `images.csv` and extracted from `dataset/media/images/<image_id>.png`:

| Image ID | Event ID | User ID | Category | Description | Extracted Amount | Currency | Document Type |
|---|---|---|---|---|---|---|---|
| `image_01` | `event_253` | `user_03` | `salary` | August 2019 net salary | **4,365,000.00** | IDR | Official Payslip (Net Pay) |
| `image_02` | `event_1442` | `user_16` | `rent` | Outstanding rent balance | **100,000.00** | INR | Rent Receipt (Balance Due) |
| `image_03` | `event_1545` | `user_17` | `groceries` | Bulk groceries and pantry purchase | **41,272.00** | INR | Retail Grocery Invoice |
| `image_04` | `event_1700` | `user_19` | `groceries` | Delivered grocery order | **2,854.00** | INR | App Order Summary (Item Bill) |
| `image_05` | `event_1786` | `user_20` | `utilities` | Outstanding telecom bill | **704.05** | INR | Telecom Utility Bill (Amount Due) |
| `image_06` | `event_3051` | `user_33` | `groceries` | Grocery tax invoice | **1,995.00** | INR | Quick-Commerce Tax Invoice |
| `image_07` | `event_3231` | `user_35` | `dining` | Restaurant tax invoice | **8,528.00** | INR | Restaurant Bill (Grand Total) |
| `image_08` | `event_4535` | `user_48` | `housing` | Property maintenance invoice | **15,339.00** | INR | Maintenance Receipt (Total Received) |
| `image_09` | `event_5170` | `user_55` | `utilities` | Water bill due | **723.00** | INR | Water Board Receipt |
| `image_10` | `event_6033` | `user_64` | `groceries` | Large grocery tax invoice | **79,679.26** | INR | Supermarket Tax Invoice |
| `image_11` | `event_6859` | `user_73` | `healthcare` | Hospital bill payable | **3,650.00** | INR | Hospital Provisional Bill |
| `image_12` | `event_7307` | `user_78` | `transport` | Taxi fare | **33.50** | USD | Taxi Service Receipt |
| `image_13` | `event_7941` | `user_84` | `shopping` | Tote bag order | **2,298.00** | INR | E-Commerce Order Confirmation |
| `image_14` | `event_9421` | `user_101` | `healthcare` | Pharmacy purchase | **4,543.00** | INR | Pharmacy Cash Bill |
| `image_15` | `event_9806` | `user_105` | `transport` | Airline ticket purchase | **9,968.00** | INR | Airline Electronic Tax Invoice |
| `image_16` | `event_10521` | `user_113` | `transport` | EV charging wallet payment | **393.22** | INR | EV Charging Session Invoice |

---

## 5. Recurring Expense & Income Patterns

Historical events span 6 months prior to `request_date`. Across users, recurring cash flows exhibit predictable cadence:
1. **Salary (`income:salary`)**:
   - Monthly frequency, predominantly settling on day **15** (or occasionally 20, 23, 24).
   - Confirmed future salary is listed as `status: scheduled`.
2. **Fixed Living Commitments**:
   - **Rent (`expense:rent`)**: Day 1, 2, or 3 of each calendar month.
   - **Utilities (`expense:utilities`)**: Days 5–7 of each month.
   - **Debt Payments (`debt_payment:debt_repayment`)**: Days 10–11 of each month.
   - **Subscriptions (`subscription:*`)**: Streaming, music, gym, delivery, cloud storage; fixed monthly amounts on identical days.
3. **Variable Living Expenses**:
   - **Groceries (`expense:groceries`)**: Weekly cadence (every ~7 days) with minor variance.
   - **Transport (`expense:transport`)**: Weekly/bi-weekly commuter passes and fuel refills.
   - **Dining & Shopping**: Discretionary flexible occurrences.

---

## 6. Message Categories & Reconstruction Rules

Inspection of 215 messages reveals specific semantics (in English and Indonesian):
1. **Salary Modification**: e.g. `message_01` increases monthly salary to IDR 42,750,000; `message_06` reduces next salary to EUR 1,422.85 due to unpaid leave; `message_04` sets temporary pay to EUR 1,037.52.
2. **Payday Date Shift**: e.g. `message_05` updates confirmed salary date to 2024-09-23.
3. **Contract / Employment Termination**: e.g. `message_09` notes seasonal contract ended with no renewal confirmed (future salary ceases).
4. **Unconfirmed Bonuses / Commissions**: e.g. `message_03`, `message_08` state bonuses/commissions are pending review; do NOT count as cash.
5. **Pending Payouts / Prizes / Lawsuits**: e.g. `message_07`, `message_16` state prize claims or gig payouts are in processing; do NOT count until settled.
6. **Failed Transaction Re-attempt**: e.g. `message_69`, `message_179`, `message_198`, `message_201` notify that a failed debit is still open and another debit will be attempted.
7. **Disputed Card Charges**: e.g. `message_106`, `message_121` state reversals are under investigation and have not posted yet.
8. **Internal Account Transfers**: e.g. `message_13` explains matching debit and credit were an internal transfer between user accounts.

---

## 7. Payment Option Structures & Plan Ranking

### Structure in `request_payment_options.csv`
- Each request provides between 2 and 4 options.
- `payment_method`: either `full_payment` (1 payment, 0 fee) or `installments` (2 to 24 payments, with financing fee).
- `financing_fee`: positive fee that increases `total_payable_amount`.

### Tie-Breaker Ranking Rules (Strict Specification)
When multiple eligible plans are verified safe by the 90-day simulation:
1. **Complete by Deadline**: Plan final payment date \(\le\) `desired_completion_date`.
2. **Spending Changes**: Zero spending changes ranked above plans requiring adjustments.
3. **Minimize Total Paid**: Lowest total cost (favoring 0-fee full payment over fee-bearing installments).
4. **Earlier Start Date**: Earliest first payment date.
5. **Fewer Payments**: Smaller payment count (e.g. 1 payment vs 3 vs 6).
6. **Lowest `payment_option_id`**: Final deterministic tie-breaker.

---

## 8. Currency Rules

- All financial calculations, comparisons, safety forecasts, and outputs are conducted in the user's `home_currency`.
- Foreign currency events are converted using `exchange_rates.csv` matched on `(settlement_date, from_currency, home_currency)`.
- Live or external market exchange rates are strictly prohibited.

---

## 9. Critical Edge Cases & Failure Modes

1. **Preference Over Financial Capacity**:
   - In `request_12`, the user had ample cash to pay `full_payment` on day 1 (`Safe = 65,164`, `Req = 65,164`), but `payment_methods_user_will_consider` was `partial_payment|installments`. The agent MUST recommend `installments`, while recording `earliest_date_for_full_payment = 2026-04-05`.
2. **Partial Payment Rules**:
   - Permitted ONLY when: `allows_partial_payment == true`, user considers `partial_payment`, `0 < amount_safe_to_pay < requested_amount`, and `earliest_date_for_full_payment <= desired_completion_date`.
   - Exactly two payments: `request_date:amount_safe_to_pay` and `earliest_date_for_full_payment:(requested_amount - amount_safe_to_pay)`.
3. **Spending Changes Boundaries**:
   - Maximum 3 changes separated by `|`.
   - Cannot stop and reduce the same event.
   - Can only modify events in categories listed in user's `expense_categories_user_is_willing_to_stop` and `expense_categories_user_is_willing_to_reduce`.
   - Must NEVER modify categories listed in `expense_categories_to_protect`.
   - `reduce_to` amount cannot fall below `minimum_allowed_amount`.
4. **Untrusted Instructions**:
   - Message texts containing prompt injections or instructions to bypass minimum balance must be ignored; only objective financial updates (dates, amounts, employment status) are extracted.
5. **No Negative Safe Amounts**:
   - `amount_safe_to_pay` is bounded: \(0 \le \text{amount\_safe\_to\_pay} \le \text{requested\_amount}\).

---

## 10. Implementation Risks & Mitigation Strategy

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Floating-point rounding drifts** | Discrepancy in installment sum or minimum balance check | Use `round(val, 2)` for EUR/USD/ZAR and integer rounding for INR/IDR where appropriate, with consistent decimal precision. |
| **Missing salary updates from messages** | Under-forecasting or over-forecasting cash inflows | Implement deterministic regex and semantic extractor in `evidence.py` to capture salary amounts and date changes. |
| **Counting unconfirmed credits** | Recommending unsafe purchases based on phantom funds | Filter strictly: ignore all pending credits, bonuses, and unconfirmed prizes. |
| **Ignoring bank retry notices** | Underestimating pending liabilities | Check messages for failed debits marked for re-attempt and maintain them as liabilities. |
| **Non-conforming output format** | Automated grading failure | Implement a strict pre-submission schema and bounds validator on `output.csv`. |
