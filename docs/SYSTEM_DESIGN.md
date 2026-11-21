# System Design: SunPower Solar Installation Management System

## 1. Goal
One platform that carries a customer from first enquiry to the 20-year warranty:
enquiry -> survey -> quote -> order + advance -> pick/dispatch with serial scans -> install proof
-> warranty clock -> service tickets -> director dashboard.

## 2. Stack (simple, production-shaped, every item has a job)
| Layer | Choice | Practical reason |
|---|---|---|
| Language | Python 3.11 | Same language family as Odoo; readable for the whole team |
| API | FastAPI + Uvicorn | Automatic validation and a free interactive API page at `/docs` for testing and the demo |
| Validation | Pydantic v2 (built into FastAPI) | Odoo's must-have: robust input validation |
| ORM | SQLAlchemy 2.0 | Real transactions and constraints |
| Database | PostgreSQL (docker-compose). SQLite for tests | Real DB for the demo; fast tests |
| Migrations | Alembic, added at the end by Person A | During the hackathon we use `create_all` plus a reset-and-seed script, because four people editing one migration history will conflict |
| Auth | JWT in an httpOnly cookie (PyJWT), `bcrypt` | Secure default, no extra services |
| Files | Local `uploads/` folder via `python-multipart` | Works offline, no cloud |
| Dates | `python-dateutil` (`relativedelta`) | Correct "add 24 months" for warranties |
| Tests | pytest + FastAPI TestClient | Prove the key rules hold |
| Frontend | React + Vite + React Router + Tailwind, plain `fetch` wrapper | Responsive UI, no state library |

Deliberately NOT used: microservices, Celery/Redis, GraphQL, websockets (leads list polls every 15 s), payment gateways, cloud storage, Kubernetes. None would improve the demo or the scoring.

## 3. Architecture: modular monolith
One backend, one database, one process. Each module owns its tables and exposes service functions.

```
backend/
  app/
    main.py                  create app, include routers, CORS, error handlers      (A)
    models_registry.py       imports every module's models.py (one line per module) (A)
    core/                    config, db session, security, deps (current user, require_roles),
                             errors, money, numbering, uploads, pagination          (A)
    modules/
      users/ catalog/ quotes/ orders/                      (A)
      inventory/ deliveries/ warranty/ billing/            (B)
      surveys/ installs/ tickets/                          (C)
      leads/ reports/ subsidy/ public/                     (D)
        models.py   schemas.py   service.py   router.py    (every module has these four files)
  seed/                      seed_<module>.py per module; seed_all.py runs all           (D)
  tests/                     test_<rule>.py
  requirements.txt
frontend/src/
  app/                       router, layout, nav, shared components, api.js              (D)
  features/<module>/         pages for that module                                       (owner)
```

Rules
1. A module writes only its own tables. Other modules call its service functions.
2. `router.py` is thin: parse request -> call service -> commit -> return. Logic lives in `service.py`.
3. **Transactions:** services take a `db: Session`, call `db.flush()` and never `db.commit()`. The router commits once at the end. So a multi-module action (confirm order, complete delivery) is one atomic transaction and rolls back fully on any error.
4. Each person defines their own models in their module, using string foreign keys such as `ForeignKey("orders.id")`. No shared schema file, so nobody waits for anybody.
5. Raw SQL only inside `reports`.

## 4. Cross-module contracts (Python signatures)
Fixed now so people can stub each other.

| Function | Owner | Called by | Effect |
|---|---|---|---|
| `catalog.service.get_package_bom(db, package_id)` | A | quotes | Parts list of a package |
| `surveys.service.is_approved(db, lead_id)` | C | quotes | Gate for R2 |
| `quotes.service.convert_to_order(db, quote_id)` | A | router | Creates Order from accepted quote |
| `billing.service.record_payment(db, order_id, amount_paise, method, user_id)` | B | router | Adds payment, updates paid total |
| `orders.service.confirm(db, order_id)` | A | router | Checks advance (R4), then calls the next two in the same session |
| `deliveries.service.create_for_order(db, order_id)` | B | orders.confirm | Pick list from the quote lines |
| `installs.service.create_for_order(db, order_id)` | C | orders.confirm | Install job on the schedule |
| `deliveries.service.complete(db, delivery_id)` | B | router | Needs all serials scanned (R6), then calls warranty |
| `warranty.service.start_for_delivery(db, delivery_id)` | B | deliveries | One warranty per serial |
| `warranty.service.check_by_serial(db, serial_no)` | B | tickets, lookup | Serial, customer, in/out of warranty |
| `billing.service.create_ticket_invoice(db, ticket_id)` | B | tickets.close | Bills parts and labour when out of warranty |
| `reports.service.*` | D | dashboard | Read-only aggregates |

