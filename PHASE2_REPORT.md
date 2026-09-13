# PHASE2_REPORT.md — Financial State Reconstruction

This report documents the implementation and verification of **Phase 2: Financial State Reconstruction** for the **Buy or Wait?** financial agent challenge.

---

## 1. Normalized Data Model

Implemented in `code/models.py`:

- **`UserProfile`**:
  - Encapsulates parsed user profile data: `user_id`, `home_currency`, `current_available_balance`, and `minimum_balance_to_keep`.
  - Parsed list collections for `financial_priorities`, `expense_categories_to_protect`, `expense_categories_user_is_willing_to_reduce`, `expense_categories_user_is_willing_to_stop`, and `payment_methods_user_will_consider`. List parsing safely handles pipe-separated (`|`), comma-separated (`,`), empty, or `"none"` strings.
  - `max_installment_months`: Integer or `None` if installments are not permitted.
- **`RequestItem`**:
  - Represents an expense evaluation request (`request_id`, `user_id`, `request_date`, `request_type`, `requested_amount`, `desired_completion_date`, `allows_partial_payment`, `request_text`).
- **`PaymentOption`**:
  - Encapsulates seller-provided installment offers from `request_payment_options.csv` with schedule terms, payment counts, frequency intervals, fees, and total payable amount.
- **`FinancialEvent`**:
  - Complete representation of a transaction or commitment:
    - Primary identifiers: `event_id`, `user_id`, `event_type`, `category`, `description`.
    - Monetary amounts: `amount` (in transaction currency) and `amount_home` (converted to user home currency).
    - Lifecycle and dates: `event_date`, `settlement_date`, `status`, `linked_event_id`.
    - Policy attributes: `flexibility`, `minimum_allowed_amount`.
    - Safety metadata: `is_cash_flow` (determines liquid cash relevance), `is_recurring`, and `source`.
- **`FinancialEvidence`**:
  - Normalized structure capturing grounded facts extracted from messages or images (`evidence_id`, `user_id`, `event_id`, `evidence_type`, `field`, `old_value`, `new_value`, `effective_date`, `source`, `confidence`).
- **`NormalizedFinancialState`**:
  - Aggregate state per user containing: `user`, `request`, `events`, `active_pending_debits`, `confirmed_future_income`, `recurring_expenses`, `evidence_applied`, and `payment_options`.

---

## 2. Event Inclusion and Exclusion Rules

Implemented in `code/evidence.py`:

| Status | Direction | Event Type | Cash Flow Eligibility (`is_cash_flow`) | Reasoning |
|---|---|---|---|---|
| `settled` | `debit` / `credit` | Any | **True** | Completed historical transaction affecting balance. |
| `pending` | `debit` | `expense` / `debt_payment` | **True** | Authorized charge; represents an active obligation reserved against available balance. |
| `pending` | `credit` | `refund` / `income` | **False** | Unconfirmed pending credit; forbidden from being counted as cash until settlement. |
| `scheduled` | `credit` | `salary` | **True** (if contract active) | Confirmed upcoming salary credited on settlement date (subject to message updates). |
| `scheduled` | `credit` | Non-salary | **False** | Unconfirmed speculative future credit. |
| `scheduled` | `debit` | `expense` / `rent` | **True** | Fixed scheduled commitment. |
| `cancelled` | Any | Any | **False** | Cancelled transaction with zero cash impact. |
| `failed` | `debit` | Any | **False** (Default) / **True** (with retry notice) | Default failed debits are ignored. If bank message confirms debit retry is active, event remains an active liability (`status = 'pending'`). |
| `unrealized`| `non_cash` | `investment_valuation` | **False** | Unrealized portfolio fluctuation; cannot be spent. |

---

## 3. Transaction Lifecycle Resolution Rules

1. **Refunds Linked to Expenses** (`linked_event_id`):
   - Settled refunds (`refund:settled`) counteract the original expense in historical records.
   - Pending refunds (`refund:pending`) have `is_cash_flow = False`, ensuring prospective refunds never prematurely inflate available cash.
2. **Cancelled Retries**:
   - Cancelled attempts (`status: cancelled`) have `is_cash_flow = False`. Retried settled events (`status: settled`) have `is_cash_flow = True`. Double-counting is completely avoided.
3. **Investment Valuation**:
   - `investment_valuation` events linked to `investment_purchase` events are marked `is_cash_flow = False`.
4. **Resolution Precedence**:
   1. Explicit cancellation or amendment takes absolute precedence.
   2. Settled records override estimates/forecasts.
   3. Financially safer interpretation is strictly applied in ambiguity.

---

## 4. Message Resolution Rules (Deterministic Fact Extraction)

Messages in `messages.csv` are treated as untrusted evidence. Prompt injection attempts or instructions to bypass minimum balances are completely ignored. Extraction strictly parses financial facts using deterministic semantic matchers:

1. **Salary Adjustments**:
   - Matches multilingual salary changes (e.g. `naik menjadi IDR 42750000`, `temporary monthly pay is EUR 1037.52`, `reduced to EUR 1422.85`).
   - Updates `amount` and `amount_home` of upcoming scheduled salary.
2. **Payday Date Changes**:
   - Matches date adjustments (e.g. `confirmed salary is now expected on 2024-09-23`).
   - Adjusts `settlement_date` of upcoming salary.
3. **Contract / Employment Termination**:
   - Matches termination notifications (e.g. `seasonal contract has ended`).
   - Sets `is_cash_flow = False` on future scheduled salary, preventing phantom income.
