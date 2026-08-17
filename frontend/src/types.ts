export type TransactionType = 'income' | 'expense' | 'transfer'

export interface Summary {
  currency: string
  start_date: string | null
  end_date: string | null
  income: number
  expenses: number
  savings: number
}

export interface Transaction {
  id: number
  account_id: number
  category_id: number | null
  amount: number
  transaction_type: TransactionType
  description: string | null
  transaction_date: string
  merchant: string | null
  notes: string | null
  category: string | null
  account: string
}

export interface Account {
  id: number
  name: string
  account_type: string
  institution: string | null
  balance: number
  currency: string
}

export interface Category {
  id: number
  name: string
  category_type: 'income' | 'expense'
  parent_id: number | null
}

export interface Preferences {
  language: string
  currency: string
  monthly_income: number | null
  risk_preference: string | null
  notification_enabled: boolean
}

export interface TransactionDraft {
  account_id: string
  category_id: string
  transaction_type: TransactionType
  amount: string
  description: string
  transaction_date: string
  merchant: string
  notes: string
}

export interface ChatMessage {
  id: string
  text: string
  user: boolean
}

export interface AuthSession {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user_id: number
  name: string
}

export interface SecuritySession {
  id: number
  created_at: string
  access_expires_at: string
  refresh_expires_at: string
  current: boolean
}

export interface Budget {
  id: number
  category_id: number
  category: string
  amount: number
  period: 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'custom'
  start_date: string
  end_date: string
  spent: number
  remaining: number
  percent_used: number
}

export interface Goal {
  id: number
  name: string
  target_amount: number
  current_amount: number
  target_date: string | null
  priority: 'low' | 'medium' | 'high'
  status: 'active' | 'completed' | 'paused'
  remaining: number
  percent_complete: number
}

export interface RecurringTransaction {
  id: number
  account_id: number
  category_id: number | null
  transaction_type: 'income' | 'expense'
  amount: number
  description: string | null
  frequency: 'daily' | 'weekly' | 'monthly' | 'yearly'
  interval_count: number
  next_date: string
  end_date: string | null
  is_active: boolean
  last_generated_date: string | null
  merchant: string | null
  notes: string | null
  account: string
  category: string | null
  schedule_kind: 'standard' | 'loan_emi'
  loan_type: 'home' | 'car' | 'personal' | 'education' | 'other' | null
  lender: string | null
}

export interface Notification {
  id: number
  notification_type: 'budget_warning' | 'budget_exceeded' | 'goal_completed' | 'recurring_generated' | 'import_completed' | 'emi_generated' | 'investment_generated' | 'investment_maturity'
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export interface Investment {
  id: number
  account_id: number
  investment_type: 'mutual_fund_sip' | 'lic' | 'rd' | 'fd' | 'other'
  name: string
  provider: string | null
  contribution_amount: number
  frequency: 'one_time' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
  interval_count: number
  next_date: string
  maturity_date: string | null
  total_contributed: number
  current_value: number
  status: 'active' | 'paused' | 'completed'
  last_contribution_date: string | null
  notes: string | null
  account: string
  gain_loss: number
}

export interface InvestmentSummary {
  total_contributed: number
  current_value: number
  gain_loss: number
  active_plans: number
  next_contribution_date: string | null
}
