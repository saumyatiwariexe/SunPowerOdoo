---
name: pytest-rules
description: Use when testing the solar workflow and business rules with pytest and TestClient.
---

# Test the core chain

- Use a fresh in-memory SQLite engine per test with `sqlite://`, `StaticPool`, and `check_same_thread=False`. Enable SQLite foreign-key enforcement.
- Import `app.models_registry` before calling `Base.metadata.create_all(engine)`. Seed only the records needed for the scenario.
- Override `get_db` with sessions bound to the test engine and use FastAPI `TestClient` as a context manager. Clear dependency overrides and dispose of the engine after each test.
- Drive enquiry, survey approval, package quote, acceptance, payment, order confirmation, serial scans, dispatch, delivery, and warranty through API calls. Use role-appropriate authentication and verify persisted effects in a fresh session after the request.
- Assert HTTP 409 and the error code on rule failures. Check that failed requests leave the relevant rows and states unchanged. Run `python -m pytest` from `backend/`.

## Required coverage

| Rule | Exercise |
| --- | --- |
| R2 | An unapproved survey blocks quote creation. Approval allows it. |
| R4 | One paise below the minimum blocks confirmation and creates no delivery or install job. The exact threshold succeeds. |
| R6 | A missing serial blocks dispatch or completion. The required counts allow it. |
| R7 | Reject a non-`IN_STOCK` serial and a serial assigned to another delivery. Verify the unique constraint independently. |
| R8 | Delivery creates one warranty per scanned serial. Start at delivery and verify calendar-month end dates for 24- and 240-month products. |
| R10 | Close confirmed tickets in both warranty states. Verify zero charge in warranty and one correct parts-plus-labour invoice out of warranty. |

Use PostgreSQL for concurrent scan and counter lock checks. SQLite covers functional rules and constraints.