4. **Rent Increases**:
   - Matches lease renewal notices (e.g. `increases monthly rent by 12%`).
   - Scales future rent payments by the specified percentage multiplier.
5. **Failed Debit Retries**:
   - Matches bank notifications stating *"The bill is still outstanding and another debit will be attempted"*.
   - Retains the failed event as an active pending liability (`status = 'pending'`).
6. **Internal Transfers**:
   - Clarifies matching debit and credit pairs as internal account movements with zero net impact on total funds.
7. **Unconfirmed Credits**:
   - Explicitly ignores pending bonuses, quarterly performance reviews, and prize processing.

---

## 5. Image Resolution Rules (All 16 Grounded)

All 16 blank-amount rows in `financial_events.csv` map 1:1 to images in `dataset/media/images/`:

| Image ID | Event ID | User ID | Category | Extracted Amount | Verified Source Document |
|---|---|---|---|---|---|
| `image_01` | `event_253` | `user_03` | `salary` | **4,365,000.00 IDR** | Official Pay Slip Net Pay |
| `image_02` | `event_1442` | `user_16` | `rent` | **100,000.00 INR** | House Rent Receipt Balance Due |
| `image_03` | `event_1545` | `user_17` | `groceries` | **41,272.00 INR** | Retail Grocery Tax Invoice |
| `image_04` | `event_1700` | `user_19` | `groceries` | **2,854.00 INR** | Grocery Delivery Item Bill |
| `image_05` | `event_1786` | `user_20` | `utilities` | **704.05 INR** | Telecom Utility Bill Amount Due |
| `image_06` | `event_3051` | `user_33` | `groceries` | **1,995.00 INR** | Quick-Commerce Tax Invoice Total |
| `image_07` | `event_3231` | `user_35` | `dining` | **8,528.00 INR** | Restaurant Tax Invoice Grand Total |
| `image_08` | `event_4535` | `user_48` | `housing` | **15,339.00 INR** | Society Maintenance Receipt Total |
| `image_09` | `event_5170` | `user_55` | `utilities` | **723.00 INR** | Water Bill Payment Receipt Total |
| `image_10` | `event_6033` | `user_64` | `groceries` | **79,679.26 INR** | Supermarket Invoice Balance Due |
| `image_11` | `event_6859` | `user_73` | `healthcare` | **3,650.00 INR** | Hospital Provisional Bill Total |
| `image_12` | `event_7307` | `user_78` | `transport` | **33.50 USD** | Taxi Fare Receipt Total |
| `image_13` | `event_7941` | `user_84` | `shopping` | **2,298.00 INR** | E-Commerce Order Confirmation Total |
| `image_14` | `event_9421` | `user_101` | `healthcare` | **4,543.00 INR** | Pharmacy Cash Bill Total |
| `image_15` | `event_9806` | `user_105` | `transport` | **9,968.00 INR** | Flight Electronic Tax Invoice Total |
| `image_16` | `event_10521` | `user_113` | `transport` | **393.22 INR** | EV Charging Invoice Total |

---

## 6. Currency Conversion Rules

Implemented in `code/currency.py`:
- Converts foreign currency amounts to the user's `home_currency` using strictly dated rates in `exchange_rates.csv`.
- Rate matching uses `(rate_date, from_currency, to_currency)`.
- If `from_currency == to_currency`, returns exact amount without conversion.
- If direct rate is present, multiplies by `rate`. If inverse rate is present, divides by inverse rate.
- If a conversion pair cannot be resolved, raises `ValueError` immediately rather than guessing or using live market rates.
- All 140 foreign currency events in `financial_events.csv` were verified to have an exact date and pair match in `exchange_rates.csv`.

---

## 7. Known Edge Cases Handled

1. **Zero Cash Effect on Failed & Cancelled Events**:
   - Explicitly ensures cancelled and failed transactions are not deducted from available cash.
2. **Retry Liabilities**:
   - Detects bank notifications regarding failed debits that remain active obligations and will be retried.
3. **Trailing Punctuation in Messages**:
   - Message parser handles numbers ending in full stops or trailing commas (e.g. `EUR 1037.52.`).
4. **Multilingual Phrasing**:
   - Deterministic extraction accommodates both English and Indonesian sentence structures for payroll and banking notifications.
5. **Internal Account Movements**:
   - Flags matching debit and credit transfers between user accounts as non-cash-flow to prevent artificial income creation.

---

## 8. Test Execution & Diagnostic Results

The test suite in `code/tests/test_evidence.py` was executed:

```bash
python code/tests/test_evidence.py
```

### Results
- `test_01_profiles_loaded`: **PASS** (all 275 profiles loaded with sanitized list fields)
- `test_02_requests_loaded_and_mapped`: **PASS** (all 250 evaluation requests and 25 sample requests mapped 1:1 to users)
- `test_03_payment_options_loaded`: **PASS** (all 790 payment options across 275 requests loaded)
- `test_04_image_amounts_resolved`: **PASS** (all 16 blank-amount events resolved to verified image values)
- `test_05_event_status_rules`: **PASS** (cancelled, failed, unrealized, and pending credits excluded from cash flow; active retries preserved)
- `test_06_currency_conversion`: **PASS** (dated conversions accurate; missing rates fail loudly)
- `test_07_message_evidence_extraction`: **PASS** (deterministic extraction of salary, date, contract, rent, and transfer facts)
- `test_08_full_state_construction_for_all_users`: **PASS** (normalized state built for all 275 users without exception)

**Summary: 8/8 tests passed in 0.582s (100% pass rate).**
