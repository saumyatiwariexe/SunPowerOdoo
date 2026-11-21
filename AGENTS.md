# Agent instructions

SunPower manages rooftop solar installations from enquiry and survey through quote, order, dispatch, and installation.
It tracks serial-based warranties, service tickets, invoices, and director reports.
Four people have 24 hours. Backend uses Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL, and pytest. Frontend uses React, Vite, and Tailwind.

## Run and test

- From the repo root, run `Copy-Item .env.example .env` in PowerShell (`cp .env.example .env` in Bash), then `docker compose up -d` to start PostgreSQL.
- If needed, create a Python 3.11 environment from `backend/` with `py -3.11 -m venv .venv` on Windows (`python3.11 -m venv .venv` on Unix).
- From `backend/`, use an active Python 3.11 virtual environment and run `python -m pip install -r requirements.txt`, `python -m seed.seed_all`, then `uvicorn app.main:app --reload`.
- From `frontend/`, run `npm install` and `npm run dev`.
- From `backend/`, run `python -m pytest`.
- See [README.md](README.md) for the setup workflow.

## Ownership

| Person | Backend folders and shared files | Frontend folders under `frontend/src/` |
| --- | --- | --- |
| A | `backend/app/core/`, `backend/app/main.py`, `backend/app/models_registry.py`, `backend/app/modules/{users,catalog,quotes,orders}/` | `features/{auth,catalog,quotes,orders}/` |
| B | `backend/app/modules/{inventory,deliveries,warranty,billing}/` | `features/{inventory,deliveries,invoices}/` |
| C | `backend/app/modules/{surveys,installs,tickets}/` | `features/{surveys,installs,tickets,lookup}/` |
| D | `backend/app/modules/{leads,reports,subsidy,public}/`, `backend/seed/seed_all.py` | `app/`, `features/{public,leads,dashboard,subsidy}/` |

Only edit your own module; for `core/` or `models_registry.py` ask Person A. Coordinate router registration in `main.py` with Person A. See [work split](docs/WORK_SPLIT.md).

## Business rules

- R1 Keep every lead. Mark it `LOST` only with a reason.
- R2 Create a quote only after the lead's survey is `APPROVED`.
- R3 Generate quotes from a package template and populate parts from its bill of materials (BOM).
- R4 Confirm an order only when received payments meet the configured advance minimum (assumed 30% of total).
- R5 Confirming an order creates exactly one delivery pick list and one install job.
- R6 Complete a delivery only when every serialized line has its required count of scanned serials.
- R7 Scan only an `IN_STOCK` serial that is absent from other deliveries. A database unique constraint is the final guard.
- R8 Completing delivery creates one warranty per serial from `Product.warranty_months` (inverter 24, battery 24, panels 240).
- R9 Use the serial number for ticket lookup and compute warranty status.
- R10 Charge zero for in-warranty tickets and automatically invoice parts and labour for out-of-warranty tickets.
- R11 Close a ticket only after recording customer confirmation.
- R12 Completing installation requires start and finish times, system kW, at least one photo, and a signature.
- R13 Prevent overlapping install slots for any crew member.
- R14 Store all money as integer paise.

## Conventions

- Modules write their own tables and call other modules through service functions.
- Services use the caller's session, flush when needed, and never commit. Write routers commit once on success. Roll back the whole transaction on failure.
- Use integer paise for money and snake_case JSON fields. Pydantic inputs use `extra="forbid"`.
- Raise `AppError(code, message, status)` with explicit error codes. Return HTTP 409 for business-rule and state conflicts.
- Enforce roles on backend routes via `Depends(require_roles(...))`.
- Use the [system design](docs/SYSTEM_DESIGN.md) for contracts and transitions, the [data model](docs/DATA_MODEL.md) for schema, and [features by role](docs/FEATURES_BY_ROLE.md) for screens and the demo.

## Definition of done

- Pydantic validation and role checks are in place. Rule violations return a clear 409.
- UI has inline form errors and loading, empty, and error states.
- Seed data exercises the feature, the demo script includes it, and relevant tests pass.

## Never

- No static JSON data, float money, raw SQL outside `reports`, secrets in Git, or unused dependencies.
