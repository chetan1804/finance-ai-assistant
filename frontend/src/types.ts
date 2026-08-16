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
