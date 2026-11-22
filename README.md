# SunPower Solar Installation Management System

Odoo x LPU Jalandhar Hackathon 2026, Team 64.

One platform for a rooftop solar company: enquiry -> survey -> quote -> order -> dispatch with serial scans -> install proof -> auto warranty -> service tickets -> director dashboard.

Stack: Python (FastAPI, SQLAlchemy, PostgreSQL) + React (Vite, Tailwind).

## Docs
- [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md): stack, architecture, contracts, business rules, state machines, conventions
- [DATA_MODEL.md](docs/DATA_MODEL.md): tables, fields, profit and warranty formulas
- [FEATURES_BY_ROLE.md](docs/FEATURES_BY_ROLE.md): screens, endpoints, owners per role, demo script
- [WORK_SPLIT.md](docs/WORK_SPLIT.md): who builds what, timeline, merge rules
- [USER_GUIDE.md](docs/USER_GUIDE.md): every current screen, button, search and staff workflow
- [CODEBASE_MANUAL.md](docs/CODEBASE_MANUAL.md): architecture, API areas and a file-by-file reference

## Local setup

From the repo root, create `.env` once with `Copy-Item .env.example .env` in PowerShell or `cp .env.example .env` in Bash. Start PostgreSQL with Docker Compose.

```sh
docker compose up -d --wait db
```

Set `JWT_SECRET` in `.env` before starting the API. Generate a value with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

Install backend dependencies in a Python 3.11 virtual environment from `backend/`.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the Windows `py` launcher does not find Python 3.11 and you have uv, use `uv venv --python 3.11 --seed .venv` from `backend/` in place of the `py` command.

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

For a QA rehearsal, set `DATABASE_URL` to a disposable database. It takes precedence over the individual PostgreSQL settings.

Create the database tables and load demo users, catalog, stock, historical warranties and surveys, then start the API. Run both commands in the activated Python 3.11 environment from `backend/`.

```sh
python -m seed.seed_all
python -m uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, with interactive docs at `/docs` and a process health check at `/api/v1/public/health`.

In a separate terminal, run the frontend from `frontend/`.

```sh
npm install
npm run dev
```

### Restarting without changing your data

Keep using the same checkout and root `.env`. `DATABASE_URL`, when set, overrides
the `POSTGRES_*` values. Different databases have different enquiries, even when
they use the same demo logins. A normal API restart does not delete records.

The frontend reads `API_PROXY_TARGET` from the root `.env` on startup. For an API
running on port 8102, set `API_PROXY_TARGET=http://127.0.0.1:8102` there, then start
the API with `python -m uvicorn app.main:app --reload --port 8102` and the frontend
with `npm run dev -- --port 5275`. Use that same frontend URL each time. A shell
`API_PROXY_TARGET` overrides the file, so remove stale shell overrides if needed.
Vite fails when its requested port is occupied instead of opening another copy.

Run the seed only for initial setup or deliberate QA preparation, not on every
restart. Keep the existing Docker database volume; `docker compose down -v`
deletes it. Switching to a QA database does not migrate existing customer data.

After pulling the staff permission update, run `python -m migrate_role_grants`
once from `backend/` before restarting the API. It adds only the new role grant
table and preserves existing staff and customer records. Directors can then
grant staff access to additional non-director roles in Staff accounts.

### Add a full sample cohort

From `backend/`, set `DATABASE_URL` to the intended demo database and set
`SAMPLE_DATA_PASSWORD` for the synthetic staff accounts. Then run
`python -m seed.seed_sample_data --apply`. The script adds a connected cohort of
300 solar jobs and verifies that **all 29 tables have at least 300 rows**. It is
repeatable and does not delete existing records or reset the original demo users.
Synthetic email addresses end in `.invalid`; photos and signatures are marked
as sample content. Synthetic packages are inactive so they do not flood the
public plan chooser, but remain visible in the staff catalog. Use a disposable
database for QA runs.

## Tests

From `backend/`, run `python -m pytest` in the Python 3.11 environment. The backend tests use in-memory SQLite.

The persistence regression uses a temporary SQLite file and two separate Python
processes. From `frontend/`, run `node --test tests/dev-server.test.js` to check
that the API target survives a fresh frontend session.

