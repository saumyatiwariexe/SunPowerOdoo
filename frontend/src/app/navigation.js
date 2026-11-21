export const sections = [
  [
    'Operations',
    [
      ['dashboard', 'Overview', 'chart', ['DIRECTOR']],
      ['leads', 'Lead inbox', 'people', ['SALES', 'DIRECTOR']],
      ['surveys', 'Site surveys', 'survey', ['SURVEYOR', 'SALES', 'DIRECTOR']],
      ['quotes', 'Quotes', 'document', ['SALES', 'DIRECTOR']],
      ['orders', 'Orders', 'bag', ['SALES', 'DIRECTOR']],
      ['installs', 'Installations', 'calendar', ['CREW', 'SUPPORT', 'DIRECTOR']],
    ],
  ],
  [
    'Fulfilment',
    [
      ['catalog', 'Catalog', 'apps', ['DIRECTOR', 'SALES']],
      ['inventory', 'Stock', 'box', ['WAREHOUSE', 'DIRECTOR']],
      ['deliveries', 'Deliveries', 'truck', ['WAREHOUSE', 'CREW', 'DIRECTOR']],
      ['invoices', 'Invoices', 'document', ['SALES', 'SUPPORT', 'DIRECTOR']],
      ['subsidy', 'Subsidy claims', 'leaf', ['SALES', 'DIRECTOR']],
    ],
  ],
  [
    'Service desk',
    [
      ['tickets', 'Tickets', 'ticket', ['SUPPORT', 'DIRECTOR']],
      ['lookup', 'Serial lookup', 'search', ['SUPPORT', 'WAREHOUSE', 'CREW', 'DIRECTOR']],
    ],
  ],
]
export const homeFor = (role) =>
  '/' +
  ({
    DIRECTOR: 'dashboard',
    SALES: 'leads',
    SURVEYOR: 'surveys',
    WAREHOUSE: 'inventory',
    CREW: 'installs',
    SUPPORT: 'tickets',
  }[role] || 'login')
export const human = (value) =>
  String(value ?? '')
    .toLowerCase()
    .replaceAll('_', ' ')
    .replace(/^./, (c) => c.toUpperCase())
