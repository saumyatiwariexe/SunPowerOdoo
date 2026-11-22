# Integration QA — 21 November 2026

**Release verification:** All nine scenes passed on `fix/demo-release` using a fresh PostgreSQL database. The tables give the original reproduction steps and the corresponding release-branch fix commits.

**Original audit of main.** The audited remote commit was `79bb7f8`. Its OpenAPI document exposes four operations: health, login, logout and current user. None of the nine demo scenes can run on a fresh checkout. The outcomes below distinguish that checkout from a supplemental rehearsal of feature commit `4642454`.

## Main checkout

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| QA-01 | P0 | Seed · D | From `backend/` run `python -m seed.seed_all` on a fresh database. Python reports `No module named seed.seed_all`. Only `seed_users` exists. | fixed | `68583d9` |
| QA-02 | P0 | Frontend boot · D | From `frontend/` run `npm run build` or `npm run dev -- --port 5273`. Both fail with ENOENT for `frontend/package.json`. Chromium at 375 px receives connection refused on port 5273. | fixed | `97227df` |
| QA-03 | P0 | Public, leads, reports · D | POST a valid 3 kW enquiry to `/api/v1/public/enquiries`. It returns 404. With a director cookie GET `/api/v1/reports/summary` also returns 404. Scenes 1 and 9 are blocked. | fixed | `97227df` |
| QA-04 | P0 | Commercial API and router registration · A | Start the API and inspect `/openapi.json`. Packages, quotes and orders are absent. The seeded sales user cannot build a quote or confirm an order. | fixed | `97227df` |
| QA-05 | P0 | Warehouse, warranty, billing · B | Inspect `/openapi.json` for stock, delivery and invoice routes. None exist. As support, GET `/api/v1/lookup?serial=INV-OLD-2024-001` returns 404 for the route. | fixed | `97227df` |
| QA-06 | P0 | Field visits, installation and tickets · C | Inspect `/openapi.json` for `/leads/{lead_id}/survey`, `/installs` and `/tickets`. All are absent. There is no assignable visit or field/service handoff. | fixed | `97227df` |
| QA-07 | P1 | Database configuration · A | In a process without `POSTGRES_*` overrides, set only `DATABASE_URL=sqlite:///unused_qa_probe.sqlite`. Inspect `Settings(_env_file=None).database_url.drivername` without opening a connection. It still returns `postgresql+psycopg`. A QA job relying solely on the URL could seed the default database. | fixed | `5f55eaf` |
| QA-08 | P2 | Validation status contract · A | POST `/api/v1/auth/login` with otherwise valid fields and an extra key. HTTP 400 has the standard `VALIDATION_ERROR` envelope. The QA checklist requires 422. Design §7 and the existing tests specify 400. The release uses the subsequently approved QA status codes. | fixed | `cfd64c5` |
| QA-09 | P1 | Integration coverage · integration, D demo handoff | On the base commit there is no `scripts/smoke_demo.py`; eight core tests can pass despite every demo route being absent. Run the committed runner to surface the blockers. | fixed | `73d4bec` |

## Supplemental rehearsal on feature commit 4642454

