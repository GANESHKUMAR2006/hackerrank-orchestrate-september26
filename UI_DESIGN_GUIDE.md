# UI Design Guide: Buy or Wait? Financial Decision Center

**Product:** Buy or Wait? Personal Finance Decision Center  
**Target Audience:** Hackathon Judges & Financial End-Users  
**Design Philosophy:** Modern digital banking aesthetic — clean, calm, trustworthy, human, and production-ready.

---

## 1. Color System

The palette is strictly restrained to modern retail banking standards:

| Token | Hex Value | Role | Usage |
|---|---|---|---|
| `--bg-app` | `#F6F8FB` | Canvas | Application background canvas |
| `--bg-surface` | `#FFFFFF` | Primary Surface | Cards, sidebar, headers, panels |
| `--bg-subtle` | `#F1F5F9` | Muted Surface | Inputs, table headers, container backgrounds |
| `--bg-hover` | `#F8FAFC` | Hover Surface | Row hover states |
| `--text-main` | `#0F172A` | Primary Text | Headings, amounts, active labels (Deep Navy) |
| `--text-secondary`| `#64748B` | Secondary Text | Labels, subtitles, metadata |
| `--text-muted` | `#94A3B8` | Muted Text | Placeholders, captions |
| `--border-light` | `#E2E8F0` | Dividers | Card outlines, row borders |
| `--primary-blue` | `#2563EB` | Accent Blue | Brand accent, active tab highlights |
| `--success` | `#059669` | Safe / Now | Verified affordable status (`#ECFDF5` bg, `#A7F3D0` border) |
| `--plan-blue` | `#1E40AF` | Structured Plan | Financing status (`#EFF6FF` bg, `#BFDBFE` border) |
| `--warning` | `#D97706` | Wait / Reconsider | Wait for payday status (`#FFFBEB` bg, `#FDE68A` border) |
| `--danger` | `#DC2626` | Unsafe | Reserve limit status (`#FEF2F2` bg, `#FECACA` border) |

*Rules:*
- No neon colors.
- No gradients.
- No glowing card effects.
- No heavy colored borders. Color is used exclusively for decision indicators and semantic numbers.

---

## 2. Typography System

The interface uses modern system sans-serif typography. Financial amounts use high-legibility standard sans fonts (not monospaced) for optimal human readability.

- **Primary Font Stack:** `Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Monospace Stack:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace` (reserved strictly for technical event IDs and code snippets in details).

### Type Hierarchy
| Level | Font Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| **Page Title** | 20px–24px | 700 (Bold) | 1.2 | Header brand title |
| **Section Title** | 18px–20px | 700 (Bold) | 1.3 | "Financial Overview", "Purchase Decision" |
| **Card / Item Title** | 14px–16px | 600–700 | 1.3 | Item names, card headings |
| **Large Numbers** | 24px–26px | 700 (Bold) | 1.1 | Requested and safe amounts |
| **Body Text** | 14px | 400 (Regular) | 1.5 | Advisor explanations, descriptions |
| **Secondary Text** | 12px–13px | 500 (Medium) | 1.4 | Subtext, timestamps, captions |

---

## 3. Spacing & Grid System

Whitespace is used to structure content naturally without relying on heavy borders:
- **Base Grid:** 8px base increment (`8px`, `16px`, `24px`, `32px`).
- **Card Padding:** `24px` (1.5rem) on primary cards; `16px` on list headers.
- **Section Gaps:** `20px` to `24px` between major blocks.
- **Micro-Gaps:** `4px` to `8px` between icons, labels, and metadata.

---

## 4. Component Rules

### A. Header Bar (~72px)
- Brand and subtitle on the left.
- Center segmented control (*My Decisions* vs *Demo Scenarios*).
- Interactive notification button opening an accessible dropdown of real system milestones (*Financial analysis completed*, *Validation passed*).
- Clean verified profile pill (*Demo Account*).

### B. Persistent Left Sidebar
- Light navigation items with simple line icons.
- Active item styled with subtle blue background (`#EFF6FF`), blue icon, and dark text.
- Very subtle system indicator at bottom (*Decision Engine • 90-day liquidity protection*).

### C. Top Financial Overview
- Compact 4-column summary grid (*Affordable Now*, *With Plan*, *Later*, *Not Affordable*).
- Subtle total decisions badge (*250 decisions evaluated*).
- Clicking any card filters the transaction list immediately.

### D. Demo Scenarios Grid (Zero Overflow)
- 2-row wrapped compact button grid displaying `Req 06`, `Req 11`, etc., with clean sublabels.
- No emoji prefixes.
- Guaranteed zero horizontal window scrollbars.

### E. Transaction List
- Styled like online banking transaction history.
- Item title, date · request ID, amount, and subtle status badge.
- Selected row features a clean 3px blue left border and soft background wash.

