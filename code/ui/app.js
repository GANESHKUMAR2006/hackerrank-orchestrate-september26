// Buy or Wait? — Premium Digital Banking & Personal Finance Application
// Phase 13.2 Polish: Functional interactions, notification dropdown, zero horizontal scroll, clean typography.
// Architectural Invariant: Read-Only presentation layer reading existing output.csv / API.

let allEvaluationRequests = [];
let allSampleRequests = [];
let currentTab = 'EVALUATION'; // 'EVALUATION' (My Decisions) or 'SAMPLE' (Demo Scenarios)
let activeFilter = 'ALL';
let searchQuery = '';
let selectedRequestId = null;

// Verified Milestone Scenarios from dataset/sample_requests.csv and output.csv
const DEMO_SCENARIOS = [
  { id: 'request_06', code: 'Req 06', label: 'Stop Expense', type: 'SAMPLE' },
  { id: 'request_11', code: 'Req 11', label: 'Reduce Expense', type: 'SAMPLE' },
  { id: 'request_18', code: 'Req 18', label: 'Wait for Payday', type: 'SAMPLE' },
  { id: 'request_19', code: 'Req 19', label: 'Partial Payment', type: 'SAMPLE' },
  { id: 'request_21', code: 'Req 21', label: 'Multi-Adjustment', type: 'SAMPLE' },
  { id: 'request_22', code: 'Req 22', label: 'Financing Plan', type: 'SAMPLE' },
  { id: 'request_25', code: 'Req 25', label: 'Reserve Limit', type: 'SAMPLE' },
  { id: 'request_26', code: 'Req 26', label: 'Family Transfer', type: 'EVALUATION' }
];

function formatMoney(amount, currency = '') {
  if (amount === null || amount === undefined || amount === '') return '0.00';
  const num = parseFloat(amount);
  if (isNaN(num)) return '0.00';
  const formatted = num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return currency ? `${currency} ${formatted}` : formatted;
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === 'none' || dateStr === 'N/A') return '';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const dt = new Date(parts[0], parts[1] - 1, parts[2]);
      return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }
  } catch (e) {}
  return dateStr;
}

function formatCategory(cat) {
  if (!cat) return 'Purchase';
  return cat
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function formatPaymentMethod(method) {
  switch (method) {
    case 'full_payment': return 'Full Payment';
    case 'installments': return 'Financing / Installments';
    case 'wait': return 'Wait (Pay on Payday)';
    case 'partial_payment': return 'Partial Payment';
    case 'not_recommended': return 'Not Recommended';
    default: return (method || '').replace(/_/g, ' ');
  }
}

function getStatusBadgeHtml(status) {
  switch (status) {
    case 'affordable_now':
      return '<span class="status-badge status-now">✓ Affordable Now</span>';
    case 'affordable_with_plan':
      return '<span class="status-badge status-plan">● With Plan</span>';
    case 'affordable_later':
      return '<span class="status-badge status-later">◷ Later</span>';
    case 'not_affordable':
      return '<span class="status-badge status-not">! Not Affordable</span>';
    default:
      return `<span class="status-badge">${status}</span>`;
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'affordable_now': return 'Affordable Now';
    case 'affordable_with_plan': return 'Affordable With Plan';
    case 'affordable_later': return 'Affordable Later';
    case 'not_affordable': return 'Not Affordable';
    default: return status;
  }
}

function getStatusSymbol(status) {
  switch (status) {
    case 'affordable_now': return '✓';
    case 'affordable_with_plan': return '●';
    case 'affordable_later': return '◷';
    case 'not_affordable': return '!';
    default: return '•';
  }
}

function getStatusCssClass(status) {
  switch (status) {
    case 'affordable_now': return 'status-now';
    case 'affordable_with_plan': return 'status-plan';
    case 'affordable_later': return 'status-later';
    case 'not_affordable': return 'status-not';
    default: return '';
  }
}

// --------------------------------------------------------------------------
// NOTIFICATION & PROFILE DROPDOWN INTERACTIONS
// --------------------------------------------------------------------------
function toggleNotifications(event) {
  if (event) event.stopPropagation();
  closeProfile();
  const dropdown = document.getElementById('notif-dropdown');
  const btn = document.getElementById('notif-toggle-btn');
  if (!dropdown) return;
  
  const isOpen = dropdown.classList.toggle('open');
  if (btn) btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

function closeNotifications() {
  const dropdown = document.getElementById('notif-dropdown');
  const btn = document.getElementById('notif-toggle-btn');
  if (dropdown && dropdown.classList.contains('open')) {
    dropdown.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
}

function toggleProfile(event) {
  if (event) event.stopPropagation();
  closeNotifications();
  const dropdown = document.getElementById('profile-dropdown');
  const btn = document.getElementById('profile-toggle-btn');
  if (!dropdown) return;

  const isOpen = dropdown.classList.toggle('open');
  if (btn) btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

function closeProfile() {
  const dropdown = document.getElementById('profile-dropdown');
  const btn = document.getElementById('profile-toggle-btn');
  if (dropdown && dropdown.classList.contains('open')) {
    dropdown.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
}

function handleProfileMenu(action) {
  closeProfile();
  if (action === 'overview') {
    handleNavClick('overview');
  } else if (action === 'decisions') {
    handleNavClick('decisions');
  } else if (action === 'preferences') {
    showToast('Demo view: User preferences are loaded from dataset/financial_profiles.csv');
  }
}

let toastTimeout = null;
function showToast(message) {
  const toast = document.getElementById('demo-toast');
  if (!toast) return;
  toast.innerText = message;
  toast.classList.add('show');
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}

// Global click & key listeners to close dropdowns
window.addEventListener('click', (e) => {
  const notifDropdown = document.getElementById('notif-dropdown');
  const notifBtn = document.getElementById('notif-toggle-btn');
  if (notifDropdown && notifDropdown.classList.contains('open')) {
    if (!notifDropdown.contains(e.target) && e.target !== notifBtn && !notifBtn.contains(e.target)) {
      closeNotifications();
    }
  }

  const profileDropdown = document.getElementById('profile-dropdown');
  const profileBtn = document.getElementById('profile-toggle-btn');
  if (profileDropdown && profileDropdown.classList.contains('open')) {
    if (!profileDropdown.contains(e.target) && e.target !== profileBtn && !profileBtn.contains(e.target)) {
      closeProfile();
    }
  }
});

window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeNotifications();
    closeProfile();
  }
});

// --------------------------------------------------------------------------
// DATA LOADING
// --------------------------------------------------------------------------
async function loadData() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
    const data = await res.json();

    allEvaluationRequests = data.evaluation_requests || [];
    allSampleRequests = data.sample_requests || [];

    renderSummary(data.summary);
    renderDemoScenariosGrid();

    // Default to the first request (request_26)
    if (allEvaluationRequests.length > 0) {
      selectedRequestId = allEvaluationRequests[0].request_id;
    }

    renderTransactionsList();
    renderDecisionHero();
  } catch (err) {
    console.error('Failed to load dataset:', err);
    document.getElementById('decision-item-name').innerText = 'Data connection error';
    document.getElementById('detail-explanation-text').innerText = 'Ensure python code/ui/server.py is running from repository root.';
  }
}

