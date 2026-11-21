# Features by Role (windows, features, endpoints, owner)

Owner letters: A, B, C, D = the four team members (see WORK_SPLIT.md).
Each role is a login with its own sidebar. Seed one demo user per role.

## 0. Public visitor / Customer (no login) , Owner: D
Windows
- Landing page: company, packages 1-5 kW (On-Grid / Off-Grid), subsidy note, enquiry CTA.
- Enquiry form: name, phone, address, pincode, requested kW, system type, subsidy interest, monthly bill (optional).
- Thank-you page with enquiry reference number.
- Signature screen is shown to the customer on the crew's device (built by C).
Endpoints: `POST /public/enquiries`, `GET /public/packages`
Rules: phone and pincode validated, honeypot field against bots, duplicate phone within 10 minutes attaches to the same lead.

## 1. Sales , Owner: D (leads), A (quotes/orders), B (payments)
Windows
1. Lead inbox (D): list by status, filters, source badge, "assigned to me". New leads appear at the top automatically. A "New lead" button lets Sales enter enquiries that arrive by WhatsApp or phone (source selectable: WEB, WHATSAPP, CALL).
2. Lead detail (D): customer info, timeline, call checklist form (shadow-free area, monthly bill, grid suitability), buttons "Request survey" and "Mark lost" (reason required).
3. Quote builder (A): choose package, parts list auto-fills from BOM, edit quantities and prices, subsidy line, send/print quote. Blocked until survey is approved.
4. Quote list and quote print view (A).
5. Order detail (A): status, payments received, "Record payment" (B's API), "Confirm order" (disabled until advance paid).
Endpoints
- D: `POST /leads` (manual entry), `GET/PATCH /leads`, `POST /leads/:id/calls`, `POST /leads/:id/lost`
- A: `POST /quotes`, `GET/PATCH /quotes/:id`, `POST /quotes/:id/send`, `POST /quotes/:id/accept`, `POST /orders/:id/confirm`
- B: `POST /orders/:id/payments`

## 2. Surveyor , Owner: C
Windows
1. My surveys (mobile friendly): scheduled visits list.
2. Survey form: roof direction, tilt, cable distance, shadow notes, photos, submit.
3. Survey review (Sales/Director): approve or reject with note.
Endpoints: `POST /leads/:id/survey` (schedule), `GET /surveys/mine`, `POST /surveys/:id/submit`, `POST /surveys/:id/approve`, `POST /surveys/:id/reject`

## 3. Warehouse , Owner: B
Windows
1. Stock dashboard: products, on-hand, low-stock badges (below reorder level).
2. Receive stock: choose product, enter quantity, scan or type serial numbers in bulk, purchase cost.
3. Pick list: opens automatically after order confirmation; shows required lines (e.g., 1 inverter, 6 panels, 1 charge controller).
4. Dispatch scan screen: scan or type serials per line; wrong or duplicate serial gives a clear error; progress bar per line; "Complete dispatch" enabled only when all required serials are scanned.
5. Delivery confirmation: mark delivered, which starts warranty.
Endpoints: `GET /products`, `POST /stock/receive`, `GET /deliveries`, `GET /deliveries/:id`, `POST /deliveries/:id/scan`, `DELETE /deliveries/:id/scan/:serialUnitId`, `POST /deliveries/:id/dispatch`, `POST /deliveries/:id/deliver`
Rules: R6, R7, R8.

## 4. Installation crew (mobile-first) , Owner: C
Windows
1. My jobs: today and upcoming, address, map link, customer phone, kW.
2. Job detail: what to install, serials delivered, checklist.
3. Completion form: start time, finish time, system kW confirm, test result, photos (camera upload), customer signature on screen, submit.
4. Scheduling board (Director/Support): week view of jobs per crew, conflict warnings.
Endpoints: `GET /installs/mine`, `POST /installs/:id/start`, `POST /installs/:id/photos`, `POST /installs/:id/complete`, `POST /installs/:id/accept` (signature), `PATCH /installs/:id/schedule`
Rules: R12, R13.

## 5. Support , Owner: C (tickets), B (billing hook)
Windows
1. Serial lookup (search bar always visible): enter serial or phone; shows customer, product, install date, warranty status (green/red) with end date.
2. New ticket from the lookup: fault code, description, priority.
3. Ticket board: kanban by status, assignment, filters.
4. Ticket detail: add parts and labour lines, resolution, "Customer confirmed" button, close.
5. Auto-bill: if out of warranty, closing creates an invoice; in warranty shows "No charge".
Endpoints: `GET /lookup?serial=` , `POST /tickets`, `GET/PATCH /tickets/:id`, `POST /tickets/:id/lines`, `POST /tickets/:id/resolve`, `POST /tickets/:id/confirm`, `POST /tickets/:id/close`
Rules: R9, R10, R11.

## 6. Director / Admin , Owner: D (dashboard), B (invoices), A (users, catalog)
Windows
1. Dashboard: tabs Today / This week / This month. Cards: revenue, collected, outstanding, jobs completed, jobs unfinished, open tickets, low stock. Chart: revenue trend. Table: profit per job (green/red), sortable.
2. Unfinished work: orders stuck at each step (awaiting survey, awaiting payment, awaiting dispatch, awaiting install). Also a monthly technician hours summary: hours worked and amount due per technician (hours x hourly rate), taken from install jobs and tickets.
3. Invoices (B): list, create, print view, payment status, record payment.
4. Subsidy tracker (D): per order status and reference number.
5. Share report (D): download CSV and a printable summary page.
6. Catalog manager (A): products, packages and BOM editor. Seed packages: Solar Panel Set (hardware only), On-Grid 1 to 5 kW, Off-Grid 1 to 5 kW. Every On-Grid and Off-Grid package includes the Installation service line, so each quote shows it.
7. Users and roles (A): create staff, assign role, set hourly rate.
Endpoints
- D: `GET /reports/summary?range=`, `GET /reports/profit-per-job`, `GET /reports/unfinished`, `GET /reports/technician-hours?month=`, `GET /reports/export.csv`, `GET/PATCH /subsidy`
- B: `GET/POST /invoices`, `GET /invoices/:id`
- A: `GET/POST/PATCH /products`, `/packages`, `/users`

## Demo script (every scene in order; all four rehearse it)
1. Visitor submits a 3 kW enquiry -> lead appears for Sales.
2. Sales logs call checklist -> requests survey -> surveyor submits -> approved.
3. Sales builds quote from the 3 kW On-Grid template, parts auto-filled -> accepted -> order.
4. Record advance payment -> confirm order -> pick list and install job appear on their own.
5. Warehouse scans serials -> dispatch -> delivered -> warranty rows appear (2 and 20 years).
6. Crew completes the job on a phone with photos and signature.
7. 18 months later (use a seeded old job): support finds the serial, sees warranty status, opens ticket.
8. In-warranty: free. Out-of-warranty: invoice generated automatically.
9. Director dashboard: profit per job, open tickets, unfinished work, export.
