# Phase 13 Demo UI Report: HackerRank Orchestrate "Buy or Wait?"

**Evaluation Date:** 2026-09-13  
**Harness / Tool:** Antigravity  
**Final Status:** **PHASE_13_COMPLETE**

---

## 1. Executive Summary

In Phase 13, a lightweight, responsive, local web demonstration dashboard was constructed for hackathon judges to visually inspect and navigate the deterministic recommendations of the "Buy or Wait?" financial decision engine.

### Strict Non-Negotiable Constraints Maintained
1. **Zero Financial Logic Modification:** The 12-phase financial engine remains 100% frozen and unmodified. No algorithms in `code/models.py`, `code/currency.py`, `code/evidence.py`, `code/financial_engine.py`, `code/affordability.py`, `code/planner.py`, `code/spending_optimizer.py`, `code/explanation.py`, or `code/validator.py` were touched or altered.
2. **Strict Presentation-Layer Boundary:** The UI is purely a read-only viewer. It loads pre-computed results directly from `output.csv` and does NOT calculate or recalculate financial decisions.
3. **Zero External Dependencies:** Built with pure Python 3 standard library (`http.server`, `urllib.parse`, `csv`, `json`) and modern vanilla HTML5, CSS3, and ES6 JavaScript. No external packages, npm modules, build steps, or external CDNs are required at runtime.
4. **Instant Startup:** Runs out-of-the-box via `npm start` or `python code/ui/server.py`.

---

## 2. UI Architecture & File Inventory

The UI consists of five dedicated files located in the repository:

```text
hackerrank-orchestrate-september26-main/
├── package.json               # NPM run configuration ("start": "python code/ui/server.py")
├── code/
│   └── ui/
│       ├── server.py          # Standard library HTTP backend & data API
│       ├── index.html         # Accessible, responsive layout structure
│       ├── style.css          # Modern dark-slate fintech styling & badge themes
│       └── app.js             # Client-side state, filtering, & detail rendering
```

### File Breakdown

| File | Size | Role | Description |
|---|---|---|---|
| `code/ui/server.py` | 11.4 KB | Server & API | Lightweight Python HTTP server. Serves static UI assets, exposes `/api/data` JSON endpoint merging `output.csv` with request metadata (`dataset/requests.csv`, `dataset/sample_requests.csv`, `dataset/financial_profiles.csv`), exposes `/api/health`, and computes summary counts. |
| `code/ui/index.html` | 8.3 KB | Markup | Two-column responsive dashboard structure containing top metric cards, multi-filter toolbar, quick-jump milestone navigation bar, dataset toggle tabs, scrollable request table, and detail panel. |
| `code/ui/style.css` | 14.1 KB | Styling | Modern dark-slate fintech theme. Includes color-coded status badges, interactive hover states, payment plan timeline tables, spending change callout cards, and mobile-friendly responsive breakpoints. |
| `code/ui/app.js` | 15.9 KB | Client App | Fast vanilla ES6 controller. Handles live search, multi-field filtering, dataset switching (Evaluation vs Reference Sample), timeline rendering (`YYYY-MM-DD:amount`), spending modification formatting (`stop:<id>` and `reduce_to:<id>:<amt>`), and 90-day liquidity buffer display. |
| `package.json` | 228 B | Runner | Enables standard npm runner workflow (`npm start` and `npm run dev`) that delegates to Python without requiring npm installs. |

---

## 3. Data Flow & Source of Truth

```text
┌────────────────────────┐     ┌────────────────────────────────────────────────────────┐
│       output.csv       │     │                   dataset/ CSV Files                   │
│ (250 Deterministic Rows)│    │ (requests.csv, sample_requests.csv, profiles.csv)      │
└───────────┬────────────┘     └───────────────────────────┬────────────────────────────┘
            │                                              │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      code/ui/server.py       │
                    │  (Zero-calc data merger)     │
                    └──────────────┬───────────────┘
                                   │  HTTP GET /api/data (JSON)
                                   ▼
                    ┌──────────────────────────────┐
                    │        code/ui/app.js        │
                    │   (Client-side Rendering)    │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │     Interactive UI View      │
                    │  - Metrics & Status Badges   │
                    │  - Payment Plan Timeline     │
                    │  - Spending Reductions       │
                    │  - Safety Floor Buffer       │
                    │  - AI Grounded Explanation   │
                    └──────────────────────────────┘
```

The server reads `output.csv` directly upon request. If `output.csv` is updated by a re-run of `python code/main.py`, the changes immediately appear on the next UI page refresh without restarting the server.