function renderSummary(summary) {
  if (!summary) return;
  const total = summary.total_evaluation_requests || 250;
  
  const totalBadge = document.getElementById('metric-total-badge');
  if (totalBadge) totalBadge.innerText = `${total} decisions evaluated`;

  const now = summary.affordable_now_count || 0;
  document.getElementById('metric-now').innerText = now;

  const plan = summary.affordable_with_plan_count || 0;
  document.getElementById('metric-plan').innerText = plan;

  const later = summary.affordable_later_count || 0;
  document.getElementById('metric-later').innerText = later;

  const notAff = summary.not_affordable_count || 0;
  document.getElementById('metric-not').innerText = notAff;

  document.getElementById('tab-eval-count').innerText = total;
  document.getElementById('tab-sample-count').innerText = allSampleRequests.length || 25;
}

// --------------------------------------------------------------------------
// DEMO SCENARIOS GRID (2-ROW WRAPPED COMPACT BUTTONS, ZERO OVERFLOW)
// --------------------------------------------------------------------------
function renderDemoScenariosGrid() {
  const container = document.getElementById('quickbar-scenarios');
  if (!container) return;
  container.innerHTML = '';

  DEMO_SCENARIOS.forEach(sc => {
    const btn = document.createElement('button');
    const isSelected = selectedRequestId === sc.id;
    btn.className = `demo-btn ${isSelected ? 'active' : ''}`;
    btn.innerHTML = `
      <span class="demo-btn-id">${sc.code}</span>
      <span class="demo-btn-label">${sc.label}</span>
    `;
    btn.onclick = () => {
      currentTab = sc.type;
      updateTabButtons();
      selectRequest(sc.id);
    };
    container.appendChild(btn);
  });
}

function updateTabButtons() {
  const evalTab = document.getElementById('tab-eval');
  const sampleTab = document.getElementById('tab-sample');
  if (evalTab) {
    evalTab.className = `mode-tab ${currentTab === 'EVALUATION' ? 'active' : ''}`;
    evalTab.setAttribute('aria-selected', currentTab === 'EVALUATION' ? 'true' : 'false');
  }
  if (sampleTab) {
    sampleTab.className = `mode-tab ${currentTab === 'SAMPLE' ? 'active' : ''}`;
    sampleTab.setAttribute('aria-selected', currentTab === 'SAMPLE' ? 'true' : 'false');
  }
}

