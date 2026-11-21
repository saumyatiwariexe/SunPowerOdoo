# SunPower codebase manual

This is the developer reference for the current checkout. It explains how a request moves through the system and gives a purpose for every project file. For screen instructions and each visible control, use [the user guide](USER_GUIDE.md). The design and work-split documents describe intentions; the source files listed here define current behavior.

## Run the project

From the repository root, copy `.env.example` to `.env`, set a fresh `JWT_SECRET` of at least 32 characters, then start PostgreSQL with `docker compose up -d --wait db`. From `backend/`, create and activate a Python 3.11 virtual environment, install `requirements.txt`, run `python -m seed.seed_all`, then `python -m uvicorn app.main:app --reload`. From `frontend/`, run `npm install` and `npm run dev`. The public UI uses port 5173; the API uses port 8000 and exposes interactive documentation at `/docs`. Run `python -m pytest` from `backend/` and `npm run build` from `frontend/` for basic verification.

The backend reads `.env` from the repository root. `DATABASE_URL` overrides individual PostgreSQL settings; a disposable `sqlite:////tmp/...` URL can be used for a local rehearsal, but PostgreSQL is the documented development database. The seed creates tables with `create_all` and adds demo data if missing. It does not run migrations. Do not use the demo credentials or a development JWT secret for a deployed system.

The Vite dev server proxies `/api` to the backend. Set `API_PROXY_TARGET` when the API is not at `http://127.0.0.1:8000`. The frontend never calls the database directly.

## How the application works

```text
Browser page → frontend/src/app/api.js → /api/v1 router → Pydantic schema
             → module service → SQLAlchemy models → database
             → {data, meta} or {error} → page state
```

`main.py` registers the routers, CORS policy and error handlers. A router checks authentication and roles, calls a service and commits a successful write once. A service may call another module's service using the same SQLAlchemy session; it flushes for generated IDs but does not commit. If a step fails, the transaction rolls back. `models_registry.py` imports all table models before seeding. The database holds integer paise, UTC timestamps, status values and unique constraints. `core/numbering.py` uses a counter row for `QT`, `ORD`, `INV` and `TKT` numbers.

The important chain is enquiry or manual lead → call → scheduled survey → approved survey → package quote → accepted quote and draft order → advance payment → confirmed order with one delivery and one install job → serial scans and dispatch → delivered serials and warranties → signed installation → service lookup and tickets → invoices and reports. The [system design](SYSTEM_DESIGN.md) lists the 14 business rules; the [user guide](USER_GUIDE.md) explains what staff do at each step.

The API prefix is `/api/v1`. List responses normally contain `data` and pagination `meta`; failures contain an `error` with `code`, `message` and `details`. Business-rule conflicts return 409, missing authentication 401, forbidden roles 403 and absent records 404. Field validation usually returns 400, with 422 for unknown fields and public enquiry phone or pincode errors. The shared frontend API helper includes the session cookie on requests and converts error details for forms.

## API areas and owning modules

| Area | Main routes | What it owns |
| --- | --- | --- |
| Auth and staff | `/auth/login`, `/auth/logout`, `/auth/me`, `/users` | Sessions, director-managed accounts and customer records |
| Public | `/public/health`, `/public/packages`, `/public/enquiries` | Public catalog and enquiry entry point |
| Leads | `/leads`, `/leads/{id}/calls`, `/lost`, `/survey-request` | Lead lifecycle and call history |
| Surveys | `/surveys`, `/surveys/mine`, `/surveys/scheduling-options`, `/leads/{id}/survey`, survey photos/submit/approve/reject | Site assessment and quote approval gate |
| Catalog | `/products`, `/packages` and item detail/update paths | Products, package templates and BOM lines |
| Quotes and orders | `/quotes`, `/quotes/{id}/send`, `/accept`, `/orders`, `/orders/{id}/confirm` | Quoting, acceptance and advance gate |
| Stock and delivery | `/stock`, `/stock/receive`, `/deliveries`, delivery scan/dispatch/deliver paths | Stock movements, serials and pick lists |
| Installations | `/installs`, `/installs/mine`, job schedule/start/photos/complete/accept paths | Crew slots and installation proof |
| Warranty and tickets | `/lookup`, `/tickets` and ticket line/resolve/confirm/close paths | Coverage calculation and service work |
| Billing | `/orders/{id}/payments`, `/invoices`, `/invoices/{id}/payments` | Receipts and order or ticket invoices |
| Subsidy and reports | `/subsidy`, `/reports/summary`, `/profit-per-job`, `/unfinished`, `/technician-hours`, `/export.csv` | Claim tracking and director metrics |

