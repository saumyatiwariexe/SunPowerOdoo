# Backend agent instructions

Each module lives in `app/modules/<module>/` and has four files.

| File | Responsibility |
| --- | --- |
| `models.py` | SQLAlchemy models, indexes, and constraints for tables the module owns |
| `schemas.py` | Pydantic v2 inputs and outputs with snake_case fields and `extra="forbid"` on inputs |
| `service.py` | State checks, business rules, and calls to other module services with the same session |
| `router.py` | HTTP validation, role checks, service calls, and one commit on successful writes |

Services flush as needed and never commit. Use `AppError` for rule failures and `require_roles` on protected routes.
Coordinate registration in `app/models_registry.py` and `app/main.py` with Person A.
Run `python -m pytest` from `backend/` in the Python 3.11 environment.
