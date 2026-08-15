import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App authentication screen', () => {
  it('keeps the bearer token masked until the user reveals it', async () => {
    const user = userEvent.setup()
    render(<App />)

    const token = screen.getByLabelText('API bearer token')
    expect(screen.getByRole('heading', { name: 'Welcome to Khata' })).toBeInTheDocument()
    expect(token).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show token' }))

    expect(token).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Hide token' })).toBeInTheDocument()
  })
})
