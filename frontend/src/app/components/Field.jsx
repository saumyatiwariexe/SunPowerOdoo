import React, { cloneElement, useId } from 'react'
export default function Field({ label, error, required, hint, children, className = '' }) {
  const id = useId()
  return (
    <div className={'field ' + className}>
      <label htmlFor={id}>
        {label}
        {required ? ' *' : ''}
      </label>
      {cloneElement(children, {
        id,
        'aria-invalid': !!error,
        'aria-describedby': error || hint ? id + '-note' : undefined,
      })}
      {(error || hint) && (
        <small id={id + '-note'} className={error ? 'form-error' : ''}>
          {error || hint}
        </small>
      )}
    </div>
  )
}
export const inputCls = 'control'
export const selectCls = 'control'
export const textareaCls = 'control'
