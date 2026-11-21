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

## Tests

From `backend/`, run `python -m pytest` in the Python 3.11 environment. The backend tests use in-memory SQLite.

The persistence regression uses a temporary SQLite file and two separate Python
processes. From `frontend/`, run `node --test tests/dev-server.test.js` to check
that the API target survives a fresh frontend session.

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
