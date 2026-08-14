const TOKEN_KEY = "finance_api_token";
const THREAD_KEY = "finance_chat_thread";

const state = {
  token: sessionStorage.getItem(TOKEN_KEY) || "",
  currency: "INR",
  accounts: [],
  categories: [],
  transactions: [],
  editingTransactionId: null,
};

const byId = (id) => document.getElementById(id);
const authView = byId("auth-view");
const appShell = byId("app-shell");
const toast = byId("toast");

function errorMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg;
  }
  return fallback;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body) headers.set("Content-Type", "application/json");

  const response = await fetch(path, { ...options, headers });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);

  if (response.status === 401) {
    disconnect(false);
    throw new Error("Your token is invalid or has expired.");
  }
  if (!response.ok) {
    throw new Error(errorMessage(payload, `Request failed (${response.status}).`));
  }
  return payload;
}

function formatMoney(value, currency = state.currency) {
  const numeric = Number(value || 0);
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(numeric);
  } catch {
    return `${currency} ${numeric.toLocaleString("en-IN")}`;
  }
}

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

let toastTimer;
function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4200);
}

function setBusy(button, busy) {
  if (!button) return;
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function disconnect(showMessage = true) {
  sessionStorage.removeItem(TOKEN_KEY);
  state.token = "";
  appShell.hidden = true;
  authView.hidden = false;
  byId("api-token").value = "";
  if (showMessage) showToast("Signed out of this browser session.");
}

function updateGreeting() {
  const hour = new Date().getHours();
  byId("day-period").textContent = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
}

function summaryQuery() {
  const params = new URLSearchParams();
  const start = byId("start-date").value;
  const end = byId("end-date").value;
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end);
  return params.size ? `?${params}` : "";
}

function renderSummary(summary) {
  state.currency = summary.currency;
  byId("savings-value").textContent = formatMoney(summary.savings);
  byId("income-value").textContent = formatMoney(summary.income);
  byId("expenses-value").textContent = formatMoney(summary.expenses);
  byId("income-chart-value").textContent = formatMoney(summary.income);
  byId("expense-chart-value").textContent = formatMoney(summary.expenses);

  const rate = summary.income > 0 ? (summary.savings / summary.income) * 100 : 0;
  byId("savings-rate").textContent = `${rate.toFixed(1)}%`;
  byId("savings-caption").textContent = summary.savings >= 0 ? "Income minus expenses" : "Expenses exceed income";

  const maximum = Math.max(summary.income, summary.expenses, 1);
  byId("income-bar").value = Math.max(2, (summary.income / maximum) * 100);
  byId("expense-bar").value = Math.max(2, (summary.expenses / maximum) * 100);
  byId("cashflow-insight").textContent = summary.savings >= 0
    ? `You retained ${rate.toFixed(1)}% of income in this period.`
    : `Spending exceeded income by ${formatMoney(Math.abs(summary.savings))}.`;

  const start = summary.start_date ? formatDate(summary.start_date) : null;
  const end = summary.end_date ? formatDate(summary.end_date) : null;
  byId("period-label").textContent = start || end ? `${start || "Start"} — ${end || "Today"}` : "All time";
}

function cell(text, className = "") {
  const element = document.createElement("td");
  element.textContent = text ?? "—";
  if (className) element.className = className;
  return element;
}

