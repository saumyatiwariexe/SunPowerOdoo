# Data Model (PostgreSQL via SQLAlchemy 2.0)

Conventions: `id` is an integer primary key, money is integer paise, all tables have `created_at` and `updated_at` (shared mixin).
Field names below are written in camelCase for reading; in Python use snake_case (`customerId` -> `customer_id`).
Each owner defines their own tables in `modules/<name>/models.py` and references others by string foreign key (`ForeignKey("orders.id")`). The Owner column shows who writes each table.

## People
| Table | Owner | Key fields |
|---|---|---|
| User | A | name, email (unique), passwordHash, role (DIRECTOR, SALES, SURVEYOR, WAREHOUSE, CREW, SUPPORT), phone, hourlyRatePaise, active |
| Customer | A | name, phone, email, address, city, pincode |

## Sales funnel
| Table | Owner | Key fields |
|---|---|---|
| Lead | D | customerId, source (WEB, WHATSAPP, CALL), requestedKw, systemType (ON_GRID, OFF_GRID), subsidyInterest, status, assignedToId, lostReason, notes |
| LeadCall | D | leadId, calledById, shadowFreeAreaSqm, monthlyBillPaise, gridSuitable (bool), outcome, notes, calledAt |
| Survey | C | leadId, surveyorId, scheduledAt, roofDirection, tiltDegrees, cableDistanceM, shadowNotes, status, approvedById, approvedAt |

## Catalog
| Table | Owner | Key fields |
|---|---|---|
| Product | A | sku (unique), name, category (PANEL, INVERTER, BATTERY, CHARGE_CONTROLLER, STAND, WIRING, SAFETY, SERVICE), unit, tracksSerial (bool), warrantyMonths (nullable), costPaise, pricePaise, reorderLevel, onHand |
| Package | A | name, systemType, capacityKw (1..5), pricePaise, active |
| PackageItem | A | packageId, productId, qty (the BOM; panels count depends on kW) |

## Quote and order
| Table | Owner | Key fields |
|---|---|---|
| Quote | A | number, leadId, customerId, packageId, status, subtotalPaise, subsidyPaise, totalPaise, validUntil |
| QuoteLine | A | quoteId, productId, description, qty, unitPricePaise, linePaise (copied from the BOM at creation, editable by Sales) |
| Order | A | number, quoteId, customerId, status, totalPaise, advanceMinPaise, confirmedAt |
| Payment | B | orderId or invoiceId, amountPaise, method (CASH, CARD, UPI, BANK), reference, paidAt, receivedById |

## Inventory and delivery
| Table | Owner | Key fields |
|---|---|---|
| StockMovement | B | productId, qty (+/-), reason (PURCHASE, DISPATCH, ADJUSTMENT, RETURN), refType, refId, costPaise |
| SerialUnit | B | productId, serialNo (unique), status, purchaseCostPaise, deliveryId (nullable), customerId (nullable), installedAt |
| Delivery | B | orderId (unique), status, vehicle, dispatchedAt, deliveredAt, deliveredById |
| DeliveryLine | B | deliveryId, productId, qtyRequired, qtyPacked |
| DeliveryScan | B | deliveryId, serialUnitId, scannedById, scannedAt |
| Warranty | B | serialUnitId (unique), customerId, orderId, startDate, endDate, status (ACTIVE, EXPIRED, VOID) |

## Field work and support
| Table | Owner | Key fields |
|---|---|---|
| InstallJob | C | orderId (unique), crewLeadId, scheduledStart, scheduledEnd, startedAt, finishedAt, systemKw, testNotes, status, signedByName, signatureUrl, acceptedAt |
| InstallCrew | C | installJobId, userId (so several technicians can be on one job) |
| JobPhoto | C | installJobId, url, caption, takenAt |
| Ticket | C | number, customerId, serialUnitId, warrantyId (nullable), faultCode, description, priority, status, assignedToId, resolution, customerConfirmedAt, billable (bool) |
| TicketLine | C | ticketId, type (PART, LABOUR), productId (nullable), description, qty, unitPricePaise |

## Money and reporting
| Table | Owner | Key fields |
|---|---|---|
| Invoice | B | number, orderId or ticketId, customerId, status (DRAFT, SENT, PAID, PARTIAL), totalPaise, paidPaise, issuedAt |
| InvoiceLine | B | invoiceId, description, qty, unitPricePaise |
| SubsidyClaim | D | orderId, scheme, status (NOT_APPLIED, SUBMITTED, APPROVED, PAID, REJECTED), amountPaise, referenceNo, notes |
| Counter | A | name (unique), value (generates QT-0001, ORD-0001, INV-0001, TKT-0001) |

## Profit per job (computed in reports, never stored)
```
revenue   = sum(Invoice.totalPaise for the order)
parts     = sum(SerialUnit.purchaseCostPaise for units on the order's delivery)
            + sum(Product.costPaise * qty) for non-serial lines
labour    = sum((finishedAt - startedAt) hours * User.hourlyRatePaise) over InstallCrew
profit    = revenue - parts - labour
```

## Warranty logic
```
startDate = Delivery.deliveredAt
endDate   = startDate + Product.warrantyMonths months
inWarranty(serial, today) = Warranty.status = ACTIVE and today <= endDate
```

## Indexes to add (search must be instant)
SerialUnit(serialNo), Lead(status), Ticket(status), Customer(phone), Quote(number), Order(number).