These findings were reproduced against an archive of the committed feature branch with a second disposable database. They are relevant to the merge decision. They do not establish that any business route works on main.

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| REF-01 | P0 | Historical delivery and seed ordering · B/D | Run the master seed against an empty DB. It reports skipped order, delivery, install and ticket seed modules, then success. Look up the documented old inverter `INV-OLD-2024-001` as support. Result: 404. Stock seeding runs before order seeding and the history fixture requires an existing closed order. Scenes 7–8 cannot be demonstrated from this seed. | fixed | `68583d9` |
| REF-02 | P2 | Site survey and lead handoff · C/D | Submit a new enquiry. In Site surveys enter that lead’s ID, a valid active surveyor ID and a visit time. The form accepts both IDs, then displays “Schedule surveys for contacted leads.” Log the first customer call under Lead inbox and submit the same IDs. The visit schedules. The lead-detail link also loses the selected lead. | fixed | `35736b8` |
| REF-03 | P2 | Installation proof response · C/A | On an in-progress job with a photo, submit completion omitting the signature, then omit each of start, finish and kW independently. Each returns 400 with a validation envelope. QA expects 409 for each. A missing photo returns 409; incomplete jobs stay open. | fixed | `cfd64c5` |
| REF-04 | P2 | Public validation · D/A | Submit a valid enquiry with just the phone changed to `bad`, then repeat with just the pincode changed to `bad`. Both return 400 with validation details. QA expects 422. Same contract decision as QA-08. | fixed | `cfd64c5` |
| REF-05 | P2 | Restricted-page navigation · D | Sign in as crew and navigate directly to `/dashboard`. Access is denied on that URL; the requested role-home redirect does not occur. The reports API correctly returns 403. | fixed | `2449fec` |
| REF-06 | P2 | Public UI · D | At a 375 px viewport load `/`, `/enquiry` and `/thank-you`. Each document is 376 px wide. On the landing page React also logs a warning for the `fetchPriority` prop. | fixed | `743726f` |
| REF-07 | P2 | Billing/inventory list scaling · B | GET `/api/v1/invoices?page_size=1` or `/api/v1/stock?page_size=1`. Their list handlers ignore pagination. In `billing.service.list_invoices`, each invoice executes a separate customer SELECT after the initial invoice query. | fixed | `5fb0ad3` |

## Original audit evidence

- Branch `fix/integration-bugs` starts at `origin/main@79bb7f8`. Main API used port 8100, frontend boot attempted port 5273. The reference used 8101 and 5274. No dependencies were installed. The existing Python 3.11 environment supplies the pinned HTTPX client (`httpx2`).
- For a repeat run, create an empty throwaway PostgreSQL database. Set **both** `DATABASE_URL` and the matching `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` and `POSTGRES_PASSWORD`. Confirm `get_engine().url.database` names that database before seeding. Use a fresh signing secret.
- From `backend/`, run `python -m seed.seed_all` and `python -m uvicorn app.main:app --host 127.0.0.1 --port 8100`. From the repo root set `QA_SEED_PASSWORD` to the seed password and run `python scripts/smoke_demo.py --base-url http://127.0.0.1:8100/api/v1` in the backend environment. The runner creates records and returns nonzero on failed checks.
- On main the master seed failed. To test the reachable auth API separately, QA created the registered tables in the throwaway database and invoked the available `seed_users` with a generated password. All six logins succeeded; unauthenticated `GET /auth/me` returned 401 with the standard envelope. Pytest passed **8/8**. No lint configuration was present.
- Main smoke result: **7 failed checks or blocked groups**. These cover unknown fields, invalid phone, invalid pincode, wrong-role report access and the three scene groups. A 404 for an absent endpoint does not count as successful role or input validation. The main frontend has no runnable application routes, so inline errors, state rendering, navigation, printing, sample-data use and layout cannot be certified there.
- Reference smoke result on the fresh seed: **8 failed checks or blocked groups**. Seven were status mismatches (unknown field, phone, pincode and four missing install-proof fields). The eighth was the missing expired serial. The other checks exercised package BOM copying, the advance boundary, idempotent confirmation, competing and parallel scans, actual month-based warranties, crew overlap, signed installation, covered ticket closure, invoice totals and reports/CSV.
- As a separate billing control, QA dated one delivered inverter warranty in the disposable reference DB to its expired state and used the normal support endpoints. Closing the confirmed ticket generated one 1,100-paise invoice for 500 paise in parts and 600 paise in labour. Repeating close returned the same invoice. This control predated the release seed fix.
- Reference browser: Chromium visited 31 public, list, detail, profile and administration URLs at 375 px. Quote and invoice print media produced PDFs with the correct document numbers. Injected list loading, empty and failed responses were sampled; direct schedule-form submission showed the server error inline. Full owner UI sign-off, including every form’s error states and visual inspection of printed pages, is pending on main.
- Main code review: the available authentication module uses a bounded email lookup; customer phone is indexed, and email, SKU and counter names are unique. Counter increments use row locks. No `db.commit()` in module services was found. CORS is restricted to the configured origin. The upload helper caps size at 5 MiB, checks image signatures and uses generated filenames. A targeted tracked-file scan found no private keys or common token signatures. No workflow list handlers, frontend rendering, serial scan locks, warranty logic or report calendar logic exist on this base to assess. The supplemental run exercised a real PostgreSQL parallel scan, with one success and one conflict.

