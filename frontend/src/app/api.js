const BASE = '/api/v1'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    },
    ...options,
  })

  // Handle no-content responses
  if (res.status === 204) {
    return { data: null, meta: null }
  }

  let body
  try {
    body = await res.json()
  } catch {
    throw { code: 'PARSE_ERROR', message: 'Invalid server response', details: [] }
  }

  if (!res.ok) {
    const err = body?.error || {}
    throw {
      code: err.code || 'SERVER_ERROR',
      message: err.message || `HTTP ${res.status}`,
      details: (err.details || []).map((d) => ({ ...d, field: d.field || d.loc?.at(-1) })),
      status: res.status,
    }
  }

  // Handle envelope: { data, meta } or plain response
  if (Object.prototype.hasOwnProperty.call(body, 'data')) {
    return { data: body.data, meta: body.meta ?? null }
  }
  return { data: body, meta: null }
}

export const api = {
  get: (path, params) => {
    const qs = params
      ? '?' +
        new URLSearchParams(
          Object.fromEntries(
            Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''),
          ),
        ).toString()
      : ''
    return request(`${path}${qs}`)
  },
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  upload: (path, body) => request(path, { method: 'POST', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path) => request(path, { method: 'DELETE' }),

  // For CSV or non-JSON responses
  getRaw: async (path) => {
    const res = await fetch(`${BASE}${path}`, { credentials: 'include' })
    if (!res.ok) throw { code: 'DOWNLOAD_ERROR', message: 'Download failed', details: [] }
    return res
  },
}

export function formatPaise(paise) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: paise % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format((paise ?? 0) / 100)
}
