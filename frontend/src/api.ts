interface ApiErrorPayload {
  detail?: string | Array<{ msg?: string }>
}

export class ApiUnauthorizedError extends Error {}

function errorMessage(payload: ApiErrorPayload | null, fallback: string) {
  if (typeof payload?.detail === 'string') return payload.detail
  if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg
  }
  return fallback
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  const response = await fetch(path, { ...options, headers })
  const payload = response.status === 204
    ? null
    : await response.json().catch(() => null) as T | ApiErrorPayload | null

  if (response.status === 401) {
    throw new ApiUnauthorizedError('Your token is invalid or has expired.')
  }
  if (!response.ok) {
    throw new Error(
      errorMessage(payload as ApiErrorPayload | null, `Request failed (${response.status}).`),
    )
  }
  return payload as T
}

export async function apiResponse(
  token: string,
  path: string,
  options: RequestInit = {},
) {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...options, headers })
  if (response.status === 401) {
    throw new ApiUnauthorizedError('Your token is invalid or has expired.')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as ApiErrorPayload | null
    throw new Error(errorMessage(payload, `Request failed (${response.status}).`))
  }
  return response
}

export function api<T>(token: string, path: string, options: RequestInit = {}) {
  return request<T>(path, options, token)
}

export function publicApi<T>(path: string, options: RequestInit = {}) {
  return request<T>(path, options)
}