function switchTab(tab) {
  currentTab = tab;
  updateTabButtons();

  const activeDataset = currentTab === 'EVALUATION' ? allEvaluationRequests : allSampleRequests;
  if (activeDataset.length > 0) {
    selectedRequestId = activeDataset[0].request_id;
  }

  renderTransactionsList();
  renderDecisionHero();
  renderDemoScenariosGrid();
}

function handleNavClick(view) {
  document.querySelectorAll('.nav-link').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById(`nav-${view}`);
  if (btn) btn.classList.add('active');

  if (view === 'overview') {
    const ov = document.getElementById('section-overview');
    if (ov) ov.scrollIntoView({ behavior: 'smooth' });
  } else if (view === 'decisions') {
    setStatusFilter('ALL');
  } else if (view === 'plans') {
    setStatusFilter('affordable_with_plan');
  } else if (view === 'activity') {
    setStatusFilter('ALL');
  }
}

function filterByPosition(status) {
  setStatusFilter(status);
  const listElem = document.getElementById('transactions-list');
  if (listElem) listElem.scrollIntoView({ behavior: 'smooth' });
}

function setStatusFilter(status, pillElement = null) {
  activeFilter = status;
  document.querySelectorAll('.filter-pills-row .filter-pill').forEach(b => {
    b.classList.remove('active');
  });

  if (pillElement) {
    pillElement.classList.add('active');
  } else {
    document.querySelectorAll('.filter-pills-row .filter-pill').forEach(b => {
      const onclickAttr = b.getAttribute('onclick') || '';
      if (onclickAttr.includes(`'${status}'`)) {
        b.classList.add('active');
      }
    });
  }

  renderTransactionsList();
}

function handleSearch() {
  searchQuery = document.getElementById('search-input').value.trim().toLowerCase();
  renderTransactionsList();
}

function getFilteredRequests() {
  const list = currentTab === 'EVALUATION' ? allEvaluationRequests : allSampleRequests;
  return list.filter(item => {
    if (activeFilter !== 'ALL' && item.affordability_status !== activeFilter) {
      return false;
    }
    if (searchQuery) {
      const matchId = item.request_id.toLowerCase().includes(searchQuery);
      const matchCategory = (item.request_type || '').toLowerCase().includes(searchQuery);
      const matchText = (item.request_text || '').toLowerCase().includes(searchQuery);
      const matchStatus = (item.affordability_status || '').toLowerCase().includes(searchQuery);
      return matchId || matchCategory || matchText || matchStatus;
    }
    return true;
  });
}

// --------------------------------------------------------------------------
// TRANSACTION-STYLE LIST
// --------------------------------------------------------------------------
function renderTransactionsList() {
  const container = document.getElementById('transactions-list');
  if (!container) return;
  container.innerHTML = '';

  const filtered = getFilteredRequests();
  if (filtered.length === 0) {
    container.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-secondary); font-size: 0.85rem;">No matching decisions found</div>';
    return;
  }

  filtered.forEach(req => {
    const isSelected = req.request_id === selectedRequestId;
    const row = document.createElement('div');
    row.className = `transaction-item ${isSelected ? 'selected' : ''}`;
    row.setAttribute('role', 'listitem');

    const curr = (req.profile && req.profile.home_currency) || '';
    const categoryTitle = formatCategory(req.request_type);
    const dateFormatted = formatDate(req.request_date);

    row.innerHTML = `
      <div class="tx-left">
        <div class="tx-title">${categoryTitle}</div>
        <div class="tx-sub">${dateFormatted || 'Request'} · ${req.request_id}</div>
      </div>
      <div class="tx-right">
        <div class="tx-amount">${formatMoney(req.requested_amount, curr)}</div>
        ${getStatusBadgeHtml(req.affordability_status)}
      </div>
    `;

    row.onclick = () => selectRequest(req.request_id);
    container.appendChild(row);
  });
}

function selectRequest(requestId) {
  selectedRequestId = requestId;
  renderDemoScenariosGrid();
  renderTransactionsList();
  renderDecisionHero();
}

function getSelectedRequest() {
  const list = currentTab === 'EVALUATION' ? allEvaluationRequests : allSampleRequests;
  let found = list.find(r => r.request_id === selectedRequestId);
  if (!found) {
    found = allEvaluationRequests.find(r => r.request_id === selectedRequestId) ||
            allSampleRequests.find(r => r.request_id === selectedRequestId);
  }
  return found;
}