### F. Hero Purchase Decision Experience
- **Item Headline & Reference:** Prominent category name, request ID, target date, and clean status badge.
- **Amount Comparison:** Side-by-side display of *Requested amount* vs. *Safe to pay today* with an integrated progress bar (*100% safe to pay today* or *Partial amount currently safe*).
- **Terms Grid:** 4-cell row separated by whitespace without individual boxes.
- **Advisor Quote Card:** Financial advisor insight note with subtle left blue accent line.
- **Payment Schedule:** Clean table with subtle dividers and *Scheduled* tags.
- **Budget Adjustments:** Actionable cards detailing non-protected expense reductions or cancellations.
- **Financial Safety:** 3 horizontal cells comparing starting balance, reserve floor, and liquid safety buffer.
- **Decision Details:** Collapsible native `<details>` drawer for audit review.

### G. Demo Account Profile Dropdown
- **Trigger Button:** Clickable `.profile-pill-btn` with chevron indicator, hover state, and `aria-expanded` toggle.
- **Interaction Mechanics:** Mutually exclusive with notification dropdown; dismisses on outside clicks or `Escape` key.
- **Header Profile Card:** Avatar circle (`DA`), `Demo Account` title, and `Demo profile` label.
- **Functional Navigation:**
  - *Account Overview*: Smooth-scrolls to the 4-column metric summary.
  - *Decision History*: Focuses and scrolls to the transaction history ledger.
  - *Preferences*: Triggers a floating toast explaining profile preferences are loaded directly from `dataset/financial_profiles.csv` without fake interactive forms.
- **Footer Metadata:** *Demo Environment • Financial data: Dataset* reassuring judges of dataset fidelity.

### H. Contextual Decision Assistant
- **Design Philosophy:** Clean digital banking inquiry panel, not a generic AI chatbot. Zero robot graphics, zero glowing gradients, zero chat bubbles.
- **Surface & Hierarchy:** White card surface (`#FFFFFF`), subtle `#E2E8F0` border, `12px` border radius, deep navy headline, and restrained blue icon badge.
- **Context-Aware Preset Questions:** Dynamically adapts based on status (`affordable_now`, `affordable_with_plan`, `affordable_later`, `not_affordable`, partial payment, and budget adjustments).
- **Preset Buttons (`.assistant-q-btn`):** `8px` radius, subtle background wash, active blue state, keyboard accessible with `aria-expanded`.
- **Inquiry Input Bar (`.assistant-query-bar`):** Single-line input with inline magnifying glass icon and dark `Ask` submit button. Supports deterministic keyword matching (`why`, `safe`, `today`, `wait`, `plan`, `spending`, `reserve`, `date`) and strict fallback notice (*"I can explain this purchase decision, payment plan, spending recommendation, or safety reserve."*).
- **Explanation Box (`.assistant-answer-box`):** Top border divider, uppercase topic badge, and smooth 150ms fade transition for explanation updates.
- **Zero Engine Modifications:** Strictly read-only presentation grounded exclusively in existing decision attributes.

---

## 5. Border Radii & Elevation

- **Cards:** `12px`
- **Buttons & Inputs:** `8px`
- **Pills:** `9999px` (strictly for status badges and segmented tabs)
- **Shadows:** Extremely subtle `0 1px 3px 0 rgba(15, 23, 42, 0.04)` (stable, grounded, trustworthy feel).

---

## 6. Judge Demonstration Walkthrough

1. **System Health & Overview:** Point out 250 evaluation requests processed deterministically; show the 4-column financial distribution.
2. **Immediate Full Payment (`request_26`):** Select first transaction; demonstrate 100% safe progress bar, liquid reserve buffer, and ask the Decision Assistant *"Why is this safe today?"*.
3. **Structured Financing Plan (`request_30`):** Demonstrate 3 equal monthly installments on the Payment Schedule table and ask *"How does my payment plan work?"*.
4. **Demo Scenarios:** Switch to *Demo Scenarios* tab; demonstrate:
   - `Req 06`: Stop expense recommendation and ask Decision Assistant *"Why do I need a spending adjustment?"*.
   - `Req 11`: Reduce expense recommendation.
   - `Req 18`: Wait for payday deferral and ask *"Why should I wait?"*.
   - `Req 19`: Partial payment schedule.
   - `Req 25`: Reserve protection denial and ask *"Why can't I afford this?"*.
5. **Contextual Inquiry Bar:** Type inquiries (e.g. *"why"*, *"what is my reserve?"*, or an unsupported topic) to demonstrate deterministic keyword intent parsing and fallback handling.
6. **Notifications & Search:** Click the notification bell to show verified system events; use the search bar to filter transactions in real time.
7. **Demo Account Profile Menu:** Click the top-right profile button to open the institutional account menu; demonstrate navigation to Overview and Decision History, and demonstrate the non-intrusive dataset preferences toast notification.


