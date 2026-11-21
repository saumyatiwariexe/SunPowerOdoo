import { api, formatPaise } from './api'
import { human } from './navigation'

export async function allRows(path, params = {}) {
  const rows = []
  for (let page = 1; ; page++) {
    const response = await api.get(path, { ...params, page, page_size: 100 })
    rows.push(...response.data)
    if (!response.meta || rows.length >= response.meta.total) return rows
    if (!response.data.length) throw new Error('Could not load all choices. Please retry.')
  }
}

export async function recordOptions(kind) {
  if (kind === 'products') {
    return (await allRows('/products')).filter((p) => p.category !== 'SERVICE').map((p) => ({
      value: p.id, label: `${p.name} · ${p.sku}`,
      detail: `${p.on_hand} in stock · ${p.tracks_serial ? 'Serial numbers required' : 'Quantity only'}`,
    }))
  }
  if (kind === 'packages') {
    return (await allRows('/packages', { status: 'ACTIVE' })).map((p) => ({
      value: p.id, label: p.name,
      detail: `${p.capacity_kw ? p.capacity_kw + ' kW · ' : ''}${formatPaise(p.price_paise)}`,
    }))
  }
  if (kind === 'approved_leads') {
    const [leads, surveys] = await Promise.all([allRows('/leads'), allRows('/surveys', { status: 'APPROVED' })])
    const approved = new Set(surveys.map((s) => s.lead_id))
    return leads.filter((l) => approved.has(l.id) && !['LOST', 'WON'].includes(l.status)).map((l) => ({
      value: l.id, label: `${l.customer.name} · Lead #${l.id}`,
      detail: `${l.customer.phone} · ${l.requested_kw} kW · ${human(l.status)}`,
    }))
  }
  if (kind === 'orders') {
    return (await allRows('/orders/options')).filter((o) => o.status !== 'CANCELLED').map((o) => ({
      value: o.id, label: `${o.customer_name} · ${o.number}`,
      detail: `${o.phone} · ${human(o.status)} · ${formatPaise(o.total_paise)}`,
    }))
  }
  if (kind === 'crew' || kind === 'assignees') {
    return (await allRows('/auth/assignment-options', kind === 'crew' ? { role: 'CREW' } : {})).map((u) => ({
      value: u.id, label: `${u.name} · ${human(u.role)}`, detail: u.email,
    }))
  }
  throw new Error('Unknown record selection.')
}