## Release verification

The release API used port 8102 and the frontend used 5275. Seeding the disposable PostgreSQL database twice retained the historical warranties and invoice. From the repository root, set `QA_SEED_PASSWORD` and run `python scripts/smoke_demo.py --base-url http://127.0.0.1:8102/api/v1`. For the browser regression, set `QA_UI_URL` to the matching frontend and run `node scripts/smoke_ui.cjs` where Playwright and Chrome are available.

## Enquiry persistence follow-up

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| REF-08 | P1 | Frontend development configuration · D/A | Start Vite with a shell-only API target on port 8102. Restart from a new shell: the old config ignores root `.env` and falls back to API 8000, which can use a different database. Saved enquiries appear absent. Vite now loads the persisted target and fails on an occupied port. | fixed | `32ab278` |

Read-only checks found 6, 7 and 10 leads through frontend ports 5173, 5274 and
5275 respectively. These are separate datasets, not evidence of deleted rows.
A submitted enquiry remained visible through the sales API after terminating
its Python process and starting a fresh one against the same temporary SQLite
file. All 41 backend tests, the proxy configuration regression and frontend build
passed. A fresh Vite process without a shell API override used the saved root
configuration and retrieved the release database's existing 10 leads. No existing
database was seeded, reset or migrated during this investigation.

## Faster data entry verification

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| UX-01 | P2 | Lead calls and record selection · A/B/C/D | Open a new lead and log a call: the outcome previously required typing. Quote, invoice, receiving, crew and ticket forms required remembered numeric IDs. Calls now offer quick answers; these forms and surveys use searchable database choices with names and identifying details. | fixed | `bac6806` |

All 43 backend tests and the frontend build passed. The reusable
`scripts/smoke_quick_forms.cjs` passed actual form submissions for calls, surveys,
quotes, invoices, stock, crew and ticket assignment at 375px against a new temporary
SQLite database. It also verified choice loading, failure and retry. The existing
mobile survey and role-redirect smoke passed. Screenshots were reviewed at mobile
and desktop sizes. The design detector reported only the existing font choice.
The original checkout was fast-forwarded to the tested release, and its API was
restarted on port 8000. Read-only verification through frontend 5173 confirmed
the new controls and Saumya's existing Lead #6 in the unchanged `sunpower` database.

## Ten-line summary

1. The release branch integrates the frontend, backend modules and nine-scene runner.
2. All 40 backend tests passed with warnings treated as errors.
3. The production frontend built successfully. The repository has no configured lint task.
4. All nine HTTP scenes and their negative checks passed against PostgreSQL.
5. Browser verification passed for named survey scheduling, first-call eligibility and surveyor assignment.
6. A fresh seed created both warranty examples and repeat seeding preserved them.
7. Mobile public pages, wrong-role redirects and quote/invoice PDF output passed the browser checks.
8. **Release risk:** merging or deploying this branch remains a separate action.
9. **Data risk:** seeding and rehearsing write records. Use a disposable database.
10. **Demo setup:** use the release branch and its matching frontend/API pair when rehearsing.

## Active demo repairs � 22 November 2026

| ID | Severity | Module / owner | Reproduction | Status | Commit |
| --- | --- | --- | --- | --- | --- |
| DEMO-01 | P0 | Seed / D | After bulk seeding, log in as standard crew or surveyor: completed history dominates and crew has no assigned work. | fixed: additive 16-project pipeline, no reset | 23e410a |
| DEMO-02 | P1 | Lookup / B,C | Enter a lowercase serial or formatted phone; no way to discover an equipment identifier. | fixed: normalized exact lookup and customer/equipment search | 23e410a |
| DEMO-03 | P1 | Tickets / C | Open create-ticket dialog without knowing a serial; existing issue text cannot be corrected. | fixed: database equipment picker and editable open/in-progress issue details | 23e410a |
| DEMO-04 | P2 | Installs, surveys / C | Lists show IDs without site context and completed history hides work. | fixed: customer/site/assignee names and status filters | 23e410a |
| DEMO-05 | P2 | Leads, quotes, deliveries / D,A,B | Lead requirements and quote details lack edit controls; pick list requires memorized serials. | fixed: field editors and available-stock selector | 23e410a |

