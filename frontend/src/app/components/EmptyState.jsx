import React from 'react'
export default function EmptyState({ title, description, action }) {
  return (
    <div className="state">
      <strong>{title}</strong>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}
