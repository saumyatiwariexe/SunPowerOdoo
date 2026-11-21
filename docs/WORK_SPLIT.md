# Work Split (4 people, Python backend)

Fill in names: Person A = ______ , B = ______ , C = ______ , D = ______.
Assign by strength: A = strongest Python/DB person. D = strongest frontend/UI person.

Split principle: each person owns **backend module + its frontend pages** end to end. Each defines their own models in `modules/<name>/models.py`, so nobody waits for a shared schema.

---
## Person A: Core + commercial (owns `app/core`, `main.py`, `models_registry.py`)
Folders: `core/`, `modules/users`, `catalog`, `quotes`, `orders`; `frontend/features/auth`, `catalog`, `quotes`, `orders`.

- [ ] Repo, `requirements.txt`, `docker-compose.yml` (Postgres), `.env.example`, run steps in README (**by 11:45**)
- [ ] `core/`: config, db session + base model with timestamps, `get_db`, security (bcrypt, JWT cookie), `get_current_user`, `require_roles`, `AppError` + handler, money helpers, numbering counter, upload helper, pagination helper (**by 12:15**)
- [ ] Base models pushed first so others can reference them: `User`, `Customer`, `Product`, `Order` (**by 12:00**)
- [ ] Auth routes: login, logout, me. Users CRUD and roles
- [ ] Catalog: products, packages, BOM editor; seed Solar Panel Set, On-Grid 1 to 5 kW and Off-Grid 1 to 5 kW packages, each system package including the Installation service line
- [ ] Quotes: create from package, BOM lines auto-filled (R3), survey gate (R2), send, accept, print view
- [ ] Orders: from quote, `confirm` with R4 and R5 in one transaction
- [ ] Core-chain test: lead -> order -> dispatch -> warranty (pytest)
- [ ] At the end (08:00): Alembic initial migration generated from the models
Depends on: C `surveys.is_approved`, B `billing.record_payment`, B `create_for_order`, C `create_for_order`.

---
## Person B: Warehouse, warranty, money
Folders: `modules/inventory`, `deliveries`, `warranty`, `billing`; `frontend/features/inventory`, `deliveries`, `invoices`.

- [ ] Models: `StockMovement`, `SerialUnit`, `Delivery`, `DeliveryLine`, `DeliveryScan`, `Warranty`, `Payment`, `Invoice`, `InvoiceLine`
- [ ] Stock list with low-stock flags; receive stock with bulk serial entry
- [ ] `create_for_order` (pick list from quote lines)
- [ ] Scan and unscan with R7 (row lock + unique constraint); progress per line
- [ ] Dispatch and deliver endpoints with R6
- [ ] `start_for_delivery` (R8) and `check_by_serial` (R9)
- [ ] Payments and invoices (order and ticket), invoice print view, `create_ticket_invoice` (R10)
- [ ] Warehouse UI: stock dashboard, receive, pick list, scan screen
- [ ] Seed: opening stock with serial numbers; one old delivered order with expired warranty for demo scene 8
Depends on: A's `Order`, `Product`, `Customer`; A's `orders.confirm` calls B.

---
## Person C: Field work and support
Folders: `modules/surveys`, `installs`, `tickets`; `frontend/features/surveys`, `installs`, `tickets`, `lookup`.

- [ ] Models: `Survey`, `InstallJob`, `InstallCrew`, `JobPhoto`, `Ticket`, `TicketLine`
- [ ] Surveys: schedule, submit with photos, approve and reject, `is_approved`
- [ ] Installs: `create_for_order`, crew assignment, conflict check (R13), week schedule board
- [ ] Crew mobile pages: my jobs, job detail, completion form with camera upload and signature canvas (R12)
- [ ] Tickets: serial lookup page (uses B's `check_by_serial`), create, board by status, lines, resolve, customer confirm, close (R9, R10, R11)
- [ ] Ticket close calls `billing.create_ticket_invoice` when out of warranty
- [ ] Seed: crew users, one scheduled job, one open ticket
Depends on: A's `Order`, `User`; B's warranty and billing (stub until ready).

---
## Person D: Front door, shell, reports, demo
Folders: `modules/leads`, `reports`, `subsidy`, `public`, `seed/seed_all.py`; `frontend/app`, `frontend/features/public`, `leads`, `dashboard`, `subsidy`.

- [ ] Models: `Lead`, `LeadCall`, `SubsidyClaim`
- [ ] **App shell first (by 12:30):** layout, role-based sidebar, protected routes, `api.js` fetch wrapper, shared components (Table, Field, Modal, Badge, EmptyState, Toast), theme colours
- [ ] Public landing page and enquiry form (validation, honeypot); `POST /public/enquiries`
- [ ] Leads inbox (polls every 15 s) and detail with call checklist, request survey, mark lost (R1); "New lead" form (`POST /leads`) for WhatsApp and phone enquiries
- [ ] Reports: summary (today / week / month), profit per job, unfinished work, monthly technician hours and amount due, CSV export, printable summary
- [ ] Dashboard UI: cards, one revenue chart, profit table
- [ ] Subsidy tracker
- [ ] `seed_all.py` runs every module's seed and creates demo users
- [ ] Demo rehearsal, screen recording, README screenshots
Depends on: everyone's data for reports (build with seed data first).

---
## Timeline (now 21 Nov 11:10 -> coding ends 22 Nov 10:00)
| Time | Phase | Goal |
|---|---|---|
| 11:10-12:30 | 0. Foundation | A: core + base models. D: app shell. B and C: write models and stub the contract functions. |
| 12:30-18:00 | 1. Vertical slices | Each person finishes their module against the real DB and UI. Merge to `main` every 2 hours. |
| 18:00-22:00 | 2. Integration | Run demo scenes 1-6 end to end. Fix hand-off bugs. |
| 22:00-02:00 | 3. Hardening | Validation, empty/error states, mobile checks, scenes 7-9, tests for R2, R4, R6, R8, R10. |
| 02:00-06:00 | Sleep shifts | Two sleep, two work. Swap at 04:00. |
| 06:00-08:30 | 4. Freeze | Feature freeze at 07:00. Bug fixes only. A adds Alembic. D records video. README final. |
| 08:30-09:50 | Final checks | Fresh clone, `docker compose up`, seed, run full demo. |
| 10:00 | Coding ends | Final push. 10:30 video links due. 13:00 presentation. |

## Merge and communication rules
1. Branch `feature/<module>-<thing>`, PR to `main`, reviewed by whoever depends on it.
2. `main` must always start with `docker compose up -d` + `uvicorn app.main:app --reload` + `npm run dev`.
3. Changes to `core/` or `models_registry.py`: ask A in chat; A merges within 15 minutes.
4. If blocked on another module, code against the contract in SYSTEM_DESIGN.md section 4 with a stub, then swap.
5. Stand-ups in chat at 14:00, 18:00, 22:00, 06:00: done, doing, blocked.

## Explainability checklist (judges ask)
Each person can explain, without notes: their tables, their state machine, the rules they enforce, and how other modules call theirs. Delete any code you cannot explain.
