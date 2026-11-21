# SunPower user guide

SunPower follows a rooftop solar job from customer enquiry through survey, quote, payment, delivery, installation, warranty and service. This guide describes the controls in the current React application. The menu changes with your staff role, and some actions appear only while a record is in the right state.

## Start and sign in

The public site is at `/`. **Request a quote** opens the enquiry form; **Explore packages** jumps to the package list. **Packages** in the header returns to that list, and **Staff sign in** opens `/login`. On the package list, **On-grid** and **Off-grid** switch the visible system type. **Enquire** on a package opens the form with its capacity and type selected. **Ask about subsidies** opens the form with the subsidy box checked. Only active packages appear on the public page.

The enquiry form asks for full name, a 10-digit Indian mobile number, installation address, six-digit pincode, 1–5 kW size, system type, optional monthly electricity bill in rupees, and subsidy interest. **Submit Enquiry** validates the visible fields, creates a customer and lead, and opens the thank-you page with a `LEAD-####` reference. A repeat submission from the same phone within ten minutes returns the recent lead reference. **Back to home** and **New enquiry** are on the thank-you page. Keep the reference for the sales conversation.

At `/login`, enter your work email and password, then use **Sign in**. The app sends you to your role's home page. Invalid credentials appear beneath the form. The seed creates `director@sunpower.test`, `sales@sunpower.test`, `surveyor@sunpower.test`, `warehouse@sunpower.test`, `crew@sunpower.test` and `support@sunpower.test`, all with the demo password `sunpower123`. These are demo accounts.

In the workspace, the left menu contains the sections your role may open. On a narrow screen, **Open navigation** opens that menu and **Close navigation** closes it. The SunPower logo goes to your role's home page. Your name opens **Staff profile**, which shows your account details; the exit icon signs out. **Skip to content** jumps past the navigation for keyboard users. Lists and details show loading, empty or error messages; **Try again** repeats a failed load. **Previous** and **Next** change list pages when there are enough records. The × on a dialog, or Escape, closes it.

| Role | Home page | Main menu access |
| --- | --- | --- |
| Director | Operations overview | Every workspace section |
| Sales | Lead inbox | Leads, surveys, quotes, orders, catalog, invoices, subsidy |
| Surveyor | My site surveys | Assigned surveys |
| Warehouse | Stock | Stock, deliveries, serial lookup |
| Crew | My installations | Assigned installations, deliveries, serial lookup |
| Support | Service tickets | Tickets, serial lookup, installations, invoices |

The menu is a guide to access, but individual write actions have their own backend role checks. If an account lacks a route's role, the API returns 403. The director can view all workspace sections, while a few actions are intentionally restricted to the assigned surveyor or crew member.

## Lead inbox and customer calls

Sales and directors open **Lead inbox** to see customer, phone, source, requested kW, system type, status and received time. The list refreshes every 15 seconds. **Search name or phone** matches part of a customer name or phone number. **All statuses** filters to one of `NEW`, `CONTACTED`, `SURVEY_PENDING`, `SURVEY_DONE`, `QUOTED`, `WON` or `LOST`. **Newest first** uses the server's newest-first order; **Order page by status** reorders only the current page. Changing search or status returns to page 1. Select a customer name to open the lead.

**＋ New lead** opens manual entry for calls or WhatsApp contacts. Enter customer name, phone, address, pincode, source, requested capacity, system type, subsidy interest and optional notes; **Create lead** saves it and opens the lead. The system keeps lost leads as records rather than deleting them.

The lead detail shows contact and project facts plus call history. **Log customer call** expands a form for shadow-free roof area in square metres, monthly electricity bill in rupees, whether the grid is suitable, required call outcome and optional notes. **Log Call** saves a timestamped call; the first call moves a `NEW` lead to `CONTACTED`. **Request site survey** appears for a contacted lead and changes it to `SURVEY_PENDING`. **Schedule survey** then opens the scheduling form. After an approved survey, **Create a quote →** takes you to Quotes, where you enter the approved lead ID.

**Mark lead as lost** expands a form requiring a reason. **Mark as lost** changes any lead except a won or already lost lead to `LOST`; the reason remains visible. The standalone `MarkLostModal.jsx` component is currently not wired into this page, so users see the expandable form instead.

## Site surveys

**Site surveys** lists the survey ID, lead ID, surveyor ID, visit time and status. Surveyors see **My site surveys**, limited to assignments. Sales and directors can use **Schedule survey** on the list or from a pending lead. Choose an eligible contacted or survey-pending lead, an active surveyor and a visit time, then press **Schedule survey**. The form explains when no lead or surveyor is available and links to an existing survey for a lead. Scheduling a contacted lead also requests the survey. A lead cannot have another active survey.

Open a survey to see its roof data, review note and uploaded photos. An assigned surveyor can **Upload photo** (JPEG, PNG or WebP, up to 5 MiB) and **Submit survey** with roof direction, tilt in degrees, cable distance in metres and optional shadow notes. Sales or a director can then choose **approve** or **reject**, enter a review note and press **Save review**. Approval marks the lead `SURVEY_DONE` and unlocks quoting; rejection leaves a record of the reviewed survey.

