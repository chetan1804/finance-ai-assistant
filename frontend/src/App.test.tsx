import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App authentication screen', () => {
  it('keeps the password masked until the user reveals it', async () => {
    const user = userEvent.setup()
    render(<App />)

    const password = screen.getByLabelText('Password')
    expect(screen.getByRole('heading', { name: 'Welcome to ArthNivo' })).toBeInTheDocument()
    expect(password).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show password' }))

    expect(password).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument()
  })

  it('offers first-account onboarding during registration', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('tab', { name: 'Create account' }))

    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Currency')).toHaveValue('INR')
    expect(screen.getByLabelText('First account')).toHaveValue('Main account')
  })
})