For exact request and response schemas, use `/docs` while the API runs. The table is an orientation map; each `router.py` is the authoritative route list.

The UI exposes lead name/phone search, ticket-number search, serial/phone lookup and the low-stock toggle. API consumers have more filters: `GET /leads?q=&status=` searches customer name or phone; `/products?q=` searches product name or SKU; `/packages?q=&status=` searches package name and filters active state; `/quotes?q=&status=` searches quote number; `/stock?q=&low_stock=` searches product name or SKU and filters products at or below reorder level; `/tickets?q=&status=&assigned_to_id=` searches ticket number and filters stage or assignee; `/subsidy?status=` filters claim stage. All list query parameters are optional. The serial lookup takes exactly one of `serial` or `phone`; phone lookup is an exact customer phone match. See each router for validation limits and role access.

## Root and project documentation files

| File | Purpose |
| --- | --- |
| `.env.example` | Template for database name, user, password, host/port, JWT secret, frontend origin, cookie mode and advance percentage. Copy to ignored `.env` for local values. |
| `.gitignore` | Keeps local virtual environments, bytecode, `.env`, uploaded images, build outputs and dependencies out of Git. |
| `AGENTS.md` | Team-wide ownership, rules R1–R14, conventions, setup and definition of done. |
| `BUGS.md` | Integration QA history, observed defects and release verification notes; it is evidence from earlier checkouts, not a live bug list. |
| `README.md` | Short project introduction, setup commands, test command, demo login list and documentation links. |
| `docker-compose.yml` | PostgreSQL 17 service, environment values, localhost port mapping, persistent named volume and health check. |
| `docs/SYSTEM_DESIGN.md` | Planned architecture, cross-module service contracts, business rules, state machines and API conventions. |
| `docs/DATA_MODEL.md` | Table ownership, key fields, profit formula and warranty date calculation. |
| `docs/FEATURES_BY_ROLE.md` | Intended screens and endpoints for each role, plus demo order. |
| `docs/WORK_SPLIT.md` | Four-person ownership, timeline and coordination rules. |
| `docs/USER_GUIDE.md` | Current UI controls, searches, forms, role access and task-by-task instructions. |
| `docs/CODEBASE_MANUAL.md` | This file: architecture, operation and file catalog. |

## Backend core files

| File | Purpose and key behavior |
| --- | --- |
| `backend/AGENTS.md` | Backend module layout and the session/commit/role rules for contributors. |
| `backend/requirements.txt` | Python runtime and test dependency ranges. |
| `backend/app/main.py` | Creates FastAPI, CORS, error handlers and `/api/v1/public/health`; includes every feature router. |
| `backend/app/models_registry.py` | Imports all ORM models so `Base.metadata.create_all` sees every table; public and reports add no tables. |
| `backend/app/core/config.py` | Reads `.env`, builds PostgreSQL or `DATABASE_URL` connection, and holds JWT, cookie, upload and advance settings. |
| `backend/app/core/db.py` | SQLAlchemy base, UTC-aware datetime type, timestamp mixin, cached engine and per-request session dependency. |
| `backend/app/core/deps.py` | Reads the signed session cookie, loads an active user and enforces allowed roles. |
| `backend/app/core/errors.py` | `AppError` and handlers that make a consistent JSON error envelope, including field errors. |
| `backend/app/core/money.py` | Strict nonnegative integer-paise type and advance minimum rounded up to a whole paise. |
| `backend/app/core/numbering.py` | Counter model and locked increment for quote, order, invoice and ticket numbers. |
| `backend/app/core/pagination.py` | Validates `page` and `page_size`, computes offset and creates list metadata. |
| `backend/app/core/security.py` | bcrypt password hashing, JWT session creation/checking and cookie constants. |
| `backend/app/core/uploads.py` | Enforces 5 MiB JPEG/PNG/WebP image content and writes random names in local uploads. |