Validation: 50 backend tests passed on an isolated test database; Vite production
build passed. No lint task is configured. The new regression covers idempotent
active data, role queues, lookup permissions, case/phone lookup, stock selection,
duplicate-scan rejection, ticket editing, resolution, confirmation and closure.
Chrome UI verification confirmed the standard crew's scheduled jobs, named job
information with Start installation, and populated serial lookup results.

1. Added 16 fictional active projects without deleting existing customer data.
2. Standard crew has scheduled, in-progress and completed work.
3. Standard surveyor has scheduled visits and a submitted survey awaits review.
4. Sales and warehouse have quotes, orders and deliveries at actionable stages.
5. Support has assigned open, in-progress and resolved tickets.
6. Added searchable equipment and editable lead, quote and ticket details.
7. Retained required installation proof and ticket confirmation rules.
8. Risk: this pass did not manually exercise every role on every mobile screen.
9. Risk: old bulk history remains synthetic; use the named active projects for the demo.
10. Risk: rehearsal advances state; the additive command preserves progress rather than resetting it.

## Ticket assignment repair � 22 November 2026

| ID | Severity | Module / owner | Reproduction | Status | Commit |
| --- | --- | --- | --- | --- | --- |
| TICKET-ASSIGN-01 | P1 | Tickets / C, Users / A | Director opens Assigned to me, but cannot be selected as ticket owner. Creating tickets offers no assignment. | fixed: director eligibility, assignment on create, Assign to me action | 34dba37 |
| TICKET-ASSIGN-02 | P2 | Tickets / C | Reassign a ticket and inspect PATCH response: assignee name still describes previous owner. | fixed: refresh descriptive fields after mutation | 34dba37 |
| TICKET-ASSIGN-03 | P2 | Tickets UI / C | Search prompts only for ticket number; an empty personal queue offers no explanation. | fixed: customer/serial/issue search label, personal queue guidance, server-authenticated mine filter | 34dba37 |

Verified the live support personal queue returns three owned tickets and director
returns zero (existing tickets were not reassigned). Isolated regressions verify
assignment during creation, director ownership, authenticated personal filtering,
reassignment, unassignment, updated names and rollback on invalid assignment.
The full suite initially passed 49/50; the remaining test asserted the old
crew/support-only eligibility. Its expectation now explicitly includes directors
and additionally verifies crew-only filtering. All 19 affected regression tests
then passed; the production frontend build passed. Native browser automation was
unavailable following the previous turn's URL-confidence stop; this ticket repair
was verified through API tests and the live read-only queue checks.

## Customer login and consistent record order � 22 November 2026

- Customer onboarding now emails a generated password and login URL. First sign-in
  activates the account within the 24-hour invitation window; resending beforehand
  replaces the password. Active accounts retain their credentials. Passwords are
  bcrypt-hashed, never returned in staff responses, and not logged. Legacy activation
  links remain supported. SendGrid tests use mocks; no real email was sent in this pass.
- The onboarding panel displays the configured login address and identifies a
  localhost address that cannot be used from a customer's device.
- Operational lists now order by descending numeric database ID before pagination.
  This fixes tied creation timestamps and inconsistent alphabetical/status/date
  sorting in leads, deliveries, surveys, installs, invoices, subsidy, catalog,
  stock and staff. Quotes, orders and tickets already used this ordering.
  Assignment dropdowns keep name ordering; reports keep their analytical sorting.
- Validation: 52 backend tests passed; frontend build passed. Extended ordering
  regression failed before the change and passed afterward across 13 module lists,
  including page boundaries and reversed invoice/subsidy timestamps.
