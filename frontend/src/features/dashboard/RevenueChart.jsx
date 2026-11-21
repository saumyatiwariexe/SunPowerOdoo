import React, { useMemo } from 'react'

/**
 * Simple SVG bar chart — no external library.
 * data: [{ label: string, value: number (paise) }]
 */
export default function RevenueChart({ data = [] }) {
  const W = 500, H = 200, PAD = { top: 10, right: 10, bottom: 40, left: 60 }
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top  - PAD.bottom

  const max = useMemo(() => Math.max(...data.map(d => d.value), 1), [data])
  const lakhMax = Math.ceil(max / 1_00_000 / 100) // paise -> lakhs, then round up

  const bars = data.map((d, i) => {
    const barW  = innerW / data.length - 8
    const barH  = (d.value / (lakhMax * 1_00_000 * 100)) * innerH
    const x     = PAD.left + i * (innerW / data.length) + 4
    const y     = PAD.top + innerH - barH
    return { ...d, barW, barH, x, y }
  })

  // Y-axis labels (5 steps)
  const ySteps = [0, 0.25, 0.5, 0.75, 1].map(f => ({
    label: `₹${(lakhMax * f).toFixed(1)}L`,
    y: PAD.top + innerH - f * innerH,
  }))

  if (!data.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-400">
        No revenue data for this period
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-2xl"
        aria-label="Revenue bar chart"
      >
        {/* Grid lines + Y labels */}
        {ySteps.map((step, i) => (
          <g key={i}>
            <line
              x1={PAD.left} y1={step.y}
              x2={W - PAD.right} y2={step.y}
              stroke="#e2e8f0" strokeWidth="1"
            />
            <text
              x={PAD.left - 6} y={step.y + 4}
              textAnchor="end" fontSize="10" fill="#94a3b8"
            >{step.label}</text>
          </g>
        ))}

        {/* Bars */}
        {bars.map((bar, i) => (
          <g key={i}>
            <rect
              x={bar.x} y={bar.y}
              width={bar.barW} height={bar.barH}
              fill="#f59e0b" rx="3"
            />
            {/* X labels */}
            <text
              x={bar.x + bar.barW / 2}
              y={H - PAD.bottom + 15}
              textAnchor="middle"
              fontSize="10"
              fill="#64748b"
            >
              {bar.label}
            </text>
          </g>
        ))}

        {/* X axis */}
        <line
          x1={PAD.left} y1={PAD.top + innerH}
          x2={W - PAD.right} y2={PAD.top + innerH}
          stroke="#cbd5e1" strokeWidth="1"
        />
      </svg>
    </div>
  )
}