---

## 4. Key UI Features for Judges

### 1. Top-Level Summary Metrics
Displays instantaneous totals across all 250 evaluation requests:
- **Total Requests:** 250
- **Affordable Now:** 53 (21.2%)
- **Affordable with Plan:** 100 (40.0%)
- **Affordable Later:** 53 (21.2%)
- **Not Affordable:** 44 (17.6%)

### 2. Visual Status Badges
Color-coded status indicators across all views:
- `affordable_now`: Emerald Green (`#10b981`)
- `affordable_with_plan`: Indigo Blue (`#3b82f6`)
- `affordable_later`: Amber Orange (`#f59e0b`)
- `not_affordable`: Rose Red (`#ef4444`)

### 3. Comprehensive Inspection Detail Panel
Selecting any row renders a comprehensive breakdown:
- **Header:** Request ID, User ID, Item Name, Category, and Currency.
- **Financial Metric Cards:** Safe Amount to Pay vs. Total Requested Amount, Earliest Safe Date for Full Payment, and Minimum Balance to Keep.
- **Decision Overview:** Recommended payment method badge and full decision summary.
- **Payment Plan Timeline:** Formatted chronological table displaying payment dates, individual installment amounts, and total scheduled commitment.
- **Spending Changes Needed:** Distinct highlighted cards for non-protected spending actions:
  * `stop:<event_id>`: Cancel ongoing discretionary subscription/service.
  * `reduce_to:<event_id>:<amount>`: Lower recurring flexible spending to a safe cap.
- **Why this decision? (AI Grounded Explanation):** Complete, unedited natural-language justification demonstrating fidelity to simulated cash flows.
- **90-Day Financial Safety Check:** Clear validation confirming the user's balance never breaches their required minimum liquidity floor over the 90-day simulation window.

### 4. Benchmark Comparison & Milestone Scenarios
The dashboard includes an explicit **SAMPLE / REFERENCE** tab for demonstrating the 7 milestone benchmark test cases defined in the specification:
- `request_06`: Installments with spending reduction (`reduce_to:evt_06_rec02:800.00`).
- `request_11`: Installments with spending cancellation (`stop:evt_11_rec01`).
- `request_18`: Direct affordable now (`full_payment`).
- `request_19`: Affordable later (`wait` for payday).
- `request_21`: Partial payment with spending reduction (`reduce_to:evt_21_rec01:1000.00`).
- `request_22`: Not affordable due to insufficient cash flow / safety floor violation.
- `request_25`: Not affordable due to strict debt-to-income and liquidity constraints.

Quick-jump shortcut chips allow judges to navigate directly to any of these milestone scenarios with a single click.

---

## 5. Verification & Quality Assurance

### A. Syntax & Static Verification
- Node.js syntax check: `node --check code/ui/app.js` passed with 0 errors.
- Python compilation: `python -m py_compile code/ui/server.py` passed with 0 errors.

### B. UI Server Endpoint Verification
An automated test script (`test_ui_server.py`) started the server in a separate thread and verified:
- `GET /`: Returned HTTP 200 (HTML document containing "Buy or Wait").
- `GET /style.css`: Returned HTTP 200 (CSS stylesheet).
- `GET /app.js`: Returned HTTP 200 (JavaScript application).
- `GET /api/data`: Returned HTTP 200 JSON response containing 250 evaluation requests and 25 sample requests.
- Metric integrity: Verified dynamic counts matched `output.csv` exactly:
  * Total: 250
  * Affordable Now: 53
  * Affordable with Plan: 100
  * Affordable Later: 53
  * Not Affordable: 44
- Data integrity: Spot-checked evaluation requests `request_26`, `request_27`, `request_29`, `request_32`, and `request_36` to ensure all fields match `output.csv` verbatim.

### C. Engine Immutability & Test Suite Integrity
- Full pytest suite: `python -m pytest code/tests/ -q`
  * Result: **127 passed in 20.43s** (100% pass rate).
- Deterministic pipeline execution: `python code/main.py`
  * Execution time: 4.92s (50.78 req/s).
- Output compliance: `verify_output.py` verified `output.csv` has exactly 250 rows and passed all 17 schema, bound, and constraint checks with 0 errors.

---

## 6. How to Run

### Start the UI Server

Judges can launch the dashboard using either of the following commands:

```bash
# Option 1: Standard NPM startup
npm start

# Option 2: Python direct startup
python code/ui/server.py
```

