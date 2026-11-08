"""Daily rule engine: reminders, overdue alerts, escalation and expiry warnings."""
import os
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import Asset, Bill, Document, MaintenanceTask, Notification, Vendor

ESCALATE_AFTER_DAYS = int(os.getenv("ESCALATE_AFTER_DAYS", "7"))
EXPIRY_WARN_DAYS = 30


def _notify(db: Session, key: str, message: str, level="info", target_role="committee") -> int:
    if db.query(Notification).filter(Notification.key == key).first():
        return 0
    db.add(Notification(key=key, message=message, level=level, target_role=target_role))
    return 1


def run_checks(db: Session) -> dict:
    today = date.today()
    created = 0
    escalated = 0

    for t in db.query(MaintenanceTask).filter(MaintenanceTask.active == True).all():  # noqa: E712
        if not t.next_due:
            continue
        days = (t.next_due - today).days
        if days < 0:
            late = -days
            created += _notify(db, f"overdue-{t.id}-{today}",
                               f"OVERDUE: {t.title} was due on {t.next_due} ({late} days late)", "danger")
            if late >= ESCALATE_AFTER_DAYS and not t.escalated:
                t.escalated = True
                escalated += 1
                created += _notify(db, f"escalate-{t.id}-{t.next_due}",
                                   f"ESCALATION: {t.title} is {late} days overdue and still not done.",
                                   "danger", target_role=None)
        elif days <= (t.reminder_days or 0):
            created += _notify(db, f"due-{t.id}-{t.next_due}",
                               f"Reminder: {t.title} is due on {t.next_due} (in {days} days)", "warning")

    horizon = today + timedelta(days=EXPIRY_WARN_DAYS)
    for a in db.query(Asset).filter(Asset.next_service != None, Asset.next_service <= horizon).all():  # noqa: E711
        created += _notify(db, f"asset-{a.id}-{a.next_service}", f"Asset service due: {a.name} on {a.next_service}", "warning")
    for v in db.query(Vendor).filter(Vendor.contract_end != None, Vendor.contract_end <= horizon).all():  # noqa: E711
        created += _notify(db, f"vendor-{v.id}-{v.contract_end}", f"Contract/AMC ending: {v.name} on {v.contract_end}", "warning")
    for d in db.query(Document).filter(Document.expiry_date != None, Document.expiry_date <= horizon).all():  # noqa: E711
        created += _notify(db, f"doc-{d.id}-{d.expiry_date}", f"Document expiring: {d.title} on {d.expiry_date}", "warning")

    overdue_bills = db.query(Bill).filter(Bill.status == "pending", Bill.due_date < today).all()
    for b in overdue_bills:
        b.status = "overdue"

    db.commit()
    return {"notifications_created": created, "escalated": escalated, "bills_marked_overdue": len(overdue_bills)}


def scheduled_job():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        run_checks(db)
    finally:
        db.close()
