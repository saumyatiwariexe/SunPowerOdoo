const BASE = '/api/v1'

async function request(path, options = {}) {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
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
      details: err.details || [],
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
  get:   (path, params) => {
    const qs = params ? '?' + new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
    ).toString() : ''
    return request(`${path}${qs}`)
  },
  post:  (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del:   (path)       => request(path, { method: 'DELETE' }),

  // For CSV or non-JSON responses
  getRaw: async (path) => {
    const res = await fetch(`${BASE}${path}`, { credentials: 'include' })
    if (!res.ok) throw { code: 'DOWNLOAD_ERROR', message: 'Download failed', details: [] }
    return res
  },
}

/** Format integer paise to Indian rupee string: ₹1,23,456 */
export function formatPaise(paise) {
  if (paise == null) return '₹0'
  const rupees = Math.abs(Math.round(paise / 100))
  const neg = paise < 0 ? '-' : ''
  const str = rupees.toString()
  if (str.length <= 3) return `${neg}₹${str}`
  const last3 = str.slice(-3)
  const rest = str.slice(0, -3)
  const formatted = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3
  return `${neg}₹${formatted}`
}

/** Format paise in lakhs for chart labels */
export function formatLakhs(paise) {
  const lakhs = paise / 10_000_000
  return `₹${lakhs.toFixed(2)}L`
}