Lead calls support clickable answers and optional exact measurements or notes.
Saving a call exposes survey scheduling with the customer preselected. Quote,
invoice, stock, survey, crew and ticket forms select database records by name
and reference; no manual record IDs are needed. Staff assignment choices are
restricted to active eligible staff and omit passwords and pay information.

With Playwright available, set `QA_UI_URL` and `QA_SEED_PASSWORD` for a disposable
seeded database and run `node scripts/smoke_quick_forms.cjs`. It writes test records
and checks these form submissions at mobile width, plus choice loading and retry.

## Demo logins (created by the seed)
| Role | Email |
|---|---|
| Director | director@sunpower.test |
| Sales | sales@sunpower.test |
| Surveyor | surveyor@sunpower.test |
| Warehouse | warehouse@sunpower.test |
| Crew | crew@sunpower.test |
| Support | support@sunpower.test |
Password for all: set in `seed_all.py`.

## Team
| Name | Module |
|---|---|
| Saumya Tiwari (leader) | ____ |
| Samarpreet Singh | ____ |
| Ekam | ____ |
| Pranjal Kumar | ____ |

## Customer portal and agent onboarding

An enquiry creates a lead, not a login. Sales or director users contact the lead, open its detail page, and use **Customer portal access > Invite customer** with the confirmed customer email. New and lost leads cannot be invited. SendGrid emails a one-time, 24-hour password-setup link. The customer chooses their own password, then signs in at `/customer`. Passwords are hashed and never emailed. Resending a pending invitation invalidates the previous link; active accounts cannot be re-invited.

Access is tied to the exact customer record selected by the agent, not a matching phone number. One account per customer and one customer account per email are supported. Separate customer records must not be linked automatically. Customers can view their enquiry, survey and installation progress, issued quotes/invoices and payment balances, equipment/warranties, and create service requests for their equipment. Quotes and invoices print/save as PDF. Online payments, online quote acceptance and self-service password resets are not included.

From `backend/`, run the additive migration once (no seed required):

```powershell
.\.venv\Scripts\python.exe migrate_customer_accounts.py
```

Configure the repository root `.env`, then restart the API:

```dotenv
SENDGRID_API_KEY=your-mail-send-api-key
SENDGRID_FROM_EMAIL=your-verified-sender@example.com
CUSTOMER_PORTAL_URL=https://your-customer-facing-site.example
```

Use a SendGrid API key with Mail Send permission and a [verified sender](https://www.twilio.com/docs/sendgrid/for-developers/sending-email/sender-identity). `CUSTOMER_PORTAL_URL` is the site's base URL reachable by customers (no `/customer` suffix); localhost links only work on the same computer. Use HTTPS and `SECURE_COOKIES=true` for deployment. Keep keys in the backend environment, never in `VITE_` variables or Git. Twilio Verify/SMS credentials are not used by this flow.

Without email configuration, invitations fail explicitly. The account invitation is saved before sending; if SendGrid fails, retry the invitation. A successful response means SendGrid accepted the email, not that it reached the inbox. Automated tests mock delivery; verify real delivery after configuring your account. Click/open tracking is disabled for invitation emails. Raw invitation tokens are not stored and are removed from the browser address bar when the activation page opens.

Customer sessions use a separate, two-hour HttpOnly cookie and cannot access staff APIs. Login and invitations are rate limited per API process; shared rate limiting is needed for multiple public workers. The portal currently shows the latest 50 records per section and up to 100 equipment units.
# Active demo work

The bulk dataset includes historical completed jobs. To add work for the standard
demo users without deleting records or resetting progress, run from `backend/`
with your existing virtual environment and intended demo database:

```powershell
python -m seed.seed_active_demo --apply
```

This adds 16 fictional customer projects once: new/contacted leads, scheduled and
submitted surveys, draft/sent quotes, an unpaid order, pending/dispatched deliveries,
scheduled/in-progress/completed installations, and open/in-progress/resolved tickets.
It requires the demo users and active 3 kW on-grid catalogue package to exist.
Re-running skips these customers; it does not reset their workflow.

Use `crew@sunpower.test` for Vikram Arora and Neha Sood's scheduled jobs and Arjun
Mehta's in-progress job. Use `surveyor@sunpower.test` for Gurpreet Singh and Meera
Kapoor's scheduled surveys, and `support@sunpower.test` for Manpreet Kaur's tickets.
The existing demo password remains unchanged. Select the status filter to see
other stages; search serial lookup by customer name, phone or serial number.