## Catalog, products and packages

Sales and directors can open **Catalog**. The **Packages** and **Products** tabs change the list. Package rows show system type, capacity, active status and price; product rows show SKU, category, stock on hand and sale price. Select a name for its detail. Product names in a package's **Bill of materials** open that product.

Directors can use **Add product** on the Products tab. Enter a unique SKU, name, category, unit, sale price, cost, serial-tracking choice, optional warranty months and reorder level. The product detail has **Edit product** and **Save product**. Serialized products need warranty months before their delivered units can receive warranties. Prices are entered as rupees but stored as integer paise.

Directors can use **Create package** on the Packages tab. Set a name, price, system type, capacity for a system package, whether it is **Active**, and at least one bill-of-materials line. **Add item** adds a product/quantity pair; **Remove** deletes a line. A product cannot be selected twice. System packages automatically include and require the `INSTALLATION` service product; its row cannot be removed. **Create package** saves the template. On an existing package, **Edit package**, **Save package** and **Cancel** manage the same fields. Inactive packages cannot be selected for new quotes or shown publicly.

## Quotes and orders

**Quotes** lists quote number, customer ID, validity date, total and status. **Create quote** asks for an approved lead ID, package ID, validity date and optional subsidy amount in rupees. The survey must be approved, the package active, and its bill of materials nonempty. The system copies package products and current product sale prices into a draft quote. The IDs can be found in lead and catalog detail URLs or the list tables. A validity date in the past is rejected.

The package's displayed price is catalog information; the quote subtotal is calculated from its copied product lines. If those prices differ, review the draft lines before sending the quote.

The quote detail shows subtotal, subsidy, total and bill-of-materials lines. While `DRAFT`, **Edit line item** lets you choose an existing line and save its quantity and unit price with **Save line**. **Mark quote as sent** moves a draft to `SENT`. **Accept quote and open order** accepts a sent quote and creates one draft order. On an already accepted quote, **Open order** goes to that same order. **Print quote** opens the browser print dialog.

**Orders** lists order number, customer ID, status, total and minimum advance. Open an order to see the quote ID, total, minimum advance and total received. **Record payment** expands a form for amount in rupees, payment method (`UPI`, `CASH`, `CARD`, `BANK`) and optional reference; its button saves a real receipt. The configured minimum is 30% by default. Until the threshold is met, the page says how much more to receive. Once met, **Confirm order** appears. Confirmation creates one delivery pick list and one installation job; if the lead requested subsidy, it also creates a claim.

## Stock and deliveries

Warehouse and directors open **Stock** for product ID, SKU, product, on-hand quantity, reorder level and low-stock status. **Low stock only** toggles a filtered list. **Receive stock** opens fields for product ID, quantity, unit purchase cost in rupees and optional serial numbers, one per line. For a serialized product, supply exactly one distinct serial for each unit; a duplicate or already-used serial is rejected. For a nonserialized product, leave serials empty. **Receive stock** updates on-hand count and records the purchase movement.

Warehouse, crew and directors can view **Deliveries**. A confirmed order appears as a `PENDING` pick list. The detail shows each product's required quantity and scanned serial count. Warehouse or director can **Scan serial** by entering an in-stock serial belonging to a listed product, or use **Remove [serial]** to undo a scan before dispatch. The same serial cannot be used on another delivery, and scanned quantity cannot exceed the required quantity. When every serialized line has its full count, **Dispatch delivery** appears; its optional Vehicle field records transport. Dispatch reduces stock, marks scanned units dispatched and advances the order. **Mark delivered** appears on a dispatched delivery and can be used by warehouse, crew or director. It records delivery time, assigns the units to the customer and starts one warranty per scanned serial.

## Installation jobs

**Installations** lists job ID, order ID, scheduled start, crew lead ID and status. Crew see **My installations**, limited to their assigned jobs. On a `SCHEDULED` job, a director or support user can enter a crew lead ID, optional other crew IDs separated by commas, start and end times, then press **Save schedule**. Only active crew users may be assigned. A crew member cannot be booked for overlapping slots.

An assigned crew member uses **Start installation** to record the start time. During `IN_PROGRESS`, **Upload site photo** attaches proof. To finish, draw in **Customer signature** using a pointer or touch, or choose **Or upload a signature image**. **Clear signature** erases the drawing. Enter finish time, installed kW, optional test notes and customer name, then use **Complete installation**. A valid start and finish, positive capacity, at least one uploaded site photo and a signature are required. **View customer signature** opens saved proof. On a completed job, assigned crew use **Accept installation** to mark the job accepted and the dispatched order installed.

## Serial lookup and service tickets

Support, warehouse, crew and director can open **Serial lookup**. Choose **Serial number** or **Customer phone**, enter a full value in **Enter serial or phone**, then press **Look up**. Serial lookup returns one unit; phone lookup returns all units assigned to that exact customer phone. Results show serial, product, customer, warranty status and coverage end date. A missing serial produces an error; a phone with no assigned units shows an empty table. **Create ticket** appears beside assigned serials for support and director and carries that serial into the ticket form.

