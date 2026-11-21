# SunPower Solar Installation Management System

Odoo x LPU Jalandhar Hackathon 2026, Team 64.

One platform for a rooftop solar company: enquiry -> survey -> quote -> order -> dispatch with serial scans -> install proof -> auto warranty -> service tickets -> director dashboard.

Stack: Python (FastAPI, SQLAlchemy, PostgreSQL) + React (Vite, Tailwind).

## Docs
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md): stack, architecture, contracts, business rules, state machines, conventions
- [DATA_MODEL.md](DATA_MODEL.md): tables, fields, profit and warranty formulas
- [FEATURES_BY_ROLE.md](FEATURES_BY_ROLE.md): screens, endpoints, owners per role, demo script
- [WORK_SPLIT.md](WORK_SPLIT.md): who builds what, timeline, merge rules

## Run (Person A fills in exact commands)
```
cp .env.example .env
docker compose up -d                      # PostgreSQL
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m seed.seed_all                   # creates tables + demo data
uvicorn app.main:app --reload             # API on :8000, docs at /docs
cd ../frontend && npm install && npm run dev
```

## Tests
```
cd backend && pytest
```

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
