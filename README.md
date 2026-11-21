# SunPower Solar Installation Management System

Odoo x LPU Jalandhar Hackathon 2026, Team 64.

One platform for a rooftop solar company: enquiry -> survey -> quote -> order -> dispatch with serial scans -> install proof -> auto warranty -> service tickets -> director dashboard.

Stack: Python (FastAPI, SQLAlchemy, PostgreSQL) + React (Vite, Tailwind).

## Docs
- [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md): stack, architecture, contracts, business rules, state machines, conventions
- [DATA_MODEL.md](docs/DATA_MODEL.md): tables, fields, profit and warranty formulas
- [FEATURES_BY_ROLE.md](docs/FEATURES_BY_ROLE.md): screens, endpoints, owners per role, demo script
- [WORK_SPLIT.md](docs/WORK_SPLIT.md): who builds what, timeline, merge rules

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

Create the database tables and load demo users, catalog, stock, and surveys, then start the API. Run both commands in the activated Python 3.11 environment from `backend/`.

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

## Tests

From `backend/`, run `python -m pytest` in the Python 3.11 environment. The backend tests use in-memory SQLite.

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