// --------------------------------------------------------------------------
// HERO PURCHASE DECISION PANEL
// --------------------------------------------------------------------------
function renderDecisionHero() {
  const req = getSelectedRequest();
  if (!req) return;

  const curr = (req.profile && req.profile.home_currency) || '';
  const status = req.affordability_status;
  const statusCss = getStatusCssClass(status);

  // Eyebrow, Title, Meta
  const typeLabel = document.getElementById('decision-type-label');
  if (typeLabel) {
    typeLabel.innerText = currentTab === 'EVALUATION' ? 'Purchase Decision' : 'Demo Scenario / Reference';
  }

  document.getElementById('decision-item-name').innerText = formatCategory(req.request_type);
  
  const refElem = document.getElementById('decision-ref-id');
  if (refElem) refElem.innerText = `Request #${req.request_id.replace('request_', '')}`;

  const desiredFormatted = formatDate(req.desired_completion_date);
  const targetElem = document.getElementById('decision-target-date');
  if (targetElem) targetElem.innerText = `Target: ${desiredFormatted || 'Flexible'}`;

  // Status Badge
  const statusBadge = document.getElementById('decision-status-badge');
  if (statusBadge) {
    statusBadge.className = `status-badge ${statusCss}`;
    statusBadge.innerHTML = `
      <span class="status-icon">${getStatusSymbol(status)}</span>
      <span class="status-label">${getStatusLabel(status)}</span>
    `;
  }

  // Amount Comparison Hero Block
  const reqAmt = req.requested_amount || 0;
  const safeAmt = parseFloat(req.amount_safe_to_pay) || 0;

  document.getElementById('comp-requested-amount').innerText = formatMoney(reqAmt, curr);
  document.getElementById('comp-safe-amount').innerText = formatMoney(safeAmt, curr);

  // Subtle progress bar
  const fillElem = document.getElementById('comp-progress-fill');
  const captionElem = document.getElementById('comp-progress-caption');

  if (safeAmt >= reqAmt && reqAmt > 0) {
    if (fillElem) {
      fillElem.style.width = '100%';
      fillElem.style.backgroundColor = 'var(--success)';
    }
    if (captionElem) captionElem.innerText = '100% safe to pay today';
  } else if (safeAmt > 0) {
    const pct = Math.min(100, Math.max(5, ((safeAmt / reqAmt) * 100))).toFixed(0);
    if (fillElem) {
      fillElem.style.width = `${pct}%`;
      fillElem.style.backgroundColor = 'var(--primary-blue)';
    }
    if (captionElem) captionElem.innerText = `Partial amount currently safe (${pct}% safe today)`;
  } else {
    if (fillElem) {
      fillElem.style.width = '0%';
      fillElem.style.backgroundColor = 'var(--danger)';
    }
    if (captionElem) captionElem.innerText = 'No immediate safe payment today';
  }

  // Terms Row
  document.getElementById('term-payment-method').innerText = formatPaymentMethod(req.recommended_payment_method);

  let earliestStr = 'Today';
  if (status === 'not_affordable') {
    earliestStr = 'Not safe in 90d';
  } else if (req.earliest_date_for_full_payment) {
    earliestStr = formatDate(req.earliest_date_for_full_payment);
  } else if (status === 'affordable_later') {
    earliestStr = 'Upon Next Payday';
  }
  document.getElementById('term-earliest-date').innerText = earliestStr;
  document.getElementById('term-desired-date').innerText = desiredFormatted || 'Flexible';
  document.getElementById('term-allows-partial').innerText = req.allows_partial_payment ? 'Yes' : 'No';

  // Why This Decision Section (Exact unedited explanation)
  document.getElementById('detail-explanation-text').innerText = req.decision_explanation || 'No explanation generated.';

  // Payment Schedule
  renderPaymentSchedule(req, curr);

  // Budget Adjustments
  renderSpendingAdjustments(req, curr);

  // Financial Safety Section
  renderSafetySection(req, curr);

  // Decision Assistant
  renderDecisionAssistant(req, curr);

  // Decision details drawer
  renderDetailsDrawer(req, curr);
}

function renderPaymentSchedule(req, curr) {
  const container = document.getElementById('payment-plan-container');
  if (!container) return;
  const plan = req.payment_plan;

  if (!plan || plan === 'none') {
    container.innerHTML = `
      <div class="empty-msg">
        No payment plan schedule required for this request.
      </div>
    `;
    return;
  }

  const entries = plan.split('|').map((part, index) => {
    const [date, amount] = part.split(':');
    return {
      step: index + 1,
      date: date ? date.trim() : '',
      amount: parseFloat(amount) || 0,
    };
  });

  let rowsHtml = '';
  entries.forEach(e => {
    rowsHtml += `
      <tr>
        <td><strong>Payment ${e.step}</strong></td>
        <td>${formatDate(e.date)}</td>
        <td>${formatMoney(e.amount, curr)}</td>
        <td><span class="table-tag">Scheduled</span></td>
      </tr>
    `;
  });

  container.innerHTML = `
    <table class="bank-table">
      <thead>
        <tr>
          <th>Installment</th>
          <th>Date</th>
          <th>Amount</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${rowsHtml}
      </tbody>
    </table>
  `;
}

