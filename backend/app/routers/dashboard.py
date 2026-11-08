from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..crud import to_dict
from ..database import get_db
from ..deps import guard
from ..models import (Bill, Booking, Complaint, Flat, MaintenanceTask, Notice, User, Visitor)
from .maintenance import serialize_task, vendor_map

router = APIRouter(prefix="/api", tags=["dashboard"])


def compliance(db: Session) -> list[dict]:
    vendors = vendor_map(db)
    tasks = [serialize_task(t, vendors) for t in db.query(MaintenanceTask).filter(MaintenanceTask.active == True)]  # noqa: E712
    return sorted(tasks, key=lambda t: (t["days_left"] if t["days_left"] is not None else 10**6))


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = guard()):
    tasks = compliance(db)
    overdue = [t for t in tasks if t["status"] == "overdue"]
    soon = [t for t in tasks if t["status"] == "due_soon"]

    unpaid = db.query(Bill).filter(Bill.status != "paid")
    if user.role == "resident":
        unpaid = unpaid.filter(Bill.flat_id == (user.flat_id or -1))
    pending_dues = sum((b.base_amount or 0) + (b.fund_amount or 0) + (b.late_fee or 0) for b in unpaid)

    complaints = db.query(Complaint).filter(Complaint.status.in_(["open", "in_progress"]))
    if user.role not in ("admin", "secretary", "treasurer", "committee", "staff"):
        complaints = complaints.filter(Complaint.raised_by == user.id)

    visitors = db.query(Visitor).filter(Visitor.status == "in")
    pending_visitors = db.query(Visitor).filter(Visitor.status == "pending")
    if user.role == "resident":
        visitors = visitors.filter(Visitor.flat_id == (user.flat_id or -1))
        pending_visitors = pending_visitors.filter(Visitor.flat_id == (user.flat_id or -1))

    return {
        "role": user.role,
        "counts": {
            "flats": db.query(func.count(Flat.id)).scalar(),
            "residents": db.query(func.count(User.id)).filter(User.role == "resident", User.is_active == True).scalar(),  # noqa: E712
            "open_complaints": complaints.count(),
            "overdue_tasks": len(overdue),
            "due_soon_tasks": len(soon),
            "pending_dues": round(pending_dues, 2),
            "visitors_inside": visitors.count(),
            "pending_visitor_approvals": pending_visitors.count(),
            "upcoming_bookings": db.query(Booking).filter(Booking.date >= date.today(), Booking.status == "approved").count(),
        },
        "overdue_tasks": overdue,
        "upcoming_tasks": soon,
        "recent_notices": [to_dict(n) for n in db.query(Notice).order_by(Notice.id.desc()).limit(5)],
    }


@router.get("/reports/compliance")
def compliance_report(db: Session = Depends(get_db), user: User = guard()):
    """Which recurring duties are overdue, and for how long. Open to all residents (transparency)."""
    rows = compliance(db)
    return {
        "generated_on": date.today(),
        "overdue": [r for r in rows if r["status"] == "overdue"],
        "due_soon": [r for r in rows if r["status"] == "due_soon"],
        "ok": [r for r in rows if r["status"] == "ok"],
    }
