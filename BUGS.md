# Integration QA — 21 November 2026

**Release verdict: blocked on main.** The audited remote commit was `79bb7f8`. Its OpenAPI document exposes four operations: health, login, logout and current user. None of the nine demo scenes can run on a fresh checkout. The outcomes below distinguish that checkout from a supplemental rehearsal of feature commit `4642454`.

## Main checkout

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| QA-01 | P0 | Seed · D | From `backend/` run `python -m seed.seed_all` on a fresh database. Python reports `No module named seed.seed_all`. Only `seed_users` exists. | needs owner | — |
| QA-02 | P0 | Frontend boot · D | From `frontend/` run `npm run build` or `npm run dev -- --port 5273`. Both fail with ENOENT for `frontend/package.json`. Chromium at 375 px receives connection refused on port 5273. | needs owner | — |
| QA-03 | P0 | Public, leads, reports · D | POST a valid 3 kW enquiry to `/api/v1/public/enquiries`. It returns 404. With a director cookie GET `/api/v1/reports/summary` also returns 404. Scenes 1 and 9 are blocked. | needs owner | — |
| QA-04 | P0 | Commercial API and router registration · A | Start the API and inspect `/openapi.json`. Packages, quotes and orders are absent. The seeded sales user cannot build a quote or confirm an order. | needs owner | — |
| QA-05 | P0 | Warehouse, warranty, billing · B | Inspect `/openapi.json` for stock, delivery and invoice routes. None exist. As support, GET `/api/v1/lookup?serial=INV-OLD-2024-001` returns 404 for the route. | needs owner | — |
| QA-06 | P0 | Field visits, installation and tickets · C | Inspect `/openapi.json` for `/leads/{lead_id}/survey`, `/installs` and `/tickets`. All are absent. There is no assignable visit or field/service handoff. | needs owner | — |
| QA-07 | P1 | Database configuration · A | In a process without `POSTGRES_*` overrides, set only `DATABASE_URL=sqlite:///unused_qa_probe.sqlite`. Inspect `Settings(_env_file=None).database_url.drivername` without opening a connection. It still returns `postgresql+psycopg`. A QA job relying solely on the URL could seed the default database. | needs owner | — |
| QA-08 | P2 | Validation status contract · A | POST `/api/v1/auth/login` with otherwise valid fields and an extra key. HTTP 400 has the standard `VALIDATION_ERROR` envelope. The QA checklist requires 422. Design §7 and the existing tests specify 400. Owner agreement is needed. | needs owner | — |
| QA-09 | P1 | Integration coverage · integration, D demo handoff | On the base commit there is no `scripts/smoke_demo.py`; eight core tests can pass despite every demo route being absent. Run the committed runner to surface the blockers. | fixed | `73d4bec` |

## Supplemental rehearsal on feature commit 4642454

These findings were reproduced against an archive of the committed feature branch with a second disposable database. They are relevant to the merge decision. They do not establish that any business route works on main.

| ID | Severity | Module and owner | Reproduction steps and result | Status | Fix commit |
| --- | --- | --- | --- | --- | --- |
| REF-01 | P0 | Historical delivery and seed ordering · B/D | Run the master seed against an empty DB. It reports skipped order, delivery, install and ticket seed modules, then success. Look up the documented old inverter `INV-OLD-2024-001` as support. Result: 404. Stock seeding runs before order seeding and the history fixture requires an existing closed order. Scenes 7–8 cannot be demonstrated from this seed. | needs owner | — |
| REF-02 | P2 | Site survey and lead handoff · C/D | Submit a new enquiry. In Site surveys enter that lead’s ID, a valid active surveyor ID and a visit time. The form accepts both IDs, then displays “Schedule surveys for contacted leads.” Log the first customer call under Lead inbox and submit the same IDs. The visit schedules. The lead-detail link also loses the selected lead. | needs owner | — |
| REF-03 | P2 | Installation proof response · C/A | On an in-progress job with a photo, submit completion omitting the signature, then omit each of start, finish and kW independently. Each returns 400 with a validation envelope. QA expects 409 for each. A missing photo returns 409; incomplete jobs stay open. | needs owner | — |
| REF-04 | P2 | Public validation · D/A | Submit a valid enquiry with just the phone changed to `bad`, then repeat with just the pincode changed to `bad`. Both return 400 with validation details. QA expects 422. Same contract decision as QA-08. | needs owner | — |
| REF-05 | P2 | Restricted-page navigation · D | Sign in as crew and navigate directly to `/dashboard`. Access is denied on that URL; the requested role-home redirect does not occur. The reports API correctly returns 403. | needs owner | — |
| REF-06 | P2 | Public UI · D | At a 375 px viewport load `/`, `/enquiry` and `/thank-you`. Each document is 376 px wide. On the landing page React also logs a warning for the `fetchPriority` prop. | needs owner | — |
| REF-07 | P2 | Billing/inventory list scaling · B | GET `/api/v1/invoices?page_size=1` or `/api/v1/stock?page_size=1`. Their list handlers ignore pagination. In `billing.service.list_invoices`, each invoice executes a separate customer SELECT after the initial invoice query. | needs owner | — |