Support and director open **Tickets**. **Board** displays lanes for `OPEN`, `IN_PROGRESS`, `RESOLVED` and `CLOSED`; **List** displays a table. Select a ticket card or ticket number to open its dialog. **Search ticket number** applies a partial ticket-number search only after Enter or the ↵ button; **Clear search** removes it. **Assigned to me** filters by your staff ID. The **Serial lookup** button opens lookup. **＋ Create ticket** opens fields for equipment serial, fault code, issue description and priority (`LOW`, `NORMAL`, `HIGH`, `URGENT`). A ticket needs a serial already assigned to a customer. Warranty coverage is calculated from that serial, not entered by staff.

In a ticket dialog, **Overview** shows fault, priority, customer, assignee, whether service is covered and whether the customer has confirmed. **Edit assignment and priority** lets you enter an active crew or support staff ID and change priority; **Save changes** applies it. **Start work** moves `OPEN` to `IN_PROGRESS`. **Resolve ticket** requires resolution text and moves it to `RESOLVED`. **Record customer confirmation** records confirmation; **Close ticket** then closes it. The **Parts & labour** tab shows charge lines and **Add line** records `PART` or `LABOUR`, description, quantity and rupee unit price. Adding a line clears any earlier customer confirmation. At closure, coverage is checked again: an in-warranty ticket creates no charge; an out-of-warranty ticket needs positive billable lines and creates an invoice. **Open invoice #…** appears in the dialog after a close action returns an invoice ID.

## Invoices and subsidy claims

Sales and directors can use **Create invoice** on **Invoices** by entering an order ID. The invoice copies quote lines and any subsidy credit; prior order payments are linked to it. Support can view and receive invoice payments but cannot create order invoices. The list shows total, balance and status. The detail shows customer, issue date, lines and payments. **Record payment** appears while balance remains; it takes amount, method and optional reference. **Print invoice** opens the browser print dialog. Recording payments updates the invoice's `SENT`, `PARTIAL` or `PAID` status.

Sales and directors can view **Subsidy claims**. A claim is created when an order for a subsidy-interested lead is confirmed; its starting status is `NOT_APPLIED` and scheme is `Scheme pending`. The detail has **Update claim** with status (`NOT_APPLIED`, `SUBMITTED`, `APPROVED`, `PAID`, `REJECTED`), scheme, rupee amount, optional reference and notes. Save the external application reference here; this screen does not submit to a government service.

## Director overview and reports

Only the director sees **Operations overview**. **Today**, **This week** and **This month** change the period used for the financial cards, revenue chart and profit report. The cards show invoiced revenue, payments collected and outstanding invoice balance. The **Invoiced revenue** chart groups the selected period into hours or days. **Work in progress** links to surveys, orders, deliveries and installations. **Field & service** links to completed/unfinished installs, open tickets and low-stock items.

In **Reports**, **Profit per job** shows revenue, parts, labour and profit for jobs in the selected period. Click the **Profit** column heading to reverse sort direction. **Technician hours** shows hours, hourly rate and amount due; **Report month** changes its month. **Export CSV ↓** downloads the currently selected report, respecting the chosen period or month and profit sort. **Print** opens the browser print dialog for the overview.

## Shared behavior and common problems

- All money inputs are rupees; the API stores integer paise. For example, `₹1,250.50` becomes `125050` paise. Negative amounts are not accepted in ordinary payment or price forms.
- Dates and times entered in the browser are sent as timestamps; displayed record times use the user's locale. Reports use the India business day.
- Image uploads accept JPEG, PNG and WebP up to 5 MiB. A file with the wrong content or too much data is rejected.
- A rule or state conflict normally returns HTTP 409 with an explanation below the form. Fix the record's prerequisite and try again. A missing record returns 404, a missing sign-in returns 401 and a forbidden role returns 403.
- Lists without a specific search control still have pagination where shown. The current UI has text search on Leads and Tickets, exact serial/phone lookup, and the Stock low-stock filter. The Catalog, Quotes and other lists do not currently expose a text-search box even if some API endpoints accept search parameters.
- **Print** actions use the browser's print dialog and print stylesheet. **Export CSV** downloads a data file; neither action sends email.

## Suggested demo path

Submit an enquiry, sign in as Sales, open the lead, log a call, schedule a survey, sign in as the assigned Surveyor, submit it, then approve it as Sales or Director. Create a package quote, send and accept it, receive the advance and confirm the order. As Warehouse, scan each required serial, dispatch and mark delivered. As Director or Support, schedule the install; as assigned Crew, start, upload a photo, collect a signature, complete and accept it. Finally, look up a serial, create a support ticket, resolve it, record customer confirmation and close it. The seed also includes an older inverter `INV-OLD-2024-001` with expired coverage and panel `PNL-OLD-2024-001` with active coverage for service demonstrations.
