import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from dateutil.relativedelta import relativedelta

from sqlalchemy import bindparam, func, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.billing.models import Invoice, Payment
from app.modules.installs.models import InstallCrew, InstallJob
from app.modules.users.models import User
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
        InstallJob.status.in_(("COMPLETED", "ACCEPTED")), InstallJob.finished_at >= start, InstallJob.finished_at < end
    ))
    jobs_unfinished = _scalar(
        db,
        "SELECT COUNT(*) FROM install_jobs WHERE status NOT IN ('COMPLETED', 'ACCEPTED')",
    )
    open_tickets = _scalar(
        db,
        "SELECT COUNT(*) FROM tickets WHERE status <> 'CLOSED'",
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


def profit_per_job(db: Session, range_: str | None = None, sort: str | None = None) -> list[ProfitJobOut]:
    # Dispatch movements snapshot the unit cost. Prefer the actual purchase
    # costs of scanned units for a serialized line, including historical jobs.
    activity_filter = ""
    params = {}
    if range_:
        start, end = period_bounds(range_)
        params = {"start": start, "end": end}
        activity_filter = """WHERE (o.confirmed_at >= :start AND o.confirmed_at < :end)
            OR (d.dispatched_at >= :start AND d.dispatched_at < :end)
            OR (inv.issued_at >= :start AND inv.issued_at < :end)
            OR (ij.finished_at >= :start AND ij.finished_at < :end)"""
    query = text(f"""
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
        {activity_filter}
        ORDER BY o.id DESC
    """)
    timestamp = InstallJob.started_at.type
    if range_:
        query = query.bindparams(bindparam("start", type_=timestamp), bindparam("end", type_=timestamp))
    query = query.columns(started_at=timestamp, finished_at=timestamp)
    result = []
    for row in db.execute(query, params).mappings():
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
    if sort:
        result.sort(key=lambda job: job.profit_paise, reverse=sort == "desc")
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
    try:
        day = date.fromisoformat(month + "-01") if month else None
    except ValueError as exc:
        raise AppError("INVALID_REPORT_MONTH", "Use a report month in YYYY-MM format.", 400) from exc
    start, end = period_bounds("month", day)
    shifts = db.execute(
        select(User.id, User.name, User.hourly_rate_paise, InstallJob.started_at, InstallJob.finished_at)
        .select_from(InstallJob)
        .join(InstallCrew, InstallCrew.install_job_id == InstallJob.id)
        .join(User, User.id == InstallCrew.user_id)
        .where(InstallJob.started_at >= start, InstallJob.started_at < end, InstallJob.finished_at.is_not(None))
        .order_by(User.id)
    )
    durations = {}
    for user_id, name, rate, started, finished in shifts:
        key = (user_id, name, rate)
        durations[key] = durations.get(key, timedelta()) + (finished - started)
    rows = [
        TechHoursOut(
            user_id=user_id, name=name, hourly_rate_paise=rate, hours_worked=duration / HOUR,
            amount_due_paise=(duration // MICROSECOND) * rate // (HOUR // MICROSECOND),
        )
        for (user_id, name, rate), duration in durations.items()
    ]
    return sorted(rows, key=lambda row: (-row.hours_worked, row.user_id))


def export_csv(db: Session, range_: str = "month", report: str = "profit", month: str | None = None,
               sort: str = "desc") -> str:
    if report == "hours":
        rows = technician_hours(db, month)
        fields = TechHoursOut.model_fields
    else:
        rows = profit_per_job(db, range_, sort)
        fields = ProfitJobOut.model_fields
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(fields))
    writer.writeheader()
    writer.writerows(row.model_dump() for row in rows)
    return buf.getvalue()
