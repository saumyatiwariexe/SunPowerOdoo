---
name: fastapi-module
description: Use when adding a FastAPI module or extending its API, tests, and seed data.
---

# Add a FastAPI module

1. Check ownership in `docs/WORK_SPLIT.md`. Use `docs/SYSTEM_DESIGN.md` for cross-module contracts and `docs/DATA_MODEL.md` for tables.
2. Add `backend/app/modules/<module>/models.py` with typed SQLAlchemy models, the shared timestamp mixin, string foreign keys, and lookup indexes.
3. Add `schemas.py` with separate request and response models. Use snake_case, `extra="forbid"` on input, and integer paise.
4. Add `service.py` functions taking `db: Session`. Check rules and transitions before mutating data. Call other modules through their services with the same session. Raise coded `AppError` exceptions and flush as needed.
5. Add `router.py` under `/api/v1`. Apply `require_roles` on protected endpoints, call the service, and commit once on successful writes. Return the shared response envelope.
6. Ask Person A to import the module's models in `backend/app/models_registry.py` and include its router in `backend/app/main.py`. Import registered models before schema creation.
7. Add a pytest case under `backend/tests/` for the success path and the relevant rejected action. Run `python -m pytest` from `backend/`.
8. Add a seed function in `backend/seed/seed_<module>.py` using the passed session. Coordinate registration and dependency order in `seed_all.py` with Person D.
