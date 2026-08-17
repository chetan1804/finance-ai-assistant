import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { api, ApiUnauthorizedError, publicApi } from './api'
import type {
  Account,
  AuthSession,
  Budget,
  Category,
  ChatMessage,
  Preferences,
  Goal,
  RecurringTransaction,
  SecuritySession,
  Summary,
  Transaction,
  TransactionDraft,
  TransactionType,
} from './types'

const TOKEN_KEY = 'finance_api_token'
const THREAD_KEY = 'finance_chat_thread'
const REFRESH_KEY = 'finance_refresh_token'
const INITIAL_TOKEN = sessionStorage.getItem(TOKEN_KEY) || ''
const INITIAL_REFRESH = sessionStorage.getItem(REFRESH_KEY) || ''
const today = () => new Date().toISOString().slice(0, 10)

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : 'An unexpected error occurred.'
}

function formatMoney(value: number, currency = 'INR') {
  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${currency} ${value.toLocaleString('en-IN')}`
  }
}

function formatDate(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function recurringHasEnded(item: RecurringTransaction) {
  return Boolean(item.end_date && item.next_date > item.end_date)
}

function summaryPath(startDate: string, endDate: string) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  return `/api/v1/summary${params.size ? `?${params}` : ''}`
}

function emptyTransaction(accountId = ''): TransactionDraft {
  return {
    account_id: accountId,
    category_id: '',
    transaction_type: 'expense',
    amount: '',
    description: '',
    transaction_date: today(),
    merchant: '',
    notes: '',
  }
}

const defaultPreferences: Preferences = {
  language: 'English',
  currency: 'INR',
  monthly_income: null,
  risk_preference: null,
  notification_enabled: true,
}

function App() {
  const [token, setToken] = useState(INITIAL_TOKEN)
  const tokenRef = useRef(INITIAL_TOKEN)
  const [tokenInput, setTokenInput] = useState(INITIAL_TOKEN)
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'legacy'>('login')
  const [authName, setAuthName] = useState('')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authCurrency, setAuthCurrency] = useState('INR')
  const [authAccount, setAuthAccount] = useState('Main account')
  const [tokenVisible, setTokenVisible] = useState(false)
  const [connected, setConnected] = useState(false)
  const [checkingSession, setCheckingSession] = useState(Boolean(INITIAL_TOKEN))
  const [authError, setAuthError] = useState('')
  const [busy, setBusy] = useState(false)

  const [summary, setSummary] = useState<Summary | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [recurring, setRecurring] = useState<RecurringTransaction[]>([])
  const [preferences, setPreferences] = useState(defaultPreferences)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [lastUpdated, setLastUpdated] = useState('Not synced yet')
  const [sessions, setSessions] = useState<SecuritySession[]>([])
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [privacyPassword, setPrivacyPassword] = useState('')
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [budgetDraft, setBudgetDraft] = useState({
    category_id: '', amount: '', period: 'monthly', start_date: today(), end_date: today(),
  })
  const [goalDraft, setGoalDraft] = useState({
    name: '', target_amount: '', current_amount: '0', target_date: '', priority: 'medium',
  })
  const [recurringDraft, setRecurringDraft] = useState({
    account_id: '', category_id: '', transaction_type: 'expense', amount: '',
    description: '', frequency: 'monthly', interval_count: '1', next_date: today(), end_date: '',
  })

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [draft, setDraft] = useState<TransactionDraft>(emptyTransaction())
  const dialogRef = useRef<HTMLDialogElement>(null)

  const [chatQuestion, setChatQuestion] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { id: 'welcome', text: 'Hi — ask me about your income, spending, savings, or categories.', user: false },
  ])
  const [chatBusy, setChatBusy] = useState(false)
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const notify = useCallback((message: string, error = false) => {
    if (toastTimer.current) clearTimeout(toastTimer.current)
    setToast({ message, error })
    toastTimer.current = setTimeout(() => setToast(null), 4200)
  }, [])

  const loadDashboard = useCallback(async (
    authToken: string,
    filters: { start: string; end: string },
  ) => {
    await api(authToken, '/api/v1/recurring-transactions/process', {
      method: 'POST', body: JSON.stringify({}),
    })
    const [nextSummary, nextTransactions, nextAccounts, nextCategories, nextPreferences, nextSessions, nextBudgets, nextGoals, nextRecurring] = await Promise.all([
      api<Summary>(authToken, summaryPath(filters.start, filters.end)),
      api<Transaction[]>(authToken, '/api/v1/transactions?limit=50'),
      api<Account[]>(authToken, '/api/v1/accounts'),
      api<Category[]>(authToken, '/api/v1/categories'),
      api<Preferences>(authToken, '/api/v1/preferences'),
      api<SecuritySession[]>(authToken, '/api/v1/auth/sessions'),
      api<Budget[]>(authToken, '/api/v1/budgets'),
      api<Goal[]>(authToken, '/api/v1/goals'),
      api<RecurringTransaction[]>(authToken, '/api/v1/recurring-transactions'),
    ])
    setSummary(nextSummary)
    setTransactions(nextTransactions)
    setAccounts(nextAccounts)
    setCategories(nextCategories)
    setPreferences(nextPreferences)
    setSessions(nextSessions)
    setBudgets(nextBudgets)
    setGoals(nextGoals)
    setRecurring(nextRecurring)
    setLastUpdated(`Updated ${new Intl.DateTimeFormat('en-IN', {
      hour: 'numeric', minute: '2-digit',
    }).format(new Date())}`)
  }, [])

  const saveSession = useCallback((session: AuthSession) => {
    sessionStorage.setItem(TOKEN_KEY, session.access_token)
    sessionStorage.setItem(REFRESH_KEY, session.refresh_token)
    setToken(session.access_token)
    tokenRef.current = session.access_token
    setTokenInput(session.access_token)
  }, [])

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(REFRESH_KEY)
    sessionStorage.removeItem(THREAD_KEY)
    setToken('')
    tokenRef.current = ''
    setTokenInput('')
    setConnected(false)
    setSessions([])
  }, [])

  async function authorizedApi<T>(path: string, options: RequestInit = {}) {
    try {
      return await api<T>(tokenRef.current, path, options)
    } catch (error) {
      const refreshToken = sessionStorage.getItem(REFRESH_KEY)
      if (!(error instanceof ApiUnauthorizedError) || !refreshToken) throw error
      const session = await publicApi<AuthSession>('/api/v1/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      saveSession(session)
      return api<T>(session.access_token, path, options)
    }
  }

  useEffect(() => {
    if (!INITIAL_TOKEN) return
    const restore = async () => {
      try {
        await loadDashboard(INITIAL_TOKEN, { start: '', end: '' })
        setConnected(true)
      } catch (initialError) {
        if (!INITIAL_REFRESH) throw initialError
        const session = await publicApi<AuthSession>('/api/v1/auth/refresh', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: INITIAL_REFRESH }),
        })
        saveSession(session)
        await loadDashboard(session.access_token, { start: '', end: '' })
        setConnected(true)
      }
    }
    void restore().catch((error: unknown) => {
        sessionStorage.removeItem(TOKEN_KEY)
        sessionStorage.removeItem(REFRESH_KEY)
        setToken('')
        setTokenInput('')
        setAuthError(messageFrom(error))
      })
      .finally(() => setCheckingSession(false))
  }, [loadDashboard, saveSession])

  useEffect(() => {
    if (dialogOpen && dialogRef.current && !dialogRef.current.open) {
      dialogRef.current.showModal()
    }
  }, [dialogOpen])

  const currency = summary?.currency || preferences.currency || 'INR'
  const rate = summary && summary.income > 0
    ? (summary.savings / summary.income) * 100
    : 0
  const chartMaximum = Math.max(summary?.income || 0, summary?.expenses || 0, 1)
  const periodLabel = summary?.start_date || summary?.end_date
    ? `${summary?.start_date ? formatDate(summary.start_date) : 'Start'} — ${summary?.end_date ? formatDate(summary.end_date) : 'Today'}`
    : 'All time'
  const greeting = new Date().getHours() < 12
    ? 'morning'
    : new Date().getHours() < 17 ? 'afternoon' : 'evening'

  const topCategories = useMemo(() => {
    const totals = new Map<string, number>()
    transactions.filter((item) => item.transaction_type === 'expense').forEach((item) => {
      const name = item.category || 'Uncategorized'
      totals.set(name, (totals.get(name) || 0) + item.amount)
    })
    return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4)
  }, [transactions])

  const availableCategories = categories.filter(
    (category) => category.category_type === draft.transaction_type,
  )
  const expenseCategories = categories.filter((category) => category.category_type === 'expense')
  const recurringCategories = categories.filter(
    (category) => category.category_type === recurringDraft.transaction_type,
  )

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthError('')
    setBusy(true)
    try {
      let accessToken: string
      if (authMode === 'legacy') {
        accessToken = tokenInput.trim()
        await loadDashboard(accessToken, { start: '', end: '' })
        sessionStorage.setItem(TOKEN_KEY, accessToken)
        sessionStorage.removeItem(REFRESH_KEY)
        setToken(accessToken)
        tokenRef.current = accessToken
      } else {
        const path = authMode === 'register' ? '/api/v1/auth/register' : '/api/v1/auth/login'
        const body = authMode === 'register'
          ? {
              name: authName,
              email: authEmail,
              password: authPassword,
              currency: authCurrency,
              account_name: authAccount,
            }
          : { email: authEmail, password: authPassword }
        const session = await publicApi<AuthSession>(path, {
          method: 'POST',
          body: JSON.stringify(body),
        })
        saveSession(session)
        accessToken = session.access_token
        await loadDashboard(accessToken, { start: '', end: '' })
      }
      setConnected(true)
    } catch (error) {
      setAuthError(messageFrom(error))
    } finally {
      setBusy(false)
    }
  }

  async function signOut() {
    const refreshToken = sessionStorage.getItem(REFRESH_KEY)
    if (token && refreshToken) {
      await api<null>(tokenRef.current, '/api/v1/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => undefined)
    }
    clearSession()
    notify('Signed out of this browser session.')
  }

  async function refreshDashboard() {
    setBusy(true)
    try {
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      notify('Dashboard refreshed.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function applyDates(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      setSummary(await authorizedApi<Summary>(summaryPath(startDate, endDate)))
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function clearDates() {
    setStartDate('')
    setEndDate('')
    try {
      setSummary(await authorizedApi<Summary>('/api/v1/summary'))
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  function openAddTransaction() {
    if (!accounts.length) {
      notify('Create an account before adding a transaction.', true)
      return
    }
    setEditingId(null)
    setDraft(emptyTransaction(String(accounts[0].id)))
    setDialogOpen(true)
  }

  function openEditTransaction(transaction: Transaction) {
    setEditingId(transaction.id)
    setDraft({
      account_id: String(transaction.account_id),
      category_id: transaction.category_id ? String(transaction.category_id) : '',
      transaction_type: transaction.transaction_type,
      amount: String(transaction.amount),
      description: transaction.description || '',
      transaction_date: transaction.transaction_date,
      merchant: transaction.merchant || '',
      notes: transaction.notes || '',
    })
    setDialogOpen(true)
  }

  function closeTransactionDialog() {
    if (dialogRef.current?.open) dialogRef.current.close()
    setDialogOpen(false)
  }

  async function saveTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    const payload = {
      account_id: Number(draft.account_id),
      category_id: draft.category_id ? Number(draft.category_id) : null,
      transaction_type: draft.transaction_type,
      amount: Number(draft.amount),
      description: draft.description.trim() || null,
      transaction_date: draft.transaction_date || null,
      merchant: draft.merchant.trim() || null,
      notes: draft.notes.trim() || null,
    }
    try {
      await authorizedApi<{ id: number }>(
        editingId ? `/api/v1/transactions/${editingId}` : '/api/v1/transactions',
        { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) },
      )
      const wasEditing = editingId !== null
      closeTransactionDialog()
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      const label = draft.transaction_type[0].toUpperCase() + draft.transaction_type.slice(1)
      notify(`${label} ${formatMoney(Number(draft.amount), currency)} ${wasEditing ? 'updated' : 'saved'}.`)
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function deleteTransaction(transaction: Transaction) {
    const label = transaction.description || transaction.merchant || 'this transaction'
    if (!globalThis.confirm(`Delete ${label}? This cannot be undone.`)) return
    try {
      await authorizedApi<null>(`/api/v1/transactions/${transaction.id}`, { method: 'DELETE' })
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      notify('Transaction deleted and account balance updated.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function saveBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      await authorizedApi<{ id: number }>('/api/v1/budgets', {
        method: 'POST',
        body: JSON.stringify({
          ...budgetDraft,
          category_id: Number(budgetDraft.category_id),
          amount: Number(budgetDraft.amount),
        }),
      })
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      setBudgetDraft({ ...budgetDraft, amount: '' })
      notify('Budget created.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function deleteBudget(budget: Budget) {
    if (!globalThis.confirm(`Delete the ${budget.category} budget?`)) return
    try {
      await authorizedApi<null>(`/api/v1/budgets/${budget.id}`, { method: 'DELETE' })
      setBudgets((current) => current.filter((item) => item.id !== budget.id))
      notify('Budget deleted.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function saveGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      await authorizedApi<{ id: number }>('/api/v1/goals', {
        method: 'POST',
        body: JSON.stringify({
          ...goalDraft,
          target_amount: Number(goalDraft.target_amount),
          current_amount: Number(goalDraft.current_amount),
          target_date: goalDraft.target_date || null,
          status: 'active',
        }),
      })
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      setGoalDraft({ ...goalDraft, name: '', target_amount: '', current_amount: '0', target_date: '' })
      notify('Savings goal created.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function deleteGoal(goal: Goal) {
    if (!globalThis.confirm(`Delete the ${goal.name} goal?`)) return
    try {
      await authorizedApi<null>(`/api/v1/goals/${goal.id}`, { method: 'DELETE' })
      setGoals((current) => current.filter((item) => item.id !== goal.id))
      notify('Savings goal deleted.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function saveRecurring(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      await authorizedApi<{ id: number }>('/api/v1/recurring-transactions', {
        method: 'POST',
        body: JSON.stringify({
          ...recurringDraft,
          account_id: Number(recurringDraft.account_id),
          category_id: recurringDraft.category_id ? Number(recurringDraft.category_id) : null,
          amount: Number(recurringDraft.amount),
          interval_count: Number(recurringDraft.interval_count),
          description: recurringDraft.description.trim() || null,
          end_date: recurringDraft.end_date || null,
          is_active: true,
        }),
      })
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      setRecurringDraft({ ...recurringDraft, amount: '', description: '' })
      notify('Recurring transaction created.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function toggleRecurring(item: RecurringTransaction) {
    if (recurringHasEnded(item)) {
      notify('This schedule has reached its end date.', true)
      return
    }
    try {
      await authorizedApi<{ id: number }>(`/api/v1/recurring-transactions/${item.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          account_id: item.account_id,
          category_id: item.category_id,
          transaction_type: item.transaction_type,
          amount: item.amount,
          description: item.description,
          frequency: item.frequency,
          interval_count: item.interval_count,
          next_date: item.next_date,
          end_date: item.end_date,
          merchant: item.merchant,
          notes: item.notes,
          is_active: !item.is_active,
        }),
      })
      setRecurring((current) => current.map((entry) => (
        entry.id === item.id ? { ...entry, is_active: !entry.is_active } : entry
      )))
      notify(item.is_active ? 'Recurring transaction paused.' : 'Recurring transaction resumed.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function deleteRecurring(item: RecurringTransaction) {
    if (!globalThis.confirm(`Delete ${item.description || 'this recurring transaction'}?`)) return
    try {
      await authorizedApi<null>(`/api/v1/recurring-transactions/${item.id}`, { method: 'DELETE' })
      setRecurring((current) => current.filter((entry) => entry.id !== item.id))
      notify('Recurring transaction deleted.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function processRecurring() {
    setBusy(true)
    try {
      const result = await authorizedApi<{ generated_count: number }>('/api/v1/recurring-transactions/process', {
        method: 'POST', body: JSON.stringify({}),
      })
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      notify(`${result.generated_count} scheduled transaction${result.generated_count === 1 ? '' : 's'} generated.`)
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    try {
      const updated = await authorizedApi<Preferences>('/api/v1/preferences', {
        method: 'PUT',
        body: JSON.stringify({
          ...preferences,
          currency: preferences.currency.trim().toUpperCase(),
          risk_preference: preferences.risk_preference || null,
        }),
      })
      setPreferences(updated)
      await loadDashboard(tokenRef.current, { start: startDate, end: endDate })
      notify('Preferences updated.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (newPassword !== confirmPassword) {
      notify('New password confirmation does not match.', true)
      return
    }
    setBusy(true)
    try {
      const session = await authorizedApi<AuthSession>('/api/v1/auth/password', {
        method: 'PATCH',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      saveSession(session)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setSessions(await api<SecuritySession[]>(session.access_token, '/api/v1/auth/sessions'))
      notify('Password changed and all previous sessions were signed out.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function revokeSession(session: SecuritySession) {
    try {
      await authorizedApi<null>(`/api/v1/auth/sessions/${session.id}`, {
        method: 'DELETE',
      })
      if (session.current) {
        clearSession()
        notify('Current session revoked.')
      } else {
        setSessions((current) => current.filter((item) => item.id !== session.id))
        notify('Session revoked.')
      }
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function signOutEverywhere() {
    if (!currentPassword) {
      notify('Enter your current password first.', true)
      return
    }
    try {
      await authorizedApi<null>('/api/v1/auth/logout-all', {
        method: 'POST',
        body: JSON.stringify({ password: currentPassword }),
      })
      clearSession()
      notify('All sessions have been signed out.')
    } catch (error) {
      notify(messageFrom(error), true)
    }
  }

  async function downloadPersonalData() {
    if (!privacyPassword) {
      notify('Enter your password to export your data.', true)
      return
    }
    setBusy(true)
    try {
      const exported = await authorizedApi<Record<string, unknown>>('/api/v1/privacy/export', {
        method: 'POST',
        body: JSON.stringify({ password: privacyPassword }),
      })
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `khata-data-${today()}.json`
      link.click()
      URL.revokeObjectURL(url)
      setPrivacyPassword('')
      notify('Your personal data export was downloaded.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function deleteAccount() {
    if (deleteConfirmation !== 'DELETE' || !privacyPassword) {
      notify('Enter your password and type DELETE exactly.', true)
      return
    }
    if (!globalThis.confirm('Permanently delete your account and all financial data?')) return
    setBusy(true)
    try {
      await authorizedApi<null>('/api/v1/privacy/account', {
        method: 'DELETE',
        body: JSON.stringify({
          password: privacyPassword,
          confirmation: deleteConfirmation,
        }),
      })
      clearSession()
      notify('Your account and stored data were permanently deleted.')
    } catch (error) {
      notify(messageFrom(error), true)
    } finally {
      setBusy(false)
    }
  }

  async function sendChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const question = chatQuestion.trim()
    if (!question) return
    const userMessage: ChatMessage = { id: crypto.randomUUID(), text: question, user: true }
    const pendingId = crypto.randomUUID()
    setChatMessages((current) => [...current, userMessage, { id: pendingId, text: 'Thinking…', user: false }])
    setChatQuestion('')
    setChatBusy(true)
    try {
      let threadId = sessionStorage.getItem(THREAD_KEY)
      if (!threadId) {
        threadId = `web-${crypto.randomUUID()}`
        sessionStorage.setItem(THREAD_KEY, threadId)
      }
      const response = await authorizedApi<{ answer: string }>('/api/v1/chat', {
        method: 'POST',
        body: JSON.stringify({ thread_id: threadId, question }),
      })
      setChatMessages((current) => current.map((message) => (
        message.id === pendingId ? { ...message, text: response.answer } : message
      )))
    } catch (error) {
      setChatMessages((current) => current.map((message) => (
        message.id === pendingId
          ? { ...message, text: `I couldn't answer that: ${messageFrom(error)}` }
          : message
      )))
    } finally {
      setChatBusy(false)
    }
  }

  if (checkingSession) {
    return <div className="loading-screen"><div><div className="brand-mark">ख</div><p>Opening your private workspace…</p></div></div>
  }

  if (!connected) {
    return (
      <>
        <div className="ambient ambient-one" />
        <div className="ambient ambient-two" />
        <section className="auth-view" aria-labelledby="auth-title">
          <div className="auth-card auth-card-onboarding">
            <div className="brand-mark" aria-hidden="true">ख</div>
            <p className="eyebrow">Private finance workspace</p>
            <h1 id="auth-title">Welcome to Khata</h1>
            <p className="auth-copy">Your financial picture, thoughtfully organized and securely yours.</p>
            <div className="auth-tabs" role="tablist" aria-label="Authentication method">
              <button type="button" role="tab" aria-selected={authMode === 'login'} className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>Sign in</button>
              <button type="button" role="tab" aria-selected={authMode === 'register'} className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>Create account</button>
            </div>
            <form className="auth-form" onSubmit={connect}>
              {authMode === 'register' && <label htmlFor="auth-name">Name<input id="auth-name" maxLength={100} required autoComplete="name" value={authName} onChange={(event) => setAuthName(event.target.value)} /></label>}
              {authMode !== 'legacy' && <label htmlFor="auth-email">Email<input id="auth-email" type="email" maxLength={254} required autoComplete="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} /></label>}
              {authMode !== 'legacy' && <label htmlFor="auth-password">Password<div className="token-field"><input id="auth-password" type={tokenVisible ? 'text' : 'password'} minLength={authMode === 'register' ? 15 : 1} maxLength={128} required autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} /><button className="icon-button" type="button" aria-label={tokenVisible ? 'Hide password' : 'Show password'} onClick={() => setTokenVisible((visible) => !visible)}>{tokenVisible ? 'Hide' : 'Show'}</button></div></label>}
              {authMode === 'register' && <div className="auth-onboarding-fields"><label htmlFor="auth-currency">Currency<input id="auth-currency" minLength={3} maxLength={3} required value={authCurrency} onChange={(event) => setAuthCurrency(event.target.value.toUpperCase())} /></label><label htmlFor="auth-account">First account<input id="auth-account" maxLength={100} required value={authAccount} onChange={(event) => setAuthAccount(event.target.value)} /></label></div>}
              {authMode === 'legacy' && <label htmlFor="api-token">API bearer token<div className="token-field"><input id="api-token" type={tokenVisible ? 'text' : 'password'} minLength={32} required autoComplete="off" placeholder="Paste your generated token" value={tokenInput} onChange={(event) => setTokenInput(event.target.value)} /><button className="icon-button" type="button" aria-label={tokenVisible ? 'Hide token' : 'Show token'} onClick={() => setTokenVisible((visible) => !visible)}>{tokenVisible ? 'Hide' : 'Show'}</button></div></label>}
              <button className="primary-button full-button" type="submit" disabled={busy}><span>{authMode === 'register' ? 'Create my workspace' : 'Open dashboard'}</span><span aria-hidden="true">→</span></button>
            </form>
            <button className="text-button auth-legacy" type="button" onClick={() => setAuthMode(authMode === 'legacy' ? 'login' : 'legacy')}>{authMode === 'legacy' ? 'Use email and password' : 'Use a legacy API token'}</button>
            <p className="auth-help">Sessions stay in this browser tab and are cleared when you sign out.</p>
            {authError && <div className="inline-error" role="alert">{authError}</div>}
          </div>
        </section>
        {toast && <div className={`toast${toast.error ? ' error' : ''}`} role="status">{toast.message}</div>}
      </>
    )
  }

  return (
    <>
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <div className="app-shell">
        <aside className="sidebar">
          <a className="brand" href="#overview" aria-label="Khata dashboard home"><span className="brand-mark small" aria-hidden="true">ख</span><span><strong>Khata</strong><small>Personal finance</small></span></a>
          <nav className="nav-list" aria-label="Dashboard navigation">
            <a className="nav-item active" href="#overview"><span aria-hidden="true">⌂</span> Overview</a>
            <a className="nav-item" href="#planning"><span aria-hidden="true">◎</span> Planning</a>
            <a className="nav-item" href="#recurring"><span aria-hidden="true">↻</span> Recurring</a>
            <a className="nav-item" href="#transactions"><span aria-hidden="true">↕</span> Transactions</a>
            <a className="nav-item" href="#accounts"><span aria-hidden="true">▣</span> Accounts</a>
            <a className="nav-item" href="#assistant"><span aria-hidden="true">✦</span> Assistant</a>
            <a className="nav-item" href="#preferences"><span aria-hidden="true">⚙</span> Preferences</a>
            <a className="nav-item" href="#security"><span aria-hidden="true">◇</span> Security</a>
          </nav>
          <div className="sidebar-footer"><div className="secure-note"><span className="status-dot" /><span><strong>Private session</strong><small>Encrypted in transit when served over HTTPS</small></span></div><button className="text-button" type="button" onClick={() => void signOut()}>Sign out</button></div>
        </aside>

        <main className="main-content">
          <header className="topbar">
            <div><p className="eyebrow">Financial command center</p><h1>Good {greeting}.</h1></div>
            <div className="topbar-actions"><span className="last-updated">{lastUpdated}</span><button className="secondary-button" type="button" disabled={busy} onClick={() => void refreshDashboard()}>↻ Refresh</button><button className="primary-button" type="button" onClick={openAddTransaction}>＋ Add transaction</button></div>
          </header>

          <section id="overview" className="section-block" aria-labelledby="overview-title">
            <div className="section-heading"><div><p className="eyebrow">Overview</p><h2 id="overview-title">Your money, in focus</h2></div><form className="date-filter" onSubmit={applyDates}><label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>To<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label><button className="secondary-button" type="submit">Apply</button><button className="text-button" type="button" onClick={() => void clearDates()}>Clear</button></form></div>
            <div className="metric-grid">
              <article className="metric-card metric-primary"><span className="metric-label">Net savings</span><strong className="metric-value">{summary ? formatMoney(summary.savings, currency) : '—'}</strong><span className="metric-caption">{summary && summary.savings < 0 ? 'Expenses exceed income' : 'Income minus expenses'}</span><div className="metric-orbit" aria-hidden="true" /></article>
              <article className="metric-card"><span className="metric-icon income" aria-hidden="true">↗</span><span className="metric-label">Total income</span><strong className="metric-value">{summary ? formatMoney(summary.income, currency) : '—'}</strong><span className="metric-caption">Money coming in</span></article>
              <article className="metric-card"><span className="metric-icon expense" aria-hidden="true">↘</span><span className="metric-label">Total expenses</span><strong className="metric-value">{summary ? formatMoney(summary.expenses, currency) : '—'}</strong><span className="metric-caption">Money going out</span></article>
              <article className="metric-card"><span className="metric-icon ratio" aria-hidden="true">%</span><span className="metric-label">Savings rate</span><strong className="metric-value">{rate.toFixed(1)}%</strong><span className="metric-caption">Of total income retained</span></article>
            </div>
            <div className="insight-grid">
              <article className="panel cashflow-panel"><div className="panel-heading"><div><p className="eyebrow">Cash flow</p><h3>Income vs spending</h3></div><span className="pill">{periodLabel}</span></div><div className="flow-chart" aria-label="Income and expense comparison"><div className="flow-row"><span>Income</span><div className="flow-track"><progress className="flow-bar income-bar" max="100" value={Math.max(2, ((summary?.income || 0) / chartMaximum) * 100)} /></div><strong>{formatMoney(summary?.income || 0, currency)}</strong></div><div className="flow-row"><span>Expenses</span><div className="flow-track"><progress className="flow-bar expense-bar" max="100" value={Math.max(2, ((summary?.expenses || 0) / chartMaximum) * 100)} /></div><strong>{formatMoney(summary?.expenses || 0, currency)}</strong></div></div><div className="insight-note">{summary && summary.savings < 0 ? `Spending exceeded income by ${formatMoney(Math.abs(summary.savings), currency)}.` : `You retained ${rate.toFixed(1)}% of income in this period.`}</div></article>
              <article className="panel category-panel"><div className="panel-heading"><div><p className="eyebrow">Spending mix</p><h3>Top categories</h3></div></div><div className="category-list">{topCategories.length ? topCategories.map(([name, total]) => <div className="category-row" key={name}><span>{name}</span><strong>{formatMoney(total, currency)}</strong><div className="category-track"><progress className="category-progress" max={topCategories[0][1]} value={total} /></div></div>) : <p className="empty-state">No expense data yet.</p>}</div></article>
            </div>
          </section>

          <section id="planning" className="section-block" aria-labelledby="planning-title">
            <div className="section-heading"><div><p className="eyebrow">Plan ahead</p><h2 id="planning-title">Budgets &amp; savings goals</h2></div></div>
            <div className="planning-grid">
              <article className="panel planning-panel">
                <div className="panel-heading"><div><p className="eyebrow">Spending limits</p><h3>Budgets</h3></div></div>
                <form className="compact-form" onSubmit={saveBudget}>
                  <label>Expense category<select required value={budgetDraft.category_id} onChange={(event) => setBudgetDraft({ ...budgetDraft, category_id: event.target.value })}><option value="">Choose category</option>{expenseCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
                  <label>Limit<input type="number" min="0.01" step="0.01" required value={budgetDraft.amount} onChange={(event) => setBudgetDraft({ ...budgetDraft, amount: event.target.value })} /></label>
                  <label>Period<select value={budgetDraft.period} onChange={(event) => setBudgetDraft({ ...budgetDraft, period: event.target.value })}><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="yearly">Yearly</option><option value="custom">Custom</option></select></label>
                  <label>From<input type="date" required value={budgetDraft.start_date} onChange={(event) => setBudgetDraft({ ...budgetDraft, start_date: event.target.value })} /></label>
                  <label>To<input type="date" required value={budgetDraft.end_date} onChange={(event) => setBudgetDraft({ ...budgetDraft, end_date: event.target.value })} /></label>
                  <button className="primary-button" type="submit" disabled={busy}>Create budget</button>
                </form>
                <div className="plan-list">{budgets.length ? budgets.map((budget) => <div className="plan-row" key={budget.id}><div><strong>{budget.category}</strong><small>{formatMoney(budget.spent, currency)} of {formatMoney(budget.amount, currency)} · until {formatDate(budget.end_date)}</small><progress max="100" value={budget.percent_used} /></div><button className="row-action delete-action" type="button" aria-label={`Delete ${budget.category} budget`} onClick={() => void deleteBudget(budget)}>🗑</button></div>) : <p className="empty-state">No budgets yet.</p>}</div>
              </article>
              <article className="panel planning-panel">
                <div className="panel-heading"><div><p className="eyebrow">Future funds</p><h3>Savings goals</h3></div></div>
                <form className="compact-form" onSubmit={saveGoal}>
                  <label>Goal name<input maxLength={100} required value={goalDraft.name} onChange={(event) => setGoalDraft({ ...goalDraft, name: event.target.value })} /></label>
                  <label>Target<input type="number" min="0.01" step="0.01" required value={goalDraft.target_amount} onChange={(event) => setGoalDraft({ ...goalDraft, target_amount: event.target.value })} /></label>
                  <label>Already saved<input type="number" min="0" step="0.01" required value={goalDraft.current_amount} onChange={(event) => setGoalDraft({ ...goalDraft, current_amount: event.target.value })} /></label>
                  <label>Target date<input type="date" value={goalDraft.target_date} onChange={(event) => setGoalDraft({ ...goalDraft, target_date: event.target.value })} /></label>
                  <label>Priority<select value={goalDraft.priority} onChange={(event) => setGoalDraft({ ...goalDraft, priority: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
                  <button className="primary-button" type="submit" disabled={busy}>Create goal</button>
                </form>
                <div className="plan-list">{goals.length ? goals.map((goal) => <div className="plan-row" key={goal.id}><div><strong>{goal.name}</strong><small>{formatMoney(goal.current_amount, currency)} of {formatMoney(goal.target_amount, currency)} · {goal.priority} priority</small><progress max="100" value={goal.percent_complete} /></div><button className="row-action delete-action" type="button" aria-label={`Delete ${goal.name} goal`} onClick={() => void deleteGoal(goal)}>🗑</button></div>) : <p className="empty-state">No savings goals yet.</p>}</div>
              </article>
            </div>
          </section>

          <section id="recurring" className="section-block" aria-labelledby="recurring-title">
            <div className="section-heading"><div><p className="eyebrow">Automation</p><h2 id="recurring-title">Recurring transactions</h2></div><button className="secondary-button" type="button" disabled={busy} onClick={() => void processRecurring()}>Generate due transactions</button></div>
            <div className="panel recurring-panel">
              <form className="compact-form recurring-form" onSubmit={saveRecurring}>
                <label>Account<select required value={recurringDraft.account_id} onChange={(event) => setRecurringDraft({ ...recurringDraft, account_id: event.target.value })}><option value="">Choose account</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
                <label>Type<select value={recurringDraft.transaction_type} onChange={(event) => setRecurringDraft({ ...recurringDraft, transaction_type: event.target.value, category_id: '' })}><option value="expense">Expense</option><option value="income">Income</option></select></label>
                <label>Category<select value={recurringDraft.category_id} onChange={(event) => setRecurringDraft({ ...recurringDraft, category_id: event.target.value })}><option value="">No category</option>{recurringCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
                <label>Amount<input type="number" min="0.01" step="0.01" required value={recurringDraft.amount} onChange={(event) => setRecurringDraft({ ...recurringDraft, amount: event.target.value })} /></label>
                <label>Description<input maxLength={500} value={recurringDraft.description} onChange={(event) => setRecurringDraft({ ...recurringDraft, description: event.target.value })} /></label>
                <label>Frequency<select value={recurringDraft.frequency} onChange={(event) => setRecurringDraft({ ...recurringDraft, frequency: event.target.value })}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></label>
                <label>Every<input type="number" min="1" max="365" required value={recurringDraft.interval_count} onChange={(event) => setRecurringDraft({ ...recurringDraft, interval_count: event.target.value })} /></label>
                <label>Next date<input type="date" required value={recurringDraft.next_date} onChange={(event) => setRecurringDraft({ ...recurringDraft, next_date: event.target.value })} /></label>
                <label>End date<input type="date" value={recurringDraft.end_date} onChange={(event) => setRecurringDraft({ ...recurringDraft, end_date: event.target.value })} /></label>
                <button className="primary-button" type="submit" disabled={busy}>Create schedule</button>
              </form>
              <div className="plan-list recurring-list">{recurring.length ? recurring.map((item) => <div className="plan-row" key={item.id}><div><strong>{item.description || `${item.transaction_type} schedule`}</strong><small>{formatMoney(item.amount, currency)} · every {item.interval_count > 1 ? `${item.interval_count} ` : ''}{item.frequency} · next {formatDate(item.next_date)}</small><span className={`status-label ${item.is_active ? 'active' : ''}`}>{item.is_active ? 'Active' : recurringHasEnded(item) ? 'Ended' : 'Paused'}</span></div><div className="row-actions">{!recurringHasEnded(item) && <button className="row-action" type="button" title={item.is_active ? 'Pause schedule' : 'Resume schedule'} aria-label={`${item.is_active ? 'Pause' : 'Resume'} ${item.description || 'schedule'}`} onClick={() => void toggleRecurring(item)}>{item.is_active ? 'Ⅱ' : '▶'}</button>}<button className="row-action delete-action" type="button" aria-label={`Delete ${item.description || 'schedule'}`} onClick={() => void deleteRecurring(item)}>🗑</button></div></div>) : <p className="empty-state">No recurring transactions yet.</p>}</div>
            </div>
          </section>

          <section id="transactions" className="section-block" aria-labelledby="transactions-title">
            <div className="section-heading"><div><p className="eyebrow">Activity</p><h2 id="transactions-title">Recent transactions</h2></div><button className="secondary-button" type="button" onClick={openAddTransaction}>Add transaction</button></div>
            <div className="table-panel"><div className="table-scroll"><table><thead><tr><th>Description</th><th>Category</th><th>Account</th><th>Date</th><th className="amount-cell">Amount</th><th className="actions-heading">Actions</th></tr></thead><tbody>{transactions.length ? transactions.map((transaction) => {
              const label = transaction.description || transaction.merchant || 'Transaction'
              const sign = transaction.transaction_type === 'income' ? '+' : transaction.transaction_type === 'expense' ? '−' : ''
              return <tr key={transaction.id}><td data-label="Description"><div className="transaction-name"><span className="transaction-badge">{transaction.transaction_type === 'income' ? '↗' : '↘'}</span><span>{label}</span></div></td><td data-label="Category"><span className="category-tag">{transaction.category || 'Uncategorized'}</span></td><td data-label="Account">{transaction.account}</td><td data-label="Date">{formatDate(transaction.transaction_date)}</td><td data-label="Amount" className={`amount-cell amount-${transaction.transaction_type}`}>{sign}{formatMoney(transaction.amount, currency)}</td><td data-label="Actions" className="transaction-actions"><div className="row-actions"><button className="row-action edit-action" type="button" title="Edit transaction" aria-label={`Edit ${label}`} onClick={() => openEditTransaction(transaction)}>✎</button><button className="row-action delete-action" type="button" title="Delete transaction" aria-label={`Delete ${label}`} onClick={() => void deleteTransaction(transaction)}>🗑</button></div></td></tr>
            }) : <tr><td colSpan={6} className="empty-state">No transactions found.</td></tr>}</tbody></table></div></div>
          </section>

          <section id="accounts" className="section-block" aria-labelledby="accounts-title"><div className="section-heading"><div><p className="eyebrow">Connected money</p><h2 id="accounts-title">Accounts</h2></div></div><div className="account-grid">{accounts.length ? accounts.map((account) => <article className="account-card" key={account.id}><small>{account.account_type} · {account.institution || 'Personal'}</small><h3>{account.name}</h3><strong>{formatMoney(account.balance, account.currency)}</strong></article>) : <p className="empty-state">No active accounts found.</p>}</div></section>

          <section id="assistant" className="section-block assistant-section" aria-labelledby="assistant-title"><div className="assistant-intro"><span className="assistant-spark" aria-hidden="true">✦</span><p className="eyebrow">AI finance assistant</p><h2 id="assistant-title">Ask your money a question</h2><p>Get grounded answers based only on your financial data.</p><div className="prompt-chips" aria-label="Suggested questions">{['How much did I spend?', 'What are my total savings?', 'How much did I spend on food?'].map((question) => <button type="button" key={question} onClick={() => setChatQuestion(question)}>{question}</button>)}</div></div><div className="chat-card"><div className="chat-messages" aria-live="polite">{chatMessages.map((message) => <div key={message.id} className={`message ${message.user ? 'user-message' : 'assistant-message'}`}>{!message.user && <span className="avatar">ख</span>}<p>{message.text}</p></div>)}</div><form className="chat-form" onSubmit={sendChat}><label className="sr-only" htmlFor="chat-question">Ask a financial question</label><textarea id="chat-question" rows={1} maxLength={2000} required placeholder="Ask about your finances…" value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} /><button className="send-button" type="submit" aria-label="Send question" disabled={chatBusy}>↑</button></form></div></section>

          <section id="preferences" className="section-block" aria-labelledby="preferences-title"><div className="section-heading"><div><p className="eyebrow">Personalization</p><h2 id="preferences-title">Preferences</h2></div></div><form className="panel preferences-form" onSubmit={savePreferences}><label>Language<input maxLength={50} required value={preferences.language} onChange={(event) => setPreferences({ ...preferences, language: event.target.value })} /></label><label>Currency<input maxLength={3} required value={preferences.currency} onChange={(event) => setPreferences({ ...preferences, currency: event.target.value })} /></label><label>Monthly income<input type="number" min="1" step="0.01" placeholder="Optional" value={preferences.monthly_income ?? ''} onChange={(event) => setPreferences({ ...preferences, monthly_income: event.target.value ? Number(event.target.value) : null })} /></label><label>Risk preference<select value={preferences.risk_preference || ''} onChange={(event) => setPreferences({ ...preferences, risk_preference: event.target.value || null })}><option value="">Not set</option><option value="conservative">Conservative</option><option value="moderate">Moderate</option><option value="aggressive">Aggressive</option></select></label><label className="toggle-label"><input type="checkbox" checked={preferences.notification_enabled} onChange={(event) => setPreferences({ ...preferences, notification_enabled: event.target.checked })} /><span className="toggle-control" /><span>Notifications enabled</span></label><button className="primary-button" type="submit" disabled={busy}>Save preferences</button></form></section>

          <section id="security" className="section-block" aria-labelledby="security-title">
            <div className="section-heading"><div><p className="eyebrow">Account control</p><h2 id="security-title">Security &amp; privacy</h2></div></div>
            <div className="security-grid">
              <form className="panel security-form" onSubmit={changePassword}>
                <div className="panel-heading"><div><p className="eyebrow">Credentials</p><h3>Change password</h3></div></div>
                <p className="panel-copy">Use at least 15 characters. Changing it signs out every previous session.</p>
                <label>Current password<input type="password" autoComplete="current-password" maxLength={128} required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
                <label>New password<input type="password" autoComplete="new-password" minLength={15} maxLength={128} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
                <label>Confirm new password<input type="password" autoComplete="new-password" minLength={15} maxLength={128} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
                <div className="security-actions"><button className="primary-button" type="submit" disabled={busy}>Change password</button><button className="secondary-button" type="button" onClick={() => void signOutEverywhere()}>Sign out everywhere</button></div>
              </form>

              <div className="panel sessions-panel">
                <div className="panel-heading"><div><p className="eyebrow">Access</p><h3>Active sessions</h3></div><span className="pill">{sessions.length}</span></div>
                <div className="session-list">{sessions.length ? sessions.map((session) => <div className="session-row" key={session.id}><div><strong>{session.current ? 'This browser' : 'Signed-in session'}</strong><small>Started {formatDateTime(session.created_at)} · expires {formatDateTime(session.refresh_expires_at)}</small></div><button className="text-button danger-text" type="button" onClick={() => void revokeSession(session)}>{session.current ? 'Sign out' : 'Revoke'}</button></div>) : <p className="empty-state">No database-backed sessions are available.</p>}</div>
              </div>

              <div className="panel privacy-panel">
                <div className="panel-heading"><div><p className="eyebrow">Your information</p><h3>Privacy controls</h3></div></div>
                <p className="panel-copy">Download a portable JSON copy or permanently erase your profile, finances, sessions, and conversation memory.</p>
                <label>Password<input type="password" autoComplete="current-password" maxLength={128} value={privacyPassword} onChange={(event) => setPrivacyPassword(event.target.value)} /></label>
                <button className="secondary-button" type="button" disabled={busy} onClick={() => void downloadPersonalData()}>Download my data</button>
                <div className="danger-zone"><strong>Delete account permanently</strong><p>This action cannot be undone. Backups remain subject to the documented retention schedule.</p><label>Type DELETE to confirm<input maxLength={6} value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} /></label><button className="danger-button" type="button" disabled={busy} onClick={() => void deleteAccount()}>Delete my account</button></div>
              </div>
            </div>
          </section>
        </main>
      </div>

      <dialog ref={dialogRef} className="modal transaction-dialog" onCancel={() => setDialogOpen(false)} onClose={() => setDialogOpen(false)}>
        <form onSubmit={saveTransaction}><div className="modal-heading"><div><p className="eyebrow">{editingId ? 'Update activity' : 'New activity'}</p><h2>{editingId ? 'Edit transaction' : 'Add transaction'}</h2></div><button className="icon-button" type="button" aria-label="Close" onClick={closeTransactionDialog}>×</button></div><div className="form-grid">
          <label>Type<select required value={draft.transaction_type} onChange={(event) => setDraft({ ...draft, transaction_type: event.target.value as TransactionType, category_id: '' })}><option value="expense">Expense</option><option value="income">Income</option><option value="transfer">Transfer</option></select></label>
          <label>Amount<input type="number" min="0.01" step="0.01" required placeholder="0.00" value={draft.amount} onChange={(event) => setDraft({ ...draft, amount: event.target.value })} /></label>
          <label>Account<select required value={draft.account_id} onChange={(event) => setDraft({ ...draft, account_id: event.target.value })}>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
          <label>Category<select disabled={draft.transaction_type === 'transfer'} value={draft.category_id} onChange={(event) => setDraft({ ...draft, category_id: event.target.value })}><option value="">No category</option>{availableCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <label className="wide-field">Description<input maxLength={500} placeholder="What was this for?" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
          <label>Merchant<input maxLength={255} placeholder="Optional" value={draft.merchant} onChange={(event) => setDraft({ ...draft, merchant: event.target.value })} /></label>
          <label>Date<input type="date" value={draft.transaction_date} onChange={(event) => setDraft({ ...draft, transaction_date: event.target.value })} /></label>
          <label className="wide-field">Notes<textarea maxLength={1000} rows={3} placeholder="Optional details" value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label>
        </div><div className="modal-actions"><button className="secondary-button" type="button" onClick={closeTransactionDialog}>Cancel</button><button className="primary-button" type="submit" disabled={busy}>{editingId ? 'Update transaction' : 'Save transaction'}</button></div></form>
      </dialog>
      {toast && <div className={`toast${toast.error ? ' error' : ''}`} role="status">{toast.message}</div>}
    </>
  )
}

export default App