## 5. Business rules (enforce these and demo them)
- R1 A lead is never deleted; it can only be marked LOST with a reason.
- R2 A quote cannot be created until the lead's survey is APPROVED.
- R3 A quote is generated from a package template; its parts list comes from the package BOM, not typed by hand.
- R4 An order can be CONFIRMED only when payments received >= advance minimum (assumption: 30% of total, one config value).
- R5 Confirming an order creates exactly one delivery (pick list) and one install job.
- R6 A delivery cannot be completed unless every serialized line has its required count of scanned serials.
- R7 A serial can be scanned only if it is IN_STOCK and not on another delivery (database unique constraint is the final guard).
- R8 Completing delivery creates one warranty per serial: inverter 24 months, battery 24 months, panels 240 months (`Product.warranty_months`).
- R9 A ticket is found by serial number; warranty status is computed, never typed.
- R10 In-warranty ticket: customer billed 0. Out-of-warranty: parts + labour invoice is created automatically.
- R11 A ticket closes only after customer confirmation is recorded.
- R12 Install completion needs start and finish time, system kW, at least one photo and a signature.
- R13 A crew member cannot have overlapping install slots.
- R14 Money is stored as integer paise, never floats.

## 6. State machines (allowed transitions checked in services)
- Lead: NEW -> CONTACTED -> SURVEY_PENDING -> SURVEY_DONE -> QUOTED -> WON | LOST
- Survey: SCHEDULED -> SUBMITTED -> APPROVED | REJECTED
- Quote: DRAFT -> SENT -> ACCEPTED | REJECTED | EXPIRED
- Order: DRAFT -> CONFIRMED -> DISPATCHED -> INSTALLED -> CLOSED (CANCELLED from DRAFT or CONFIRMED)
- Delivery: PENDING -> DISPATCHED -> DELIVERED
- InstallJob: SCHEDULED -> IN_PROGRESS -> COMPLETED -> ACCEPTED (customer signed)
- Ticket: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED
- Serial: IN_STOCK -> DISPATCHED -> INSTALLED

## 7. API conventions
- Base path `/api/v1`. JSON only. Auth cookie required except `/public/*` and `/auth/login`.
- Success: `{ "data": ..., "meta": { "page", "page_size", "total" } }`
- Error: `{ "error": { "code": "RULE_VIOLATION", "message": "...", "details": [...] } }`
- Codes: 400 validation, 401 not logged in, 403 wrong role, 404 not found, 409 rule or state violation.
- Lists accept `page`, `page_size`, `q`, `status`.
- Dates ISO-8601 UTC, IDs integers, money in paise, JSON field names snake_case.
- Raise `AppError(code, message, status)` from services; one handler in `main.py` formats it.
- Order numbers (`QT-0001`, `ORD-0001`, `INV-0001`, `TKT-0001`) come from `core/numbering.py` using a locked counter row.

## 8. Security and quality baseline
- `bcrypt` passwords, login rate limit (simple in-memory counter is fine), CORS locked to the frontend origin.
- Pydantic models reject unknown fields (`extra="forbid"`).
- Role check as a dependency: `Depends(require_roles("SALES", "DIRECTOR"))`.
- Uploads: jpeg, png, webp only, max 5 MB, random file names.
- Every table has `created_at`, `updated_at` from a shared mixin in `core/db.py`.
- Add DB indexes on lookup columns (serial_no, phone, status, number).
- Seed script creates a demo user for every role and one complete sample project plus one old delivered order for the warranty demo.

## 9. UI baseline
- One colour scheme and layout, role-based sidebar, responsive to phone width.
- Crew and warehouse scan screens are mobile-first (large inputs and buttons).
- Every form shows inline validation errors; every list has loading, empty and error states.
- Print views (quote, invoice, dashboard summary) use a print stylesheet; no PDF library needed.

## 10. Git workflow
- `main` always runs. Branch `feature/<module>-<thing>`, PR into `main`, reviewed by the person who depends on it.
- Small, frequent commits from everyone, message format `module: what changed`.
- Never edit another person's module folder without telling them. Shared files (`core/`, `models_registry.py`) belong to A: ask in chat, A merges within 15 minutes.

## 11. Definition of done (per feature)
1. Pydantic validation. 2. Role check. 3. Rule violations return 409 with a clear message.
4. UI has loading, empty, error states. 5. Seed data exercises it. 6. It appears in the demo script.
