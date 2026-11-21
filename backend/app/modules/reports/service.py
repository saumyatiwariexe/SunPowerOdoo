import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from dateutil.relativedelta import relativedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.billing.models import Invoice, Payment
from app.modules.installs.models import InstallJob
from app.modules.reports.schemas import ProfitJobOut, SummaryOut, TechHoursOut, UnfinishedOut


# The business calendar follows India Standard Time. Timestamps are stored in UTC.
BUSINESS_TZ = timezone(timedelta(hours=5, minutes=30))
HOUR = timedelta(hours=1)
MICROSECOND = timedelta(microseconds=1)


def period_bounds(range_: str, day: date | None = None) -> tuple[datetime, datetime]:
    day = day or datetime.now(BUSINESS_TZ).date()
    if range_ == "week":
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(weeks=1)
    elif range_ == "month":
        start = day.replace(day=1)
        end = start + relativedelta(months=1)
    else:
        start, end = day, day + timedelta(days=1)
    return datetime.combine(start, time.min, BUSINESS_TZ), datetime.combine(end, time.min, BUSINESS_TZ)


def _scalar(db: Session, sql: str):
    return db.scalar(text(sql)) or 0


def summary(db: Session, range_: str = "today") -> SummaryOut:
    start, end = period_bounds(range_)
    invoice_window = (Invoice.issued_at >= start, Invoice.issued_at < end)
    revenue_paise = db.scalar(select(func.sum(Invoice.total_paise)).where(*invoice_window)) or 0
    collected_paise = db.scalar(select(func.sum(Payment.amount_paise)).where(
        Payment.paid_at >= start, Payment.paid_at < end
    )) or 0
    due = Invoice.total_paise - Invoice.paid_paise
    outstanding_paise = db.scalar(select(func.sum(due)).where(*invoice_window, due > 0)) or 0

    jobs_completed = db.scalar(select(func.count(InstallJob.id)).where(
        InstallJob.status == "COMPLETED", InstallJob.finished_at >= start, InstallJob.finished_at < end
    ))
    jobs_unfinished = _scalar(
        db,
        "SELECT COUNT(*) FROM install_jobs WHERE status NOT IN ('COMPLETED', 'ACCEPTED')",
    )
    open_tickets = _scalar(
        db,
        "SELECT COUNT(*) FROM tickets WHERE status NOT IN ('RESOLVED', 'CLOSED')",
    )
    low_stock_count = _scalar(
        db,
        "SELECT COUNT(*) FROM products WHERE on_hand <= reorder_level",
    )

    return SummaryOut(
        range=range_,
        revenue_paise=revenue_paise or 0,
        collected_paise=collected_paise or 0,
        outstanding_paise=outstanding_paise,
        jobs_completed=jobs_completed or 0,
        jobs_unfinished=jobs_unfinished or 0,
        open_tickets=open_tickets or 0,
        low_stock_count=low_stock_count or 0,
    )


