import { lazy } from 'react'

// Feature owners can merge their page independently of the shell.
const pages = import.meta.glob([
  '../features/*/*Page.jsx',
  '!../features/public/**',
  '!../features/auth/LoginPage.jsx',
])
export function featurePage(file) {
  const load = pages[`../features/${file}Page.jsx`]
  return load ? lazy(load) : null
}

function moduleEntry(path, label, file, roles, color, icon) {
  return { path, label, roles, color, icon, Page: featurePage(file) }
}

export const modules = [
  moduleEntry('/leads', 'Leads', 'leads/Leads', ['SALES', 'DIRECTOR'], '#258d89', 'people'),
  moduleEntry('/quotes', 'Quotes', 'quotes/Quotes', ['SALES'], '#b35b71', 'document'),
  moduleEntry('/orders', 'Orders', 'orders/Orders', ['SALES'], '#b67b36', 'bag'),
  moduleEntry('/dashboard', 'Dashboard', 'dashboard/Dashboard', ['DIRECTOR'], '#80639c', 'chart'),
  moduleEntry('/subsidy', 'Subsidy', 'subsidy/Subsidy', ['DIRECTOR'], '#568958', 'leaf'),
  moduleEntry('/surveys', 'Surveys', 'surveys/Surveys', ['SURVEYOR', 'SALES', 'DIRECTOR'], '#697fa7', 'survey'),
  moduleEntry('/inventory', 'Inventory', 'inventory/Inventory', ['WAREHOUSE'], '#b67b36', 'box'),
  moduleEntry('/deliveries', 'Deliveries', 'deliveries/Deliveries', ['WAREHOUSE'], '#258d89', 'truck'),
  moduleEntry('/installs', 'Install jobs', 'installs/Installs', ['CREW', 'SUPPORT', 'DIRECTOR'], '#5b8799', 'calendar'),
  moduleEntry('/tickets', 'Tickets', 'tickets/Tickets', ['SUPPORT'], '#b35b71', 'ticket'),
  moduleEntry('/lookup', 'Serial lookup', 'lookup/Lookup', ['SUPPORT'], '#697fa7', 'search'),
  moduleEntry('/invoices', 'Invoices', 'invoices/Invoices', ['DIRECTOR'], '#ad687b', 'document'),
  moduleEntry('/catalog', 'Catalog', 'catalog/Catalog', ['DIRECTOR'], '#ae8844', 'box'),
  moduleEntry('/users', 'Users', 'auth/Users', ['DIRECTOR'], '#6279a0', 'people'),
]