function renderTransactions(transactions) {
  state.transactions = transactions;
  const body = byId("transaction-body");
  body.replaceChildren();

  if (!transactions.length) {
    const row = document.createElement("tr");
    const empty = cell("No transactions found.", "empty-state");
    empty.colSpan = 6;
    row.append(empty);
    body.append(row);
    renderCategories([]);
    return;
  }

  transactions.forEach((transaction) => {
    const row = document.createElement("tr");
    const descriptionCell = document.createElement("td");
    const wrapper = document.createElement("div");
    wrapper.className = "transaction-name";
    const badge = document.createElement("span");
    badge.className = "transaction-badge";
    badge.textContent = transaction.transaction_type === "income" ? "↗" : "↘";
    const label = document.createElement("span");
    label.textContent = transaction.description || transaction.merchant || "Transaction";
    wrapper.append(badge, label);
    descriptionCell.append(wrapper);

    const categoryCell = document.createElement("td");
    const category = document.createElement("span");
    category.className = "category-tag";
    category.textContent = transaction.category || "Uncategorized";
    categoryCell.append(category);

    const sign = transaction.transaction_type === "income" ? "+" : "−";
    const amount = cell(`${sign}${formatMoney(transaction.amount)}`, `amount-cell amount-${transaction.transaction_type}`);
    descriptionCell.dataset.label = "Description";
    categoryCell.dataset.label = "Category";
    const account = cell(transaction.account);
    account.dataset.label = "Account";
    const transactionDate = cell(formatDate(transaction.transaction_date));
    transactionDate.dataset.label = "Date";
    amount.dataset.label = "Amount";

    const actions = document.createElement("td");
    actions.className = "transaction-actions";
    actions.dataset.label = "Actions";
    const actionButtons = document.createElement("div");
    actionButtons.className = "row-actions";
    const edit = document.createElement("button");
    edit.className = "row-action edit-action";
    edit.type = "button";
    edit.dataset.action = "edit";
    edit.dataset.transactionId = String(transaction.id);
    edit.textContent = "✎";
    edit.title = "Edit transaction";
    edit.setAttribute("aria-label", `Edit ${label.textContent}`);
    const remove = document.createElement("button");
    remove.className = "row-action delete-action";
    remove.type = "button";
    remove.dataset.action = "delete";
    remove.dataset.transactionId = String(transaction.id);
    remove.textContent = "🗑";
    remove.title = "Delete transaction";
    remove.setAttribute("aria-label", `Delete ${label.textContent}`);
    actionButtons.append(edit, remove);
    actions.append(actionButtons);

    row.append(descriptionCell, categoryCell, account, transactionDate, amount, actions);
    body.append(row);
  });
  renderCategories(transactions);
}

function renderCategories(transactions) {
  const totals = new Map();
  transactions.filter((item) => item.transaction_type === "expense").forEach((item) => {
    const name = item.category || "Uncategorized";
    totals.set(name, (totals.get(name) || 0) + Number(item.amount));
  });
  const sorted = [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
  const container = byId("category-list");
  container.replaceChildren();
  if (!sorted.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No expense data yet.";
    container.append(empty);
    return;
  }
  const max = sorted[0][1];
  sorted.forEach(([name, total]) => {
    const row = document.createElement("div");
    row.className = "category-row";
    const title = document.createElement("span");
    title.textContent = name;
    const value = document.createElement("strong");
    value.textContent = formatMoney(total);
    const track = document.createElement("div");
    track.className = "category-track";
    const bar = document.createElement("progress");
    bar.className = "category-progress";
    bar.max = max;
    bar.value = total;
    track.append(bar);
    row.append(title, value, track);
    container.append(row);
  });
}

function renderAccounts(accounts) {
  state.accounts = accounts;
  const grid = byId("account-grid");
  const select = byId("transaction-account");
  grid.replaceChildren();
  select.replaceChildren();

  if (!accounts.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No active accounts found.";
    grid.append(empty);
  }

  accounts.forEach((account) => {
    const card = document.createElement("article");
    card.className = "account-card";
    const type = document.createElement("small");
    type.textContent = `${account.account_type} · ${account.institution || "Personal"}`;
    const name = document.createElement("h3");
    name.textContent = account.name;
    const balance = document.createElement("strong");
    balance.textContent = formatMoney(account.balance, account.currency);
    card.append(type, name, balance);
    grid.append(card);

    const option = document.createElement("option");
    option.value = String(account.id);
    option.textContent = account.name;
    select.append(option);
  });
}

function updateCategoryOptions() {
  const type = byId("transaction-type").value;
  const select = byId("transaction-category");
  select.replaceChildren();
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "No category";
  select.append(empty);
  state.categories.filter((item) => item.category_type === type).forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    option.textContent = item.name;
    select.append(option);
  });
  select.disabled = type === "transfer";
}

function renderPreferences(preferences) {
  state.currency = preferences.currency;
  byId("preference-language").value = preferences.language;
  byId("preference-currency").value = preferences.currency;
  byId("preference-income").value = preferences.monthly_income ?? "";
  const risk = byId("preference-risk");
  risk.value = [...risk.options].some((option) => option.value === preferences.risk_preference) ? (preferences.risk_preference || "") : "";
  byId("preference-notifications").checked = preferences.notification_enabled;
}

