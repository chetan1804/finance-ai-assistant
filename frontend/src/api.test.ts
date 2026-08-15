import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from './api'

describe('api', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('surfaces FastAPI validation messages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Transaction not found.' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } },
    )))

    await expect(api('x'.repeat(32), '/api/v1/transactions/99'))
      .rejects.toThrow('Transaction not found.')
  })

  it('uses a safe authentication error for unauthorized responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Internal authentication detail' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    )))

    await expect(api('x'.repeat(32), '/api/v1/summary'))
      .rejects.toThrow('Your token is invalid or has expired.')
  })
})