def profit_per_job(db: Session) -> list[ProfitJobOut]:
    # Dispatch movements snapshot the unit cost. Prefer the actual purchase
    # costs of scanned units for a serialized line, including historical jobs.
    query = text("""
        SELECT o.id AS order_id, o.number AS order_number, c.name AS customer_name,
               COALESCE(inv.total_paise, 0) AS revenue_paise,
               COALESCE((SELECT SUM(su.purchase_cost_paise)
                         FROM serial_units su WHERE su.delivery_id = d.id), 0)
               + COALESCE((SELECT SUM(-m.qty * m.cost_paise)
                           FROM stock_movements m
                           WHERE m.ref_type = 'DELIVERY' AND m.ref_id = d.id
                             AND m.reason = 'DISPATCH'
                             AND NOT EXISTS (SELECT 1 FROM serial_units su
                                             WHERE su.delivery_id = d.id AND su.product_id = m.product_id)), 0)
                   AS parts_paise,
               ij.started_at, ij.finished_at,
               COALESCE((SELECT SUM(u.hourly_rate_paise) FROM install_crew ic
                         JOIN users u ON u.id = ic.user_id WHERE ic.install_job_id = ij.id), 0) AS crew_rate
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        LEFT JOIN invoices inv ON inv.order_id = o.id
        LEFT JOIN deliveries d ON d.order_id = o.id AND d.status IN ('DISPATCHED', 'DELIVERED')
        LEFT JOIN install_jobs ij ON ij.order_id = o.id
        ORDER BY o.id DESC
    """).columns(started_at=InstallJob.started_at.type, finished_at=InstallJob.finished_at.type)
    result = []
    for row in db.execute(query).mappings():
        duration = timedelta()
        if row.started_at and row.finished_at:
            duration = row.finished_at - row.started_at
        labour = (duration // MICROSECOND) * int(row.crew_rate) // (HOUR // MICROSECOND)
        parts = int(row.parts_paise)
        result.append(ProfitJobOut(
            order_id=row.order_id, order_number=row.order_number, customer_name=row.customer_name,
            revenue_paise=row.revenue_paise, parts_paise=parts, labour_paise=labour,
            profit_paise=row.revenue_paise - parts - labour,
        ))
    return result


def unfinished(db: Session) -> UnfinishedOut:
    awaiting_survey = _scalar(
        db,
        "SELECT COUNT(*) FROM leads WHERE status = 'SURVEY_PENDING'",
    )
    awaiting_payment = _scalar(
        db,
        "SELECT COUNT(*) FROM orders WHERE status = 'DRAFT'",
    )
    awaiting_dispatch = _scalar(
        db,
        "SELECT COUNT(*) FROM deliveries WHERE status = 'PENDING'",
    )
    awaiting_install = _scalar(
        db,
        "SELECT COUNT(*) FROM install_jobs WHERE status IN ('SCHEDULED', 'IN_PROGRESS')",
    )
    return UnfinishedOut(
        awaiting_survey=awaiting_survey or 0,
        awaiting_payment=awaiting_payment or 0,
        awaiting_dispatch=awaiting_dispatch or 0,
        awaiting_install=awaiting_install or 0,
    )


def technician_hours(db: Session, month: str | None = None) -> list[TechHoursOut]:
    """
    month format: YYYY-MM  (defaults to current month)
    Returns hours worked + amount due per technician from install jobs and tickets.
    """
    if month:
        try:
            y, m = month.split("-")
            period = f"'{y}-{m}-01'::date"
        except Exception:
            period = "date_trunc('month', CURRENT_DATE)"
    else:
        period = "date_trunc('month', CURRENT_DATE)"

    sql = f"""
        SELECT
            u.id AS user_id,
            u.name,
            u.hourly_rate_paise,
            COALESCE(
                SUM(
                    EXTRACT(EPOCH FROM (ij.finished_at - ij.started_at)) / 3600.0
                ),
            0) AS hours_worked
        FROM users u
        JOIN install_crew ic ON ic.user_id = u.id
        JOIN install_jobs ij ON ij.id = ic.install_job_id
        WHERE ij.started_at >= {period}
          AND ij.started_at < {period} + interval '1 month'
          AND ij.finished_at IS NOT NULL
        GROUP BY u.id, u.name, u.hourly_rate_paise
        ORDER BY hours_worked DESC
    """
    rows = db.execute(text(sql)).mappings().all()
    return [
        TechHoursOut(
            user_id=r["user_id"],
            name=r["name"],
            hours_worked=float(r["hours_worked"]),
            hourly_rate_paise=int(r["hourly_rate_paise"]),
            amount_due_paise=int(float(r["hours_worked"]) * int(r["hourly_rate_paise"])),
        )
        for r in rows
    ]


def export_csv(db: Session, range_: str = "month") -> str:
    """Return a CSV string of profit-per-job data."""
    rows = profit_per_job(db)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["order_id", "order_number", "customer_name", "revenue_paise", "parts_paise", "labour_paise", "profit_paise"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row.model_dump())
    return buf.getvalue()