async function loadDashboard() {
  const [summary, transactions, accounts, categories, preferences] = await Promise.all([
    api(`/api/v1/summary${summaryQuery()}`),
    api("/api/v1/transactions?limit=50"),
    api("/api/v1/accounts"),
    api("/api/v1/categories"),
    api("/api/v1/preferences"),
  ]);
  renderPreferences(preferences);
  renderSummary(summary);
  renderTransactions(transactions);
  state.categories = categories;
  renderAccounts(accounts);
  updateCategoryOptions();
  byId("last-updated").textContent = `Updated ${new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(new Date())}`;
}

async function connect(event) {
  event.preventDefault();
  const button = event.submitter;
  const error = byId("auth-error");
  error.hidden = true;
  state.token = byId("api-token").value.trim();
  setBusy(button, true);
  try {
    await loadDashboard();
    sessionStorage.setItem(TOKEN_KEY, state.token);
    authView.hidden = true;
    appShell.hidden = false;
    updateGreeting();
  } catch (failure) {
    state.token = "";
    error.textContent = failure.message;
    error.hidden = false;
  } finally {
    setBusy(button, false);
  }
}

async function refreshDashboard() {
  const button = byId("refresh-all");
  setBusy(button, true);
  try {
    await loadDashboard();
    showToast("Dashboard refreshed.");
  } catch (failure) {
    showToast(failure.message, true);
  } finally {
    setBusy(button, false);
  }
}

function appendMessage(text, user = false) {
  const message = document.createElement("div");
  message.className = `message ${user ? "user-message" : "assistant-message"}`;
  if (!user) {
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.textContent = "ख";
    message.append(avatar);
  }
  const content = document.createElement("p");
  content.textContent = text;
  message.append(content);
  const container = byId("chat-messages");
  container.append(message);
  container.scrollTop = container.scrollHeight;
  return message;
}

async function sendChat(event) {
  event.preventDefault();
  const input = byId("chat-question");
  const question = input.value.trim();
  if (!question) return;
  const button = event.submitter;
  appendMessage(question, true);
  input.value = "";
  setBusy(button, true);
  const pending = appendMessage("Thinking…");
  try {
    let threadId = sessionStorage.getItem(THREAD_KEY);
    if (!threadId) {
      threadId = `web-${globalThis.crypto?.randomUUID?.() || Date.now()}`;
      sessionStorage.setItem(THREAD_KEY, threadId);
    }
    const response = await api("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ thread_id: threadId, question }),
    });
    pending.querySelector("p").textContent = response.answer;
  } catch (failure) {
    pending.querySelector("p").textContent = `I couldn't answer that: ${failure.message}`;
  } finally {
    setBusy(button, false);
  }
}