function renderSpendingAdjustments(req, curr) {
  const container = document.getElementById('spending-changes-container');
  if (!container) return;
  const sc = req.spending_changes_needed;

  if (!sc || sc === 'none') {
    container.innerHTML = `
      <div class="empty-msg">
        No budget adjustments required. All regular expenses and required reserves remain intact.
      </div>
    `;
    return;
  }

  const parts = sc.split('|');
  let rowsHtml = '';

  parts.forEach(part => {
    part = part.trim();
    if (part.startsWith('stop:')) {
      const eventId = part.split(':')[1];
      rowsHtml += `
        <div class="adj-row adj-row-stop">
          <div>
            <div class="adj-action text-danger">Stop recurring expense</div>
            <div class="adj-sub">Cancel or pause recurring commitment to restore safe reserve.</div>
          </div>
          <div class="adj-ref">Ref: ${eventId}</div>
        </div>
      `;
    } else if (part.startsWith('reduce_to:')) {
      const [, eventId, newAmount] = part.split(':');
      rowsHtml += `
        <div class="adj-row adj-row-reduce">
          <div>
            <div class="adj-action text-warning">Reduce recurring expense</div>
            <div class="adj-sub">New monthly amount: <strong>${formatMoney(newAmount, curr)}</strong></div>
          </div>
          <div class="adj-ref">Ref: ${eventId}</div>
        </div>
      `;
    }
  });

  container.innerHTML = `
    <div class="adjustments-list">
      ${rowsHtml}
    </div>
  `;
}

function renderSafetySection(req, curr) {
  const prof = req.profile || {};
  const startingBal = prof.current_available_balance !== undefined ? prof.current_available_balance : 0;
  const minBal = prof.minimum_balance_to_keep !== undefined ? prof.minimum_balance_to_keep : 0;
  const buffer = startingBal - minBal;

  document.getElementById('safety-starting-balance').innerText = formatMoney(startingBal, curr);
  document.getElementById('safety-min-balance').innerText = formatMoney(minBal, curr);

  const bufferElem = document.getElementById('safety-buffer');
  if (bufferElem) {
    bufferElem.innerText = (buffer >= 0 ? '+' : '') + formatMoney(buffer, curr);
    bufferElem.className = `safety-cell-val ${buffer >= 0 ? 'text-success' : 'text-danger'}`;
  }
}

function renderDetailsDrawer(req, curr) {
  const drawer = document.getElementById('decision-raw-details');
  if (!drawer) return;
  const prof = req.profile || {};

  drawer.innerHTML = `
    <div><strong>Request ID:</strong> ${req.request_id}</div>
    <div><strong>User ID:</strong> ${req.user_id || 'N/A'}</div>
    <div><strong>Home Currency:</strong> ${prof.home_currency || curr}</div>
    <div><strong>Request Date:</strong> ${req.request_date || 'N/A'}</div>
    <div><strong>Payment Plan:</strong> ${req.payment_plan || 'none'}</div>
    <div><strong>Spending Changes:</strong> ${req.spending_changes_needed || 'none'}</div>
  `;
}

// --------------------------------------------------------------------------
// CONTEXTUAL DECISION ASSISTANT (Phase 13.4)
// Purely deterministic, data-grounded explanations with zero external AI calls
// --------------------------------------------------------------------------
let currentAssistantQuestions = [];
let activeAssistantIndex = 0;

function formatPlanSummary(plan, curr) {
  if (!plan || plan === 'none') return 'no structured installment schedule';
  const parts = plan.split('|');
  if (parts.length === 1) {
    const [d, a] = parts[0].split(':');
    return `a single payment of ${formatMoney(a, curr)} on ${formatDate(d)}`;
  }
  const first = parts[0].split(':');
  const last = parts[parts.length - 1].split(':');
  return `${parts.length} scheduled payments starting ${formatDate(first[0])} and completing on ${formatDate(last[0])} (${formatMoney(first[1], curr)} per installment)`;
}

function formatSpendingExplanation(spending, curr) {
  if (!spending || spending === 'none') return 'none';
  const parts = spending.split('|').map(p => p.trim());
  const descs = parts.map(p => {
    if (p.startsWith('stop:')) {
      return `stopping recurring expense ${p.split(':')[1]}`;
    } else if (p.startsWith('reduce_to:')) {
      const [, id, amt] = p.split(':');
      return `reducing recurring expense ${id} to ${formatMoney(amt, curr)}`;
    }
    return p;
  });
  return descs.join(' and ');
}

