---
name: sqlalchemy-rules
description: Use when changing database models, transactions, constraints, or state transitions.
---

# SQLAlchemy rules

- Use the shared mixin from `core/db.py` for `created_at` and `updated_at` on every table. Use SQLAlchemy 2.0 typed mappings.
- Declare cross-module references with strings, for example `ForeignKey("orders.id")`. Keep table writes in their owning module.
- Index frequently queried columns such as `serial_no`, `phone`, `status`, and `number`. Reuse unique indexes where they cover the same lookup.
- Check business rules in the service. Use database unique constraints as the final guard for duplicate serial scans, delivery or install job per order, and warranty per serial. Translate expected uniqueness conflicts to a coded 409 and roll back the transaction.
- During a scan, lock the serial row with `with_for_update()` before checking availability and assignment. Lock the delivery row when updating shared scan counts or checking completion. Take locks in a consistent order across operations.
- Lock the counter row with `with_for_update()` before reading and incrementing it. Keep locks in the write router's transaction through commit.
- Store money as integer paise in schemas, services, and database columns.
- Check the current state and allowed next state in the owning service before mutation. Follow the transition table in `docs/SYSTEM_DESIGN.md`.
- Services flush and never commit. Write routers commit once. SQLite tests cover rules and constraints. Verify row-lock behavior on PostgreSQL.