async function saveTransaction(event) {
  event.preventDefault();
  const button = event.submitter;
  setBusy(button, true);
  const category = byId("transaction-category").value;
  const transactionDate = byId("transaction-date").value;
  const payload = {
    account_id: Number(byId("transaction-account").value),
    category_id: category ? Number(category) : null,
    transaction_type: byId("transaction-type").value,
    amount: Number(byId("transaction-amount").value),
    description: byId("transaction-description").value.trim() || null,
    merchant: byId("transaction-merchant").value.trim() || null,
    notes: byId("transaction-notes").value.trim() || null,
    transaction_date: transactionDate || null,
  };
  try {
    const editing = state.editingTransactionId;
    const path = editing ? `/api/v1/transactions/${editing}` : "/api/v1/transactions";
    await api(path, { method: editing ? "PUT" : "POST", body: JSON.stringify(payload) });
    byId("transaction-dialog").close();
    resetTransactionForm();
    await loadDashboard();
    const type = payload.transaction_type[0].toUpperCase() + payload.transaction_type.slice(1);
    showToast(`${type} ${formatMoney(payload.amount)} ${editing ? "updated" : "saved"}.`);
  } catch (failure) {
    showToast(failure.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function savePreferences(event) {
  event.preventDefault();
  const button = event.submitter;
  const income = byId("preference-income").value;
  const payload = {
    language: byId("preference-language").value.trim(),
    currency: byId("preference-currency").value.trim().toUpperCase(),
    monthly_income: income ? Number(income) : null,
    risk_preference: byId("preference-risk").value || null,
    notification_enabled: byId("preference-notifications").checked,
  };
  setBusy(button, true);
  try {
    const preferences = await api("/api/v1/preferences", { method: "PUT", body: JSON.stringify(payload) });
    renderPreferences(preferences);
    await loadDashboard();
    showToast("Preferences updated.");
  } catch (failure) {
    showToast(failure.message, true);
  } finally {
    setBusy(button, false);
  }
}

function openTransactionDialog() {
  if (!state.accounts.length) {
    showToast("Create an account before adding a transaction.", true);
    return;
  }
  resetTransactionForm();
  byId("transaction-dialog").showModal();
}

function resetTransactionForm() {
  state.editingTransactionId = null;
  byId("transaction-form").reset();
  byId("transaction-type").value = "expense";
  byId("transaction-date").value = new Date().toISOString().slice(0, 10);
  byId("transaction-dialog-eyebrow").textContent = "New activity";
  byId("transaction-dialog-title").textContent = "Add transaction";
  byId("save-transaction").textContent = "Save transaction";
  updateCategoryOptions();
}

function editTransaction(transactionId) {
  const transaction = state.transactions.find((item) => item.id === transactionId);
  if (!transaction) {
    showToast("Transaction is no longer available. Refresh and try again.", true);
    return;
  }
  state.editingTransactionId = transactionId;
  byId("transaction-type").value = transaction.transaction_type;
  updateCategoryOptions();
  byId("transaction-account").value = String(transaction.account_id);
  byId("transaction-category").value = transaction.category_id ? String(transaction.category_id) : "";
  byId("transaction-amount").value = transaction.amount;
  byId("transaction-description").value = transaction.description || "";
  byId("transaction-merchant").value = transaction.merchant || "";
  byId("transaction-date").value = transaction.transaction_date;
  byId("transaction-notes").value = transaction.notes || "";
  byId("transaction-dialog-eyebrow").textContent = "Update activity";
  byId("transaction-dialog-title").textContent = "Edit transaction";
  byId("save-transaction").textContent = "Update transaction";
  byId("transaction-dialog").showModal();
}

async function deleteTransaction(transactionId) {
  const transaction = state.transactions.find((item) => item.id === transactionId);
  if (!transaction) return;
  const description = transaction.description || transaction.merchant || "this transaction";
  if (!globalThis.confirm(`Delete ${description}? This cannot be undone.`)) return;
  try {
    await api(`/api/v1/transactions/${transactionId}`, { method: "DELETE" });
    await loadDashboard();
    showToast("Transaction deleted and account balance updated.");
  } catch (failure) {
    showToast(failure.message, true);
  }
}

function handleTransactionAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const transactionId = Number(button.dataset.transactionId);
  if (button.dataset.action === "edit") editTransaction(transactionId);
  if (button.dataset.action === "delete") deleteTransaction(transactionId);
}

byId("auth-form").addEventListener("submit", connect);
byId("toggle-token").addEventListener("click", () => {
  const input = byId("api-token");
  const visible = input.type === "text";
  input.type = visible ? "password" : "text";
  byId("toggle-token").textContent = visible ? "Show" : "Hide";
});
byId("sign-out").addEventListener("click", () => disconnect(true));
byId("refresh-all").addEventListener("click", refreshDashboard);
byId("date-filter").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { renderSummary(await api(`/api/v1/summary${summaryQuery()}`)); }
  catch (failure) { showToast(failure.message, true); }
});
byId("clear-dates").addEventListener("click", async () => {
  byId("start-date").value = "";
  byId("end-date").value = "";
  try { renderSummary(await api("/api/v1/summary")); }
  catch (failure) { showToast(failure.message, true); }
});
byId("open-transaction").addEventListener("click", openTransactionDialog);
byId("open-transaction-secondary").addEventListener("click", openTransactionDialog);
byId("close-transaction").addEventListener("click", () => byId("transaction-dialog").close());
byId("cancel-transaction").addEventListener("click", () => byId("transaction-dialog").close());
byId("transaction-type").addEventListener("change", updateCategoryOptions);
byId("transaction-form").addEventListener("submit", saveTransaction);
byId("transaction-body").addEventListener("click", handleTransactionAction);
byId("preferences-form").addEventListener("submit", savePreferences);
byId("chat-form").addEventListener("submit", sendChat);
document.querySelectorAll("[data-question]").forEach((button) => button.addEventListener("click", () => {
  byId("chat-question").value = button.dataset.question;
  byId("chat-question").focus();
}));

updateGreeting();
if (state.token) {
  byId("api-token").value = state.token;
  loadDashboard().then(() => {
    authView.hidden = true;
    appShell.hidden = false;
  }).catch((failure) => {
    disconnect(false);
    byId("auth-error").textContent = failure.message;
    byId("auth-error").hidden = false;
  });
}