function buildAssistantQuestions(req, curr) {
  const status = req.affordability_status;
  const reqAmt = req.requested_amount || 0;
  const safeAmt = parseFloat(req.amount_safe_to_pay) || 0;
  const plan = req.payment_plan || 'none';
  const spending = req.spending_changes_needed || 'none';
  const hasSpendingAdj = spending && spending !== 'none';
  const hasPlan = plan && plan !== 'none';
  const earliestDate = req.earliest_date_for_full_payment || '';
  const prof = req.profile || {};
  const startBal = prof.current_available_balance !== undefined ? prof.current_available_balance : 0;
  const minBal = prof.minimum_balance_to_keep !== undefined ? prof.minimum_balance_to_keep : 0;
  const buffer = startBal - minBal;

  const questions = [];

  if (status === 'affordable_now') {
    questions.push({
      id: 'why_safe_today',
      question: 'Why is this safe today?',
      topic: 'Immediate Full Payment Feasibility',
      answer: `Your requested amount of ${formatMoney(reqAmt, curr)} is 100% safe to pay today. Your starting available balance is ${formatMoney(startBal, curr)}, providing a liquid buffer of ${formatMoney(buffer, curr)} above your required ${formatMoney(minBal, curr)} reserve floor. The 90-day simulation confirms your balance will never drop below your reserve.`
    });
    questions.push({
      id: 'how_much_today',
      question: 'How much can I pay today?',
      topic: 'Safe Disbursement Limit',
      answer: `You can safely disburse ${formatMoney(safeAmt, curr)} today (100% of the purchase amount). No financing, deferral, or spending adjustments are needed.`
    });
    questions.push({
      id: 'safety_buffer_meaning',
      question: 'What does my safety buffer mean?',
      topic: 'Liquidity Reserve Protection',
      answer: `Your safety buffer is ${formatMoney(buffer, curr)}. This is the surplus currently in your account beyond your non-negotiable ${formatMoney(minBal, curr)} reserve floor, ensuring you can comfortably handle upcoming bills and unexpected expenses.`
    });
  } else if (status === 'affordable_with_plan') {
    if (hasSpendingAdj) {
      questions.push({
        id: 'why_spending_adj',
        question: 'Why do I need a spending adjustment?',
        topic: 'Budget Adjustment Requirement',
        answer: `To make this purchase of ${formatMoney(reqAmt, curr)} while keeping your required ${formatMoney(minBal, curr)} reserve protected, the existing decision requires adjusting recurring commitments: ${formatSpendingExplanation(spending, curr)}. Making this change frees up the necessary cash flow to stay financially safe.`
      });
    }
    questions.push({
      id: 'why_need_plan',
      question: 'Why do I need a payment plan?',
      topic: 'Cash Flow Protection',
      answer: `Paying ${formatMoney(reqAmt, curr)} in a single upfront lump sum today would breach your required reserve floor of ${formatMoney(minBal, curr)}. Spreading the cost allows your incoming paychecks to replenish cash reserves before subsequent installments come due.`
    });
    if (hasPlan) {
      questions.push({
        id: 'how_plan_works',
        question: 'How does my payment plan work?',
        topic: 'Installment Structure',
        answer: `Your recommendation uses ${formatPlanSummary(plan, curr)}. Each installment is synchronized with your projected cash flow so your balance never dips below your mandatory reserve.`
      });
    }
    questions.push({
      id: 'why_plan_safe',
      question: 'Why is this plan considered safe?',
      topic: 'Simulation Invariant',
      answer: `Every installment date in the schedule was verified against your future payroll deposits and fixed expenses across the entire 90-day simulation. Your projected liquidity remains strictly at or above your ${formatMoney(minBal, curr)} reserve floor at all times.`
    });
  } else if (status === 'affordable_later') {
    questions.push({
      id: 'why_wait',
      question: 'Why should I wait?',
      topic: 'Waiting Recommendation',
      answer: `Paying the full ${formatMoney(reqAmt, curr)} today is not safe because only ${formatMoney(safeAmt, curr)} is available before breaching your ${formatMoney(minBal, curr)} reserve. Waiting until ${formatDate(earliestDate)} allows upcoming income (payday) to replenish your cash buffer.`
    });
    questions.push({
      id: 'when_safe_full',
      question: 'When can I safely pay the full amount?',
      topic: 'Earliest Safe Payment Date',
      answer: `The earliest safe date for full payment is ${formatDate(earliestDate)}. By that date, scheduled payroll deposits restore your account balance to a level where the full payment can be disbursed without risk.`
    });
    questions.push({
      id: 'what_if_pay_today',
      question: 'What happens if I pay today?',
      topic: 'Risk of Early Payment',
      answer: `Paying today is only safe up to ${formatMoney(safeAmt, curr)}. Paying the full ${formatMoney(reqAmt, curr)} immediately would leave your account below your ${formatMoney(minBal, curr)} reserve, creating an immediate overdraft risk when scheduled expenses occur.`
    });
    if (hasSpendingAdj) {
      questions.push({
        id: 'what_spending_change',
        question: 'What should I change in my spending?',
        topic: 'Spending Adjustment',
        answer: `The recommendation advises: ${formatSpendingExplanation(spending, curr)}.`
      });
    }
  } else if (status === 'not_affordable') {
    questions.push({
      id: 'why_not_affordable',
      question: "Why can't I afford this?",
      topic: 'Reserve Protection Constraint',
      answer: `Across the entire 90-day simulation, your projected cash inflows minus mandatory expenses do not provide enough discretionary surplus to cover ${formatMoney(reqAmt, curr)} without breaching your required ${formatMoney(minBal, curr)} reserve floor.`
    });
    questions.push({
      id: 'what_preventing',
      question: 'What is preventing this purchase?',
      topic: 'Obligation Bottleneck',
      answer: `Existing recurring commitments and necessary living expenses absorb your projected cash inflows. Committing ${formatMoney(reqAmt, curr)} would push your balance below your non-negotiable ${formatMoney(minBal, curr)} safety limit.`
    });
    questions.push({
      id: 'what_needs_change',
      question: 'What would need to change?',
      topic: 'Future Viability',
      answer: `To make this purchase viable without endangering your safety reserve, you would need an increase in recurring income, a lower purchase price, or a structural reduction in monthly recurring expenses.`
    });
  }

  // If partial payment is allowed and safe amount is partial
  if (req.allows_partial_payment && safeAmt > 0 && safeAmt < reqAmt && status !== 'affordable_now') {
    questions.push({
      id: 'partial_payment_why',
      question: 'Why is partial payment recommended?',
      topic: 'Partial Payment Option',
      answer: `You can safely disburse ${formatMoney(safeAmt, curr)} today while keeping your required ${formatMoney(minBal, curr)} reserve protected. The remaining ${formatMoney(reqAmt - safeAmt, curr)} can be paid once future cash inflows arrive.`
    });
  }

  return questions;
}

