---
name: business-rules
description: Use when implementing or reviewing enforcement and tests for rules R1–R14.
---

# Business rule map

`docs/SYSTEM_DESIGN.md` defines the rules and cross-module contracts. Functions marked **planned** have proposed names. Tests below are planned coverage under `backend/tests/`.

| Rule | Enforcing module and function | Test and evidence |
| --- | --- | --- |
| R1 | D · `leads.service.mark_lost` (planned) | `test_r1_lead_kept_when_lost` checks a reason is required, the row is retained, and no delete route exists. |
| R2 | A · `quotes.service.create_from_package` (planned), calls C · `surveys.service.is_approved` | `test_r2_quote_requires_approved_survey` checks 409 and no quote before approval, then successful creation after approval. |
| R3 | A · `quotes.service.create_from_package` (planned), calls `catalog.service.get_package_bom` | `test_r3_quote_copies_package_bom` compares created line products and quantities with the package BOM. |
| R4 | A · `orders.service.confirm` | `test_r4_confirm_requires_advance` checks failure one paise below the minimum and success at the threshold. |
| R5 | A · `orders.service.confirm`, calls B · `deliveries.service.create_for_order` and C · `installs.service.create_for_order` | `test_r5_confirm_creates_one_delivery_and_job` checks one of each on repeat and full rollback if either create fails. |
| R6 | B · `deliveries.service.complete` and `deliveries.service.dispatch` (dispatch name planned) | `test_r6_delivery_requires_all_serials` checks 409 with a short count, then success with every required serial scanned. |
| R7 | B · `deliveries.service.scan_serial` (planned), unique constraint on the scanned serial | `test_r7_rejects_unavailable_or_duplicate_serial` checks out-of-stock and cross-delivery duplicates. Test the constraint separately. |
| R8 | B · `deliveries.service.complete` calls `warranty.service.start_for_delivery` | `test_r8_delivery_starts_warranty_per_serial` checks one row per serial, delivery start date, and product-specific end dates. |
| R9 | C · `tickets.service.lookup_by_serial` (planned), calls B · `warranty.service.check_by_serial` | `test_r9_lookup_computes_warranty_status` checks serial lookup and the inclusive end date and expired cases. |
| R10 | C · `tickets.service.close` (planned), calls B · `billing.service.create_ticket_invoice` for billable tickets | `test_r10_close_bills_only_out_of_warranty` checks zero charge in warranty and one parts-plus-labour invoice out of warranty. |
| R11 | C · `tickets.service.close` (planned) | `test_r11_close_requires_customer_confirmation` checks 409 before confirmation and success after it is recorded. |
| R12 | C · `installs.service.complete` (planned) | `test_r12_install_requires_completion_proof` checks that missing times, kW, photo, or signature blocks completion. |
| R13 | C · `installs.service.schedule` (planned) | `test_r13_rejects_overlapping_crew_slots` checks conflicts for any member of the assigned crew and allows adjacent slots. |
| R14 | All money-bearing modules · strict integer inputs, service calculations, and integer columns. A · `core.money` shared helpers | `test_r14_money_round_trips_as_integer_paise` checks float rejection and exact totals through persistence and the API. |

R12 requires a signature at completion. The design also shows separate complete and accept routes. Coordinate the signature handoff with Person C and keep the completion gate in place.
