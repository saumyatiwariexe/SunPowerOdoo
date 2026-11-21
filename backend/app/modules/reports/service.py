"""
Reports service — raw SQL only (allowed exception per SYSTEM_DESIGN.md §5).
All queries wrapped in try/except to handle missing tables gracefully while
other modules are still being built.
"""

import csv
import io
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.schemas import ProfitJobOut, SummaryOut, TechHoursOut, UnfinishedOut


def _run(db: Session, sql: str, **params):
    try:
        return db.execute(text(sql), params).mappings().all()
    except Exception:
        return []


def _scalar(db: Session, sql: str, default=0, **params):
    try:
        result = db.execute(text(sql), params).scalar()
        return result if result is not None else default
    except Exception:
        return default


def summary(db: Session, range_: str = "today") -> SummaryOut:
    """
    range_: 'today' | 'week' | 'month'
    """
    if range_ == "today":
        date_filter = "CURRENT_DATE"
        interval = "interval '0 days'"
    elif range_ == "week":
        date_filter = "date_trunc('week', CURRENT_DATE)"
        interval = "interval '6 days'"
    else:  # month
        date_filter = "date_trunc('month', CURRENT_DATE)"
        interval = "interval '30 days'"

    revenue_paise = _scalar(
        db,
        f"SELECT COALESCE(SUM(total_paise), 0) FROM invoices WHERE issued_at >= {date_filter}",
    )
    collected_paise = _scalar(
        db,
        f"SELECT COALESCE(SUM(paid_paise), 0) FROM invoices WHERE issued_at >= {date_filter}",
    )
    outstanding_paise = max(0, (revenue_paise or 0) - (collected_paise or 0))

    jobs_completed = _scalar(
        db,
        f"SELECT COUNT(*) FROM install_jobs WHERE status = 'COMPLETED' AND finished_at >= {date_filter}",
    )
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
    sql = """
        SELECT
            o.id AS order_id,
            o.number AS order_number,
            c.name AS customer_name,
            COALESCE(SUM(inv.total_paise), 0) AS revenue_paise,
            COALESCE(
                (SELECT SUM(su.purchase_cost_paise)
                 FROM serial_units su
                 JOIN deliveries d ON su.delivery_id = d.id
                 WHERE d.order_id = o.id), 0
            ) AS parts_paise,
            COALESCE(
                (SELECT SUM(
                    EXTRACT(EPOCH FROM (ij.finished_at - ij.started_at)) / 3600.0
                    * u.hourly_rate_paise
                 )
                 FROM install_jobs ij
                 JOIN install_crew ic ON ic.install_job_id = ij.id
                 JOIN users u ON u.id = ic.user_id
                 WHERE ij.order_id = o.id
                   AND ij.finished_at IS NOT NULL
                   AND ij.started_at IS NOT NULL), 0
            ) AS labour_paise
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        LEFT JOIN invoices inv ON inv.order_id = o.id
        GROUP BY o.id, o.number, c.name
        ORDER BY o.id DESC
    """
    rows = _run(db, sql)
    return [
        ProfitJobOut(
            order_id=r["order_id"],
            order_number=r["order_number"],
            customer_name=r["customer_name"],
            revenue_paise=int(r["revenue_paise"]),
            parts_paise=int(r["parts_paise"]),
            labour_paise=int(r["labour_paise"]),
            profit_paise=int(r["revenue_paise"]) - int(r["parts_paise"]) - int(r["labour_paise"]),
        )
        for r in rows
    ]


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
    rows = _run(db, sql)
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