Each feature module generally has four files: `models.py` declares owned tables and constraints; `schemas.py` declares validated input and output shapes; `service.py` implements rules and transaction-safe operations; `router.py` exposes authenticated HTTP routes and commits writes. The rows below identify what each file contributes beyond that shared pattern.

## Backend feature files

| File | Purpose and key behavior |
| --- | --- |
| `backend/app/modules/users/models.py` | `User`, `Customer` and role values; staff identity, credentials and customer contact fields. |
| `backend/app/modules/users/schemas.py` | Login, staff create/update and output shapes; forbids extra inputs. |
| `backend/app/modules/users/service.py` | Authentication, login attempt limiter, staff listing and changes; protects the last active director. |
| `backend/app/modules/users/router.py` | Login/logout/current-user routes and director-only staff list/create/detail/update. |
| `backend/app/modules/catalog/models.py` | Products, package templates and BOM items, categories, system types, SKU/name constraints and stock count. |
| `backend/app/modules/catalog/schemas.py` | Product and package inputs/outputs, including BOM item validation and paise fields. |
| `backend/app/modules/catalog/service.py` | Product/package CRUD, stock adjustment, BOM replacement, duplicate checks and required installation service line. |
| `backend/app/modules/catalog/router.py` | Product/package list/detail/create/update; director writes and role-limited reads. |
| `backend/app/modules/quotes/models.py` | Quote and quote-line tables with status, totals, source lead/package and copied part prices. |
| `backend/app/modules/quotes/schemas.py` | Quote creation, draft patch and response fields; validates lines, subsidy and validity date. |
| `backend/app/modules/quotes/service.py` | Requires approved survey and active package, copies BOM, reprices draft, sends and accepts a quote once. |
| `backend/app/modules/quotes/router.py` | Sales/director quote list/create/detail/edit/send/accept endpoints. |
| `backend/app/modules/orders/models.py` | Order table and status, unique quote link, total, minimum advance and confirmation time. |
| `backend/app/modules/orders/schemas.py` | Order list and detail response shapes, including total received on detail. |
| `backend/app/modules/orders/service.py` | Creates one draft order, checks received advance, confirms and creates delivery/install/claim in one transaction. |
| `backend/app/modules/orders/router.py` | Sales/director order list/detail/confirm endpoints. |
| `backend/app/modules/inventory/models.py` | Stock movement history and individually tracked serial units with unique serial number and status. |
| `backend/app/modules/inventory/schemas.py` | Stock-receipt input, serial list and stock response validation. |
| `backend/app/modules/inventory/service.py` | Stock list/low-stock filter, receipt, exact serialized count and duplicate checks. |
| `backend/app/modules/inventory/router.py` | Stock read and warehouse/director receipt routes. |
| `backend/app/modules/deliveries/models.py` | Delivery, pick-list lines and scan records; unique order and serial assignment guards. |
| `backend/app/modules/deliveries/schemas.py` | Serial scan and dispatch input contracts. |
| `backend/app/modules/deliveries/service.py` | Builds pick list from quote, scans/unscans stock serials, checks counts, dispatches and completes delivery. |
| `backend/app/modules/deliveries/router.py` | Delivery list/detail and role-checked scan/remove/dispatch/deliver routes. |
| `backend/app/modules/warranty/models.py` | Warranty per serial with customer/order, start/end dates and status. |
| `backend/app/modules/warranty/schemas.py` | Warranty output and lookup result types. |
| `backend/app/modules/warranty/service.py` | Starts coverage on delivery using product months; computes current serial/phone lookup and warranty status. |
| `backend/app/modules/warranty/router.py` | Authenticated `/lookup` by exactly one serial or phone value. |
| `backend/app/modules/billing/models.py` | Payments, invoices and invoice lines, including order or ticket origin and paid totals. |
| `backend/app/modules/billing/schemas.py` | Payment and invoice input/output data with integer-paise validation. |
| `backend/app/modules/billing/service.py` | Records receipts, links order advances to invoices, creates order/ticket invoices and updates payment status. |
| `backend/app/modules/billing/router.py` | Order and invoice payments, invoice list/create/detail with sales/support/director role checks. |
| `backend/app/modules/surveys/models.py` | Survey and survey-photo tables, status, roof measurements and review metadata. |
| `backend/app/modules/surveys/schemas.py` | Schedule, submission, review and survey output validation. |
| `backend/app/modules/surveys/service.py` | Eligible scheduling choices, one active survey per lead, assigned surveyor work and approval gate. |
| `backend/app/modules/surveys/router.py` | Schedule/list/mine/detail, photo upload, submit, approve/reject and photo serving. |
| `backend/app/modules/installs/models.py` | Install job, crew membership and job photos, schedule/proof/status fields. |
| `backend/app/modules/installs/schemas.py` | Schedule and completion inputs, including crew IDs, aware timestamps and required proof data. |
| `backend/app/modules/installs/service.py` | One job per confirmed order, active-crew and slot conflict checks, start/photo/complete/accept transitions. |
| `backend/app/modules/installs/router.py` | Job list/mine/detail, scheduling, start, photo and signature upload, completion, acceptance and media serving. |
| `backend/app/modules/tickets/models.py` | Ticket, ticket-line, status and priority data tied to customer and serial. |
| `backend/app/modules/tickets/schemas.py` | Ticket creation/patch, part/labour line and resolution validation. |
| `backend/app/modules/tickets/service.py` | Warranty-based ticket creation, assignment, work stages, customer confirmation and conditional invoice at close. |
| `backend/app/modules/tickets/router.py` | Support/director ticket list/create/detail/edit/line/resolve/confirm/close routes. |
| `backend/app/modules/leads/__init__.py` | Marks the leads directory as an importable Python package. |
| `backend/app/modules/leads/models.py` | Lead and call tables, source/system/status values, transitions and lost reason. |
| `backend/app/modules/leads/schemas.py` | Manual lead, customer, call, update and lost-reason input/output validation. |
| `backend/app/modules/leads/service.py` | Name/phone search, lead creation, first-call transition, survey request and reasoned loss. |
| `backend/app/modules/leads/router.py` | Lead list/create/detail/update, lost, calls and survey-request routes. |
| `backend/app/modules/public/__init__.py` | Marks the public module as importable. |
| `backend/app/modules/public/models.py` | Empty placeholder: public enquiries use the existing customer and lead tables. |
| `backend/app/modules/public/schemas.py` | Public enquiry input, phone/pincode and hidden-field validation, plus returned reference. |
| `backend/app/modules/public/service.py` | Creates customer/lead or returns a same-phone lead submitted in the prior ten minutes; lists active packages. |
| `backend/app/modules/public/router.py` | Anonymous enquiry submission and public package listing. |
| `backend/app/modules/reports/__init__.py` | Marks the reports module as importable. |
| `backend/app/modules/reports/models.py` | Empty placeholder: reports read other modules' tables and own no tables. |
| `backend/app/modules/reports/schemas.py` | Summary, profit, unfinished-work and technician-hours response shapes. |
| `backend/app/modules/reports/service.py` | India-time period boundaries, aggregate SQL, profit and hours calculations and CSV generation. |
| `backend/app/modules/reports/router.py` | Director-only summary, profit, unfinished, hours and CSV download endpoints. |
| `backend/app/modules/subsidy/__init__.py` | Marks the subsidy module as importable. |
| `backend/app/modules/subsidy/models.py` | Claim table, status and unique order association. |
| `backend/app/modules/subsidy/schemas.py` | Claim list/detail/update fields with paise validation. |
| `backend/app/modules/subsidy/service.py` | Creates a claim for interested confirmed orders and lists/updates existing claims. |
| `backend/app/modules/subsidy/router.py` | Sales/director claim list/detail/update. |

