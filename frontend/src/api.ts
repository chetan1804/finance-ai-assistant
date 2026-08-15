interface ApiErrorPayload {
  detail?: string | Array<{ msg?: string }>
}

function errorMessage(payload: ApiErrorPayload | null, fallback: string) {
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg
  }
  return fallback
}

export async function api<T>(
  token: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (options.body) headers.set('Content-Type', 'application/json')

  const response = await fetch(path, { ...options, headers })
  const payload = response.status === 204
    ? null
    : await response.json().catch(() => null) as T | ApiErrorPayload | null

  if (response.status === 401) {
    throw new Error('Your token is invalid or has expired.')
  }
  if (!response.ok) {
    throw new Error(
      errorMessage(payload as ApiErrorPayload | null, `Request failed (${response.status}).`),
    )
  }
  return payload as T
}