function renderDecisionAssistant(req, curr) {
  const container = document.getElementById('assistant-questions-list');
  if (!container) return;
  container.innerHTML = '';

  currentAssistantQuestions = buildAssistantQuestions(req, curr);
  activeAssistantIndex = 0;

  // Render question buttons
  currentAssistantQuestions.forEach((q, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `assistant-q-btn ${idx === 0 ? 'active' : ''}`;
    btn.innerText = q.question;
    btn.setAttribute('aria-expanded', idx === 0 ? 'true' : 'false');
    btn.onclick = () => selectAssistantQuestion(idx);
    container.appendChild(btn);
  });

  // Display initial answer
  updateAssistantAnswer(0);

  // Clear query input
  const input = document.getElementById('assistant-query-input');
  if (input) input.value = '';
}

function selectAssistantQuestion(index) {
  if (index < 0 || index >= currentAssistantQuestions.length) return;
  activeAssistantIndex = index;

  const buttons = document.querySelectorAll('.assistant-q-btn');
  buttons.forEach((btn, idx) => {
    const isActive = idx === index;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-expanded', isActive ? 'true' : 'false');
  });

  updateAssistantAnswer(index);
}

function updateAssistantAnswer(index, customTopic, customText) {
  const box = document.getElementById('assistant-answer-box');
  const topicElem = document.getElementById('assistant-answer-topic');
  const textElem = document.getElementById('assistant-answer-text');
  if (!box || !topicElem || !textElem) return;

  // Subtle 150ms fade transition
  box.style.opacity = '0';
  setTimeout(() => {
    if (customText) {
      topicElem.innerText = customTopic || 'Explanation';
      textElem.innerText = customText;
    } else if (currentAssistantQuestions[index]) {
      const q = currentAssistantQuestions[index];
      topicElem.innerText = q.topic || 'Explanation';
      textElem.innerText = q.answer;
    }
    box.style.opacity = '1';
  }, 150);
}