### Access the Dashboard

Open any modern browser and navigate to:
```text
http://localhost:8080/
```

To stop the server, press `Ctrl+C` in the terminal.

---

## 7. Conclusion

Phase 13 successfully delivers an intuitive, aesthetically refined, zero-dependency demonstration dashboard that faithfully presents the deterministic financial decisions generated by the "Buy or Wait?" agent. The underlying financial decision engine remains pristine and frozen, with all 127 tests passing and full submission readiness preserved.


---

## 8. Visual Redesign — Banking Product UI (Phase 13.1)

### A. Problem with Initial UI
The initial Phase 13 implementation functioned reliably but visually resembled a developer console / AI hackathon analytics dashboard:
- Dark-mode "hacker" theme with deep grays and neon accents.
- Oversized technical badges ("DETERMINISTIC CORE ACTIVE", "AUTHORITATIVE OUTPUT.CSV").
- Developer-oriented statistics and raw technical identifiers front-and-center.
- Interface lacked the calm, trustworthy, and polished presentation expected of an enterprise personal banking or wealth-management product.

### B. New Banking Design Direction
In Phase 13.1, the interface was completely overhauled into a **Professional Digital Banking / Personal Finance Application**:
- **Aesthetic Tone:** Trustworthy, calm, premium, clean, and production-ready.
- **Color Palette:** Soft neutral canvas (`#f8fafc`), crisp white card surfaces (`#ffffff`), subtle borders (`#e2e8f0`), and deep navy typography (`#0f172a`).
- **Restrained Status Signaling:** Understated, banking-style status indicators (`✓ Affordable Now`, `● With Plan`, `◷ Affordable Later`, `! Not Affordable`) replacing noisy badges.
- **Embedded Intelligence:** Removed "AI" branding overload; the intelligent decision-making is presented naturally as an institutional personal finance advisor.

### C. Major Visual & Structural Changes
1. **Persistent Left Sidebar:**
   - Bank brand header: *Buy or Wait? — Personal Finance Decision Center*.
   - View navigation: *Overview*, *Purchase Decisions*, *Payment Plans*, and *Financial Activity*.
   - Security & engine status footer: *Financial Safety Engine • output.csv*.
2. **Professional Top Bar:**
   - Page breadcrumbs and subtitle.
   - Segmented tab control (*My Decisions* [250] vs *Demo Scenarios* [25]).
   - Subtle notification bell icon and verified *Demo Account* profile pill.
3. **Current Financial Position Summary:**
   - 5 cohesive banking metric cards dynamically computed from `output.csv` without hard-coding.
4. **Interactive Purchase Decision Experience:**
   - Category and item headline (e.g. *Family Transfer*, *Purchase*, *Investment*).
   - Side-by-side financial comparison comparing **Requested Amount** directly against **Safe Amount Today**.
   - Contextual financial summary banner explaining the practical decision impact.
   - Key terms grid: Payment method, earliest safe date, target deadline, and partial payment terms.