## Seed and test files

| File | Purpose |
| --- | --- |
| `backend/seed/seed_all.py` | Imports model registry, creates all tables and runs counter, user, lead, catalog, stock, historical delivery, survey and claim seed steps in one transaction. |
| `backend/seed/seed_b.py` | Opens stock and serialized units, plus an older paid order/delivery with one expired inverter and one covered panel warranty. |
| `backend/seed/seed_catalog.py` | Creates products and 1–5 kW on/off-grid packages with BOMs; updates older controller entries without overwriting negotiated prices. |
| `backend/seed/seed_inventory.py` | Runs warehouse stock seed and fills missing controller serials for untouched old demo stock. |
| `backend/seed/seed_leads.py` | Creates example contacted, lost, survey-pending and new leads with customers and a call. |
| `backend/seed/seed_subsidy.py` | Backfills missing claim index/claims for eligible previously confirmed orders. |
| `backend/seed/seed_surveys.py` | Schedules the demo pending lead for the demo surveyor. |
| `backend/seed/seed_users.py` | Creates one user per role if missing; `seed_all.py` supplies the demo password. |
| `backend/tests/test_catalog.py` | Checks product roles, paise, SKU uniqueness, BOM edits and seed/public catalog behavior. |
| `backend/tests/test_commercial_handoffs.py` | End-to-end rule tests across surveys, quote/order, delivery, install, warranty, tickets, reports and seed. |
| `backend/tests/test_core.py` | Checks auth, cookie/roles, staff changes, rollback, upload rules, health/CORS and settings. |
| `backend/tests/test_quote_order.py` | Checks quote send/accept, one order, expiry and rollback on failed conversion. |
| `backend/tests/test_r1_lead_lost.py` | Checks lead loss requires a reason and preserves records. |
| `scripts/smoke_demo.py` | Exercises the multi-role demo against a running API and throwaway database; it creates records. |
| `scripts/smoke_ui.cjs` | Browser smoke checks for routes, layout, flows and print views. |

