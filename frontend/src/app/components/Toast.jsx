import React, { useState, useCallback } from 'react'

const STYLES = {
  success: 'bg-emerald-50 border-emerald-400 text-emerald-800',
  error:   'bg-red-50 border-red-400 text-red-800',
  info:    'bg-teal-50 border-teal-600 text-teal-700',
}

function ToastItem({ id, type, message, onDismiss }) {
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg text-sm max-w-sm ${STYLES[type]}`}
    >
      <span className="text-base">{type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
      <p className="flex-1">{message}</p>
      <button onClick={() => onDismiss(id)} className="ml-2 opacity-60 hover:opacity-100">✕</button>
    </div>
  )
}

// Global toast state
let _setToasts = null
let _id = 0

export function toast(type, message, duration = 4000) {
  if (!_setToasts) return
  const id = ++_id
  _setToasts(prev => [...prev, { id, type, message }])
  if (duration > 0) {
    setTimeout(() => {
      _setToasts(prev => prev.filter(t => t.id !== id))
    }, duration)
  }
}

export function ToastContainer() {
  const [toasts, setToasts] = useState([])
  _setToasts = setToasts

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2">
      {toasts.map(t => (
        <ToastItem key={t.id} {...t} onDismiss={dismiss} />
      ))}
    </div>
  )
}

export default ToastContainer
