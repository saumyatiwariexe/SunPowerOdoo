import React, { useRef, useState } from 'react'

export default function SignatureField({ onChange }) {
  const canvas = useRef(null)
  const pointer = useRef(null)
  const [drawn, setDrawn] = useState(false)
  function point(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    return [
      ((e.clientX - rect.left) * canvas.current.width) / rect.width,
      ((e.clientY - rect.top) * canvas.current.height) / rect.height,
    ]
  }
  function begin(e) {
    if (pointer.current !== null) return
    pointer.current = e.pointerId
    e.currentTarget.setPointerCapture(e.pointerId)
    const ctx = canvas.current.getContext('2d')
    const [x, y] = point(e)
    ctx.lineCap = 'round'
    ctx.lineWidth = 3
    ctx.strokeStyle = '#192921'
    ctx.beginPath()
    ctx.moveTo(x, y)
    ctx.lineTo(x + 0.1, y)
    ctx.stroke()
  }
  function move(e) {
    if (pointer.current !== e.pointerId) return
    const ctx = canvas.current.getContext('2d')
    ctx.lineTo(...point(e))
    ctx.stroke()
  }
  function end(e) {
    if (pointer.current !== e.pointerId) return
    pointer.current = null
    setDrawn(true)
    onChange(canvas.current)
  }
  function clear() {
    canvas.current.getContext('2d').clearRect(0, 0, canvas.current.width, canvas.current.height)
    setDrawn(false)
    onChange(null)
  }
  return (
    <div className="signature">
      <p>Customer signature</p>
      <canvas
        ref={canvas}
        width="640"
        height="180"
        aria-label="Draw the customer signature, or upload a signature image below"
        onPointerDown={begin}
        onPointerMove={move}
        onPointerUp={end}
        onPointerCancel={end}
      />
      {drawn && (
        <button className="text-link" type="button" onClick={clear}>
          Clear signature
        </button>
      )}
    </div>
  )
}