function handleAssistantSubmit(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('assistant-query-input');
  if (!input) return;
  const rawQuery = (input.value || '').trim();
  if (!rawQuery) return;

  const qLower = rawQuery.toLowerCase();
  const req = getSelectedRequest();
  if (!req) return;
  const curr = (req.profile && req.profile.home_currency) || '';
  const status = req.affordability_status;
  const reqAmt = req.requested_amount || 0;
  const safeAmt = parseFloat(req.amount_safe_to_pay) || 0;
  const minBal = req.profile ? req.profile.minimum_balance_to_keep : 0;
  const spending = req.spending_changes_needed || 'none';
  const plan = req.payment_plan || 'none';
  const earliestDate = req.earliest_date_for_full_payment || '';

  // De-activate question buttons to show custom inquiry
  const buttons = document.querySelectorAll('.assistant-q-btn');
  buttons.forEach(btn => {
    btn.classList.remove('active');
    btn.setAttribute('aria-expanded', 'false');
  });

  // Intent recognition patterns:
  // why, safe, today, wait, payment, plan, spending, reduce, stop, reserve, amount, date
  if (qLower.includes('spend') || qLower.includes('reduc') || qLower.includes('stop') || qLower.includes('adjust')) {
    if (spending && spending !== 'none') {
      updateAssistantAnswer(
        -1,
        'Spending Adjustment Explanation',
        `To safely fund this purchase while preserving your required ${formatMoney(minBal, curr)} reserve, the existing decision requires: ${formatSpendingExplanation(spending, curr)}.`
      );
    } else {
      updateAssistantAnswer(
        -1,
        'Spending Adjustment Status',
        `No spending adjustments are required for this decision. All existing recurring expenses remain intact.`
      );
    }
  } else if (qLower.includes('plan') || qLower.includes('installment') || (qLower.includes('payment') && !qLower.includes('safe') && !qLower.includes('today'))) {
    if (plan && plan !== 'none') {
      updateAssistantAnswer(
        -1,
        'Payment Plan Structure',
        `Your recommendation uses ${formatPlanSummary(plan, curr)}. This schedule distributes the cost safely across your income cycles without violating your ${formatMoney(minBal, curr)} reserve.`
      );
    } else {
      updateAssistantAnswer(
        -1,
        'Payment Plan Status',
        `No installment plan is required for this decision. The purchase is evaluated for ${formatPaymentMethod(req.recommended_payment_method).toLowerCase()}.`
      );
    }
  } else if (qLower.includes('wait') || qLower.includes('date') || qLower.includes('when') || qLower.includes('delay')) {
    if (status === 'affordable_later' || earliestDate) {
      updateAssistantAnswer(
        -1,
        'Timing & Wait Rationale',
        `The earliest safe date for full payment is ${formatDate(earliestDate)}. Paying today would reduce your balance below your ${formatMoney(minBal, curr)} reserve floor, whereas waiting allows your upcoming paycheck to restore liquidity.`
      );
    } else if (status === 'affordable_now') {
      updateAssistantAnswer(
        -1,
        'Timing & Wait Rationale',
        `No waiting is necessary. You can safely pay 100% of ${formatMoney(reqAmt, curr)} today while maintaining your required reserve.`
      );
    } else {
      updateAssistantAnswer(
        -1,
        'Timing & Wait Rationale',
        `This purchase is not affordable within the 90-day simulation window because projected cash flows do not yield sufficient surplus above your ${formatMoney(minBal, curr)} reserve.`
      );
    }
  } else if (qLower.includes('safe') || qLower.includes('today') || qLower.includes('amount') || qLower.includes('how much')) {
    updateAssistantAnswer(
      -1,
      'Safe Payment Limit',
      `The amount safe to pay today is ${formatMoney(safeAmt, curr)}. Any payment exceeding this amount would breach your required reserve floor of ${formatMoney(minBal, curr)}.`
    );
  } else if (qLower.includes('reserve') || qLower.includes('buffer') || qLower.includes('floor') || qLower.includes('minimum')) {
    const prof = req.profile || {};
    const startBal = prof.current_available_balance !== undefined ? prof.current_available_balance : 0;
    const buffer = startBal - minBal;
    updateAssistantAnswer(
      -1,
      'Reserve & Buffer Protection',
      `Your required reserve floor is ${formatMoney(minBal, curr)}, and your current liquid buffer is ${formatMoney(buffer, curr)}. The decision engine ensures your available funds never drop below this reserve.`
    );
  } else if (qLower.includes('why') || qLower.includes('reason') || qLower.includes('explain')) {
    if (currentAssistantQuestions.length > 0) {
      selectAssistantQuestion(0);
    } else {
      updateAssistantAnswer(
        -1,
        'Decision Explanation',
        req.decision_explanation || 'No explanation available.'
      );
    }
  } else {
    // Unrecognized intent fallback strictly per specification:
    updateAssistantAnswer(
      -1,
      'Decision Assistant Guidance',
      'I can explain this purchase decision, payment plan, spending recommendation, or safety reserve.'
    );
  }
}

window.addEventListener('DOMContentLoaded', loadData);