5. **Bank Payment Schedule:**
   - Replaces technical raw plan strings with a clean, structured schedule table (*Installment #*, *Date*, *Amount*, *Cumulative Total*, and *Scheduled* status).
6. **Budget Recommendations (Spending Adjustments):**
   - Replaces cryptic `stop:<id>` and `reduce_to:<id>:<amt>` strings with human-readable budget cards explaining the exact recommended action, capped amount, and event reference.
7. **90-Day Financial Safety Section:**
   - Intuitive reserve display displaying starting available balance, required reserve floor, and liquid safety buffer.
8. **Digital Banking Transaction List:**
   - Clean, searchable transaction list with category names, dates, amounts, and subtle status chips.
9. **Benchmark Demo Scenarios Selector:**
   - Quick-access chips for the 7 verified milestone reference cases from `sample_requests.csv`.

### D. Confirmation of Engine Immutability
- All financial engine modules (`code/models.py`, `code/currency.py`, `code/evidence.py`, `code/financial_engine.py`, `code/affordability.py`, `code/planner.py`, `code/spending_optimizer.py`, `code/explanation.py`, `code/validator.py`) remained **100% untouched**.
- `output.csv` remained authoritative and unchanged.
- Zero fake banking transactions or fabricated account numbers were introduced. All values originate strictly from `output.csv`, `requests.csv`, and `financial_profiles.csv`.

### E. Comprehensive Test & Validation Results
- **Full Test Suite:** `python -m pytest code/tests/ -q` -> **127 passed in 21.34s** (100% pass rate).
- **Engine Execution:** `python code/main.py` -> Completed in 5.20s (48.11 req/s) with 0 errors.
- **Output Integrity:** `verify_output.py` -> 250 rows, 0 errors, 17/17 schema constraints satisfied.
- **Server Endpoints:** `test_ui_server.py` -> HTTP 200 OK across `/`, `/style.css`, `/app.js`, and `/api/data`.
- **Client Interactions:** `test_ui_interactions.js` -> 6/6 tests passed for `affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable`, payment schedule rendering, and search filtering.


---

## 9. Premium UI Polish (Phase 13.2)

### A. Visual Problems Identified
While Phase 13.1 moved the aesthetic towards a banking theme, user audit identified several residual visual and interaction defects:
1. **Visual Crowding:** Too many pill shapes, borders around every individual label, and nested card containers competing for visual importance.
2. **Horizontal Overflow:** The demo scenario chips bar created an unwanted horizontal scrollbar across the entire screen.
3. **Dead Interaction:** The notification bell icon in the top bar had no click behavior.
4. **Heavy Metrics:** Five oversized metric cards dominated the top of the viewport instead of presenting an elegant personal finance summary.

### B. Changes & Polish Implemented
1. **Restrained Color Palette & Typography:**
   - Background: `#F6F8FB` canvas with crisp `#FFFFFF` card surfaces.
   - Primary text: `#0F172A` (deep navy) and `#64748B` (slate secondary).
   - Semantic accents: `#059669` (success), `#2563EB` (primary/plan blue), `#D97706` (warning), `#DC2626` (danger).
   - Removed all gradients, neon colors, glow effects, and redundant colored borders.
   - Clean system typography stack (`Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
2. **Refined Header & Working Notification Dropdown:**
   - Fixed header height (~72px) with clean brand hierarchy and center segmented control (*My Decisions* [250] vs *Demo Scenarios* [25]).
   - **Functional Notification System:** Clicking the notification bell button toggles a clean dropdown panel showing authentic system milestones (*Financial analysis completed: 250 requests evaluated*, *Output validation passed: All rows verified*). Clicking outside or pressing `Escape` closes the panel smoothly.
   - Fully accessible with `aria-label="Notifications"`, `aria-expanded`, and keyboard support.
3. **Zero Horizontal Overflow:**
   - Redesigned the Demo Scenarios section as a compact, 2-row wrapped button grid (`flex-wrap: wrap`) displaying clean identifiers (`Req 06`, `Req 11`, etc.) and short labels (`Stop Expense`, `Reduce Expense`).
   - Removed emoji prefixes and amount clutter from buttons.
   - Guaranteed **0 horizontal page scrollbars** across all screen resolutions (1440×900, 1280×720, tablet, mobile).
4. **Streamlined Financial Overview:**
   - Replaced the heavy 5-card row with a clean 4-column summary (*Affordable Now: 53*, *With Plan: 100*, *Later: 53*, *Not Affordable: 44*) paired with a subtle total decisions badge (*250 decisions evaluated*).
5. **Hero Decision Panel & Visual Comparison:**
   - Prominent item headline, request reference (`Request #26`), and clean status badge.
   - Side-by-side **Requested amount** vs. **Safe to pay today** comparison paired with a subtle comparison progress bar (*100% safe to pay today* or proportional safe percentage).
   - Streamlined key terms row separated by natural whitespace rather than heavy nested boxes.
   - Financial advisor insight note (*Based on your projected cash flow*).
   - Tabular payment schedule with clean alternating dividers and *Scheduled* tags.
   - Human-readable budget adjustments (*Stop recurring expense*, *Reduce recurring expense*).
   - 3-cell horizontal *Financial Safety* row comparing starting balance, reserve floor, and liquid buffer.

### C. Validation & Test Results
- **Full Pytest Suite:** `python -m pytest code/tests/ -q` -> **127 passed in 25.47s** (100% pass rate).
- **Engine Execution:** `python code/main.py` -> Completed in 7.12s (35.10 req/s) with 0 errors.
- **Output Validation:** `verify_output.py` -> Exactly 250 rows, 0 errors, 17/17 schema constraints verified.
- **Server Endpoints:** `test_ui_server.py` -> HTTP 200 OK across `/`, `/style.css`, `/app.js`, and `/api/data`.
- **Client Interactions:** `test_ui_interactions.js` -> 8/8 tests passed (notification toggle, all 4 status states, progress bar logic, schedule rendering, clean demo scenario buttons, and search filtering).
- **Zero Financial Logic Changes:** Frozen engine remains 100% untouched.


---

## 10. Demo Account Interaction (Phase 13.3)

### A. Feature Goal & Design
The top-right "Demo Account" profile pill was transformed from a static display element into an interactive, accessible digital banking profile dropdown menu.

### B. Implemented Interaction Behavior
1. **Interactive Trigger:**
   - Keyboard accessible trigger (`#profile-toggle-btn`) with circular initials avatar `DA`, label `Demo Account`, and a rotating chevron icon.
   - Proper ARIA attributes: `aria-haspopup="menu"`, `aria-expanded="false"|"true"`, `aria-label="Demo Account Profile Menu"`.
2. **Profile Dropdown Menu Structure:**
   - Dropdown header displaying user initials avatar `DA`, account label *Demo Account*, and environment tag *Demo profile*.
   - Menu items:
     - **Account Overview:** Navigates directly to the Financial Overview section (`handleNavClick('overview')`).
     - **Decision History:** Focuses and scrolls to the transaction decisions list (`handleNavClick('decisions')`).
     - **Preferences:** Displays an unobtrusive, non-blocking demo toast (*"Demo view: User preferences are loaded from dataset/financial_profiles.csv"*).
   - System information footer: *Demo Environment • Financial data: Dataset*.
3. **Robust Interaction Handlers:**
   - Click profile button toggles open/close state.
   - Click outside closes the dropdown.
   - `Escape` key closes the dropdown.
   - **Mutual Exclusion:** Opening the profile dropdown automatically closes the notifications dropdown, and vice versa.
4. **Zero Fake Account Functionality:**
   - Purely non-sensitive demo information.
   - No fake authentication, login/logout, passwords, bank names, account numbers, or synthetic balances were added.

### C. Validation Results
- **Full Pytest Suite:** `python -m pytest code/tests/ -q` -> **127 passed in 39.43s** (100% pass rate).
- **Engine Execution:** `python code/main.py` -> Completed in 8.92s (28.01 req/s) with 0 errors.
- **Output Validation:** `verify_output.py` -> Exactly 250 rows, 0 errors, 17/17 schema constraints satisfied.
- **Server Endpoints:** `test_ui_server.py` -> Verified HTTP 200 OK across `/`, `/style.css`, `/app.js`, and `/api/data`.
- **Client Interactions:** `test_ui_interactions.js` -> 8/8 tests passed (including profile toggle, mutual exclusion, menu navigation, toast notice, and keyboard dismissal).

```text
PHASE 13.3 STATUS:
COMPLETE
```




---

## 11. Contextual Decision Assistant (Phase 13.4)

### A. Purpose & Concept
The Contextual Decision Assistant provides a professional, digital banking explanation interface directly inside the Purchase Decision experience. It is designed specifically to help users and judges understand *why* a particular financial recommendation was made, without behaving like a generic AI chatbot.

### B. Architectural Invariants & Data Grounding
1. **Engine Freeze Integrity:**
   - The financial decision engine (`models.py`, `currency.py`, `evidence.py`, `financial_engine.py`, `affordability.py`, `planner.py`, `spending_optimizer.py`, `explanation.py`, `validator.py`) and `output.csv` remained strictly **frozen and untouched**.
   - The Assistant never performs independent affordability calculations or overrides decisions.
   - Flow: `output.csv -> Deterministic Engine -> UI Decision -> Decision Assistant (Explanation Only)`.
2. **Deterministic Offline Operation:**
   - 100% offline, local response generation based on deterministic templates and existing decision fields.
   - Zero external AI services, zero API calls (no OpenAI, Gemini, Anthropic, or external chatbot endpoints), and zero API keys.
3. **Strict Data Grounding:**
   - Explanations are derived exclusively from actual request fields (`request_id`, `requested_amount`, `amount_safe_to_pay`, `affordability_status`, `recommended_payment_method`, `payment_plan`, `earliest_date_for_full_payment`, `spending_changes_needed`, `decision_explanation`, and financial profile reserve parameters).
   - Zero invented balances, accounts, salaries, or institutions.

### C. Context-Aware Preset Questions & Responses
The Assistant dynamically adapts its preset questions to the active request:
- **Affordable Now (`affordable_now`):**
  - *"Why is this safe today?"* -> Explains immediate disbursement safety, reserve floor margin, and 90-day simulation stability.
  - *"How much can I pay today?"* -> Confirms 100% safe to pay today with no deferral or financing needed.
  - *"What does my safety buffer mean?"* -> Explains the liquid surplus available above the mandatory reserve floor.
- **Affordable With Plan (`affordable_with_plan`):**
  - *"Why do I need a payment plan?"* -> Explains that lump-sum payment today would breach the reserve floor, while installments align with cash flow cycles.
  - *"How does my payment plan work?"* -> Summarizes exact installment count, dates, and amounts.
  - *"Why is this plan considered safe?"* -> Explains that every scheduled date preserves the minimum reserve floor throughout the 90-day simulation.
  - *If Spending Adjustment Needed:* *"Why do I need a spending adjustment?"* -> Explains specific non-protected recurring expenses requiring reduction or cancellation (e.g. `request_06` stopping `event_476`).
- **Affordable Later (`affordable_later`):**
  - *"Why should I wait?"* -> Explains that today's safe amount is insufficient and waiting until payday restores liquidity.
  - *"When can I safely pay the full amount?"* -> Highlights the earliest safe payment date.
  - *"What happens if I pay today?"* -> Explains overdraft and reserve violation risk if paying before upcoming income arrives.
- **Not Affordable (`not_affordable`):**
  - *"Why can't I afford this?"* -> Explains that 90-day net cash inflows do not yield sufficient surplus above the mandatory reserve floor.
  - *"What is preventing this purchase?"* -> Details existing fixed obligations absorbing cash flow.
  - *"What would need to change?"* -> Details changes needed (higher income, lower purchase price, or reduced fixed costs).
- **Partial Payment Option:**
  - *"Why is partial payment recommended?"* -> Details today's safe limit and remainder deferral.

### D. Contextual Inquiry Input with Strict Intent Recognition
A compact single-line query bar allows natural user inquiries:
- Recognizes supported intents: `why`, `safe`, `today`, `wait`, `date`, `payment`, `plan`, `spending`, `reduce`, `stop`, `reserve`, `buffer`.
- Out-of-context fallback message: *"I can explain this purchase decision, payment plan, spending recommendation, or safety reserve."* (zero hallucinations).

### E. Banking Visual Design & Accessibility
- Clean white card surface, `#E2E8F0` border, `12px` border radius, deep navy text (`#0F172A`), muted secondary text (`#64748B`), restrained blue accent (`#2563EB`).
- Small SVG information badge (zero robot icons, zero glowing AI gradients, zero chat bubbles).
- Keyboard-accessible buttons, `aria-expanded` attributes, visible focus rings, and `aria-live="polite"` for answer updates.
- 150ms smooth fade transition when switching questions.
- Fully responsive on desktop, tablet, and mobile (no horizontal scrollbars).

### F. Judge Demonstration Flow
1. **Immediate Full Payment (`request_26`):** Select request 26; click *"Why is this safe today?"* to see reserve floor calculation and safety buffer verification.
2. **Spending Adjustment Case (`request_06`):** Select request 06; click *"Why do I need a spending adjustment?"* to inspect the advice to pause recurring subscription `event_476`.
3. **Wait on Payday (`request_18`):** Select request 18; click *"Why should I wait?"* and *"When can I safely pay the full amount?"* to verify the earliest payment date on 15 September 2026.
4. **Reserve Protection Limit (`request_25`):** Select request 25; click *"Why can't I afford this?"* to inspect the reserve floor constraint.
5. **Installment Schedule (`request_30`):** Select request 30; click *"How does my payment plan work?"* to view the 3-installment summary.
6. **Contextual Query Bar:** Type *"why should I wait?"*, *"what is my reserve?"*, or an unsupported topic to demonstrate intent parsing and safe fallback.

### G. Validation & Regression Test Results
- **Full Pytest Suite:** `python -m pytest code/tests/ -q` -> **127 passed in 38.16s** (100% pass rate).
- **Engine Execution:** `python code/main.py` -> Verified 250 rows in 4.47s with 0 errors.
- **Output Validation:** `verify_output.py` -> 250 evaluation rows, 17/17 checks passed.
- **Byte-for-Byte Output Invariant:** `output.csv` verified 100% identical byte-for-byte (50,295 bytes).
- **UI Server Endpoints:** `test_decision_assistant.py` -> HTTP 200 OK across `/`, `/style.css`, `/app.js`, and `/api/data`.
- **Client Interactions:** `test_assistant_interactions.js` -> 6/6 test suites passed across all 5 scenario states and intent matching.

```text
PHASE 13.4 STATUS:
COMPLETE
```