## Reproduction and coverage

- Branch `fix/integration-bugs` starts at `origin/main@79bb7f8`. Main API used port 8100, frontend boot attempted port 5273. The reference used 8101 and 5274. No dependencies were installed. The existing Python 3.11 environment supplies the pinned HTTPX client (`httpx2`).
- For a repeat run, create an empty throwaway PostgreSQL database. Set **both** `DATABASE_URL` and the matching `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` and `POSTGRES_PASSWORD`. Confirm `get_engine().url.database` names that database before seeding. Use a fresh signing secret.
- From `backend/`, run `python -m seed.seed_all` and `python -m uvicorn app.main:app --host 127.0.0.1 --port 8100`. From the repo root set `QA_SEED_PASSWORD` to the seed password and run `python scripts/smoke_demo.py --base-url http://127.0.0.1:8100/api/v1` in the backend environment. The runner creates records and returns nonzero on failed checks.
- On main the master seed failed. To test the reachable auth API separately, QA created the registered tables in the throwaway database and invoked the available `seed_users` with a generated password. All six logins succeeded; unauthenticated `GET /auth/me` returned 401 with the standard envelope. Pytest passed **8/8**. No lint configuration was present.
- Main smoke result: **7 failed checks or blocked groups**. These cover unknown fields, invalid phone, invalid pincode, wrong-role report access and the three scene groups. A 404 for an absent endpoint does not count as successful role or input validation. The main frontend has no runnable application routes, so inline errors, state rendering, navigation, printing, sample-data use and layout cannot be certified there.
- Reference smoke result on the fresh seed: **8 failed checks or blocked groups**. Seven were status mismatches (unknown field, phone, pincode and four missing install-proof fields). The eighth was the missing expired serial. The other checks exercised package BOM copying, the advance boundary, idempotent confirmation, competing and parallel scans, actual month-based warranties, crew overlap, signed installation, covered ticket closure, invoice totals and reports/CSV.
- As a separate billing control, QA dated one delivered inverter warranty in the disposable reference DB to its expired state and used the normal support endpoints. Closing the confirmed ticket generated one 1,100-paise invoice for 500 paise in parts and 600 paise in labour. Repeating close returned the same invoice. REF-01 remains open.
- Reference browser: Chromium visited 31 public, list, detail, profile and administration URLs at 375 px. Quote and invoice print media produced PDFs with the correct document numbers. Injected list loading, empty and failed responses were sampled; direct schedule-form submission showed the server error inline. Full owner UI sign-off, including every form’s error states and visual inspection of printed pages, is pending on main.
- Main code review: the available authentication module uses a bounded email lookup; customer phone is indexed, and email, SKU and counter names are unique. Counter increments use row locks. No `db.commit()` in module services was found. CORS is restricted to the configured origin. The upload helper caps size at 5 MiB, checks image signatures and uses generated filenames. A targeted tracked-file scan found no private keys or common token signatures. No workflow list handlers, frontend rendering, serial scan locks, warranty logic or report calendar logic exist on this base to assess. The supplemental run exercised a real PostgreSQL parallel scan, with one success and one conflict.

## Ten-line summary

1. Added the reusable HTTP smoke runner in `73d4bec`.
2. Eight core tests passed on the latest main.
3. All six seeded roles authenticated after the isolated user-only bootstrap.
4. Main’s master seed, frontend build and frontend boot are blocked.
5. Missing main routes prevent release validation of all nine scenes.
6. The supplemental rehearsal passed the commercial, warehouse and installation handoffs.
7. The site-survey error is reproducible on a new lead; logging the first call unlocks scheduling.
8. **Risk 1:** an incomplete merge leaves the presentation without an application to open.
9. **Risk 2:** the reference seed omits the expired inverter needed for automatic-billing scenes.
10. **Risk 3:** relying on `DATABASE_URL` alone can aim a rehearsal at the wrong database.
