import React from 'react'

const paths = {
  exit: 'M10 4H4v16h6 M9 12h12 M17 8l4 4-4 4',
  menu: 'M3 6h18 M3 12h18 M3 18h18',
  board: 'M3 4h18v16H3z M9 4v16 M15 4v16',
  list: 'M7 6h14 M7 12h14 M7 18h14 M3 6h.1 M3 12h.1 M3 18h.1',
  apps: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  people:
    'M15.5 8a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0z M5 20v-2a7 5 0 0 1 14 0v2 M18 5a3 3 0 0 1 0 6 M20 14q3 1 3 4',
  chart: 'M3 3v18h18 M7 16v-3 M12 16V9 M17 16V5',
  leaf: 'M4 19C1 7 10 4 21 4c0 11-5 17-14 14 M3 22 15 10',
  document: 'M5 2h10l4 4v16H5z M14 2v5h5 M8 11h8 M8 15h8 M8 18h5',
  bag: 'M4 8h16l1 13H3z M8 9V6a4 4 0 0 1 8 0v3',
  survey: 'M3 11 12 3l9 8 M5 10v11h14V10 M9 21v-7h6v7',
  box: 'm3 7 9-5 9 5v10l-9 5-9-5z M3 7l9 5 9-5 M12 12v10 M7 5l10 5',
  truck:
    'M2 5h12v12H2z M14 9h4l4 5v3h-8 M8 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0z M20 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0z',
  calendar: 'M3 5h18v16H3z M7 2v6 M17 2v6 M3 10h18 M8 15l3 3 5-5',
  ticket: 'M2 7h20v4a2 2 0 0 0 0 4v3H2v-3a2 2 0 0 0 0-4z M15 8v2m0 2v2m0 2v1',
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0z M15 15l6 6',
}

export default function AppIcon({ name, size = 20 }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name]} />
    </svg>
  )
}