## Frontend foundation and shared files

| File | Purpose and key behavior |
| --- | --- |
| `frontend/AGENTS.md` | Frontend ownership, API wrapper, mobile layout and form-state conventions. |
| `frontend/.gitignore` | Ignores installed Node packages and built output within `frontend/`. |
| `frontend/package.json` | React, React Router, Vite, Tailwind dependencies and `dev`, `build`, `preview` scripts. |
| `frontend/package-lock.json` | Generated npm dependency lock from local install; use it for reproducible installs if the team chooses to track it. |
| `frontend/index.html` | HTML shell and `root` element for React. |
| `frontend/postcss.config.js` | PostCSS plugin setup for Tailwind and autoprefixer. |
| `frontend/tailwind.config.js` | Tailwind content paths and theme extensions. |
| `frontend/vite.config.js` | React plugin, port 5173 and `/api` proxy to the API. |
| `frontend/public/fonts/OFL.txt` | Open Font License for the bundled font. |
| `frontend/public/fonts/instrument-sans.woff2` | Bundled Instrument Sans font loaded by the stylesheet. |
| `frontend/public/solar-array.jpg` | Solar photograph for the public landing and login screens. |
| `frontend/public/sunpower.svg` | SunPower brand mark. |
| `frontend/src/main.jsx` | Mounts React and loads the main stylesheet. |
| `frontend/src/index.css` | Theme, responsive layout, component styles and print rules. |
| `frontend/src/app/App.jsx` | Defines public and protected routes and maps menu sections to pages. |
| `frontend/src/app/navigation.js` | Sidebar labels/roles, role home destinations and status label formatting. |
| `frontend/src/app/api.js` | Credentialed fetch wrapper, JSON/error envelopes, uploads, CSV access and rupee/paise display helpers. |
| `frontend/src/app/AuthContext.jsx` | Loads current user, signs in/out and shares account state. |
| `frontend/src/app/ProtectedRoute.jsx` | Redirects unsigned users to login and wrong-role users to their home page. |
| `frontend/src/app/Layout.jsx` | Workspace header, responsive navigation dialog and content outlet. |
| `frontend/src/app/Sidebar.jsx` | Role-filtered navigation, brand/home link, profile link and sign-out button. |
| `frontend/src/app/Brand.jsx` | Reusable SunPower logo/link for public and staff layouts. |
| `frontend/src/app/AppIcon.jsx` | Shared SVG icon rendering by semantic icon name. |
| `frontend/src/app/ActionForm.jsx` | Generic forms with field rendering, rupee-to-paise conversion, validation errors and busy state. |
| `frontend/src/app/records.jsx` | Shared data loader, loading/error/empty states, headings, statuses, tables, pagination and fact lists. |
| `frontend/src/app/RecordPage.jsx` | Shared collection/detail page shells, create dialog, record links, photo list and upload helper. |
| `frontend/src/app/components/Badge.jsx` | Reusable colored status/label badge component. |
| `frontend/src/app/components/ConfirmModal.jsx` | Generic confirmation dialog with Cancel/Confirm and waiting state; available for future screens. |
| `frontend/src/app/components/EmptyState.jsx` | Reusable empty-state presentation component. |
| `frontend/src/app/components/Field.jsx` | Label, hint, inline error and common input style definitions. |
| `frontend/src/app/components/Modal.jsx` | Native dialog wrapper with title, close button and Escape handling. |
| `frontend/src/app/components/PageHeader.jsx` | Reusable page title/action header component. |
| `frontend/src/app/components/Spinner.jsx` | Small and large loading indicators. |
| `frontend/src/app/components/Table.jsx` | Reusable table presentation component. |
| `frontend/src/app/components/Toast.jsx` | Toast context/container and temporary notification display. |

## Frontend feature files

| File | Purpose and visible surface |
| --- | --- |
| `frontend/src/features/public/PublicFrame.jsx` | Public header, Packages and Staff sign-in links, footer and shared brand. |
| `frontend/src/features/public/LandingPage.jsx` | Hero, package type switcher, package enquiry links, subsidy link and public catalog loading/empty states. |
| `frontend/src/features/public/EnquiryForm.jsx` | Public contact/system form, phone/pincode checks, hidden spam field, API submit and reference navigation. |
| `frontend/src/features/public/ThankYouPage.jsx` | Displays enquiry reference and links home or to a new enquiry. |
| `frontend/src/features/auth/LoginPage.jsx` | Staff email/password sign-in and error/busy state. |
| `frontend/src/features/auth/ProfilePage.jsx` | Read-only current staff identity and role. |
| `frontend/src/features/auth/StaffPage.jsx` | Director staff list, add account dialog and editable staff detail. |
| `frontend/src/features/leads/LeadsPage.jsx` | Polling lead inbox with name/phone search, status filter, page sort and new-lead dialog. |
| `frontend/src/features/leads/LeadDetailPage.jsx` | Lead facts, call history, survey request, quote link and reasoned loss action. |
| `frontend/src/features/leads/CallChecklistForm.jsx` | Customer call/site assessment inputs and inline error handling. |
| `frontend/src/features/leads/NewLeadModal.jsx` | Manual customer and lead entry for sales. |
| `frontend/src/features/leads/MarkLostModal.jsx` | Alternative loss dialog component; not currently imported by the active lead detail page. |
| `frontend/src/features/surveys/ScheduleSurveyButton.jsx` | Eligible lead/surveyor choices and schedule dialog. |
| `frontend/src/features/surveys/SurveysPage.jsx` | Survey list/detail, photo upload, submit and approve/reject forms. |
| `frontend/src/features/catalog/CatalogPage.jsx` | Product/package tabs, lists, product editor and package detail. |
| `frontend/src/features/catalog/PackageEditor.jsx` | Package metadata and dynamic BOM lines, including mandatory installation service. |
| `frontend/src/features/quotes/QuotesPage.jsx` | Quote list/create, draft line edit, send/accept and print detail. |
| `frontend/src/features/orders/OrdersPage.jsx` | Order list/detail, received amount, payment entry and conditional confirmation. |
| `frontend/src/features/inventory/InventoryPage.jsx` | Stock list, low-stock toggle and stock receipt form. |
| `frontend/src/features/deliveries/DeliveriesPage.jsx` | Pick list, serial scan/remove, dispatch and delivered actions. |
| `frontend/src/features/installs/InstallsPage.jsx` | Install list/detail, schedule, crew start, photo and signed completion. |
| `frontend/src/features/installs/SignatureField.jsx` | Pointer/touch signature canvas and Clear action. |
| `frontend/src/features/lookup/LookupPage.jsx` | Exact serial or customer-phone lookup and create-ticket link. |
| `frontend/src/features/tickets/TicketBoard.jsx` | Board/list switch, ticket-number search, assigned-to-me filter and create/detail dialogs. |
| `frontend/src/features/tickets/TicketDetail.jsx` | Ticket overview and parts/labour tabs, work transitions, confirmation and invoice link. |
| `frontend/src/features/invoices/InvoicesPage.jsx` | Invoice list/create/detail, payment form and print view. |
| `frontend/src/features/subsidy/SubsidyPage.jsx` | Claim list/detail and status, scheme, reference and amount update form. |
| `frontend/src/features/dashboard/DashboardPage.jsx` | Director financial cards, work links, report switches, CSV export and print. |
| `frontend/src/features/dashboard/RevenueTrend.jsx` | Period-bucketed invoiced revenue chart loaded from invoice data. |

## Agent skill files

The `.agents/skills/` directory contains contributor instructions, not application runtime code. Each `SKILL.md` describes a focused workflow used by coding agents; the SQLAlchemy license and references are supporting material.

| File | Purpose |
| --- | --- |
| `.agents/skills/business-rules/SKILL.md` | Review/implementation workflow for R1–R14. |
| `.agents/skills/fastapi-module/SKILL.md` | Checklist for adding a backend module, API, tests and seed data. |
| `.agents/skills/pytest-rules/SKILL.md` | pytest and TestClient workflow for the solar rules. |
| `.agents/skills/react-feature-page/SKILL.md` | React list/form/detail/print screen conventions. |
| `.agents/skills/sqlalchemy-rules/SKILL.md` | Model, transaction, constraint and state-transition guidance. |
| `.agents/skills/sqlalchemy/SKILL.md` | SQLAlchemy 2.x behavior review workflow across databases. |
| `.agents/skills/sqlalchemy/LICENSE` | License for the bundled SQLAlchemy guidance. |
| `.agents/skills/sqlalchemy/references/sources.md` | References used by the SQLAlchemy skill. |
| `.agents/skills/sqlalchemy/references/sqlalchemy-extras.md` | Additional SQLAlchemy examples and guidance. |

Generated directories such as `backend/.venv/`, `frontend/node_modules/`, bytecode caches and `frontend/dist/` contain tools or build outputs and are not project source files. `.env` is a local secret-bearing configuration copy. Uploaded images live under the configured uploads directory. The only generated file specifically named above is `frontend/package-lock.json`, created by npm during setup.
