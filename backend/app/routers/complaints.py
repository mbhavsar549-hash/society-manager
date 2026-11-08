from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import COMMITTEE, Complaint, Flat, User, now

router = APIRouter(prefix="/api/complaints", tags=["complaints"])
HANDLERS = ("secretary", "committee", "staff")
SLA_HOURS = {"high": 24, "medium": 72, "low": 168}


def ser(c: Complaint, flats: dict, users: dict) -> dict:
    d = to_dict(c)
    d["flat_number"] = flats.get(c.flat_id)
    d["raised_by_name"] = users.get(c.raised_by)
    sla = SLA_HOURS.get(c.priority or "medium", 72)
    d["sla_hours"] = sla
    open_ = c.status in ("open", "in_progress")
    d["sla_breached"] = bool(open_ and c.created_at and (now() - c.created_at).total_seconds() > sla * 3600)
    return d


def maps(db: Session):
    return ({f.id: f.number for f in db.query(Flat)}, {u.id: u.name for u in db.query(User)})


@router.get("")
def list_complaints(status: str | None = None, db: Session = Depends(get_db), user: User = guard()):
    q = db.query(Complaint)
    if user.role not in COMMITTEE + ("staff",):
        q = q.filter(Complaint.raised_by == user.id)
    if status:
        q = q.filter(Complaint.status == status)
    flats, users = maps(db)
    return [ser(c, flats, users) for c in q.order_by(Complaint.id.desc())]


@router.post("")
def create_complaint(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard()):
    fields = coerce(Complaint, data, skip=("id", "status", "created_at", "resolved_at", "rating", "feedback", "raised_by"))
    if not fields.get("title"):
        raise HTTPException(422, "Title is required")
    if user.role == "resident" or not fields.get("flat_id"):
        fields["flat_id"] = user.flat_id
    fields["priority"] = fields.get("priority") or "medium"
    c = Complaint(**fields, raised_by=user.id)
    db.add(c)
    db.flush()
    audit(db, user, "create", "complaint", c.id, c.title)
    db.commit()
    return ser(c, *maps(db))


@router.put("/{complaint_id}")
def update_complaint(complaint_id: int, data: dict = Body(...), db: Session = Depends(get_db),
                     user: User = guard(*HANDLERS)):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    allowed = {k: v for k, v in data.items() if k in ("status", "assigned_to", "resolution", "priority", "category")}
    if allowed.get("status") not in (None, "open", "in_progress", "resolved", "closed"):
        raise HTTPException(422, "Invalid status")
    for k, v in coerce(Complaint, allowed).items():
        setattr(c, k, v)
    if c.status in ("resolved", "closed") and not c.resolved_at:
        c.resolved_at = now()
    elif c.status in ("open", "in_progress"):
        c.resolved_at = None
    audit(db, user, "update", "complaint", c.id, f"status={c.status}")
    db.commit()
    return ser(c, *maps(db))


@router.post("/{complaint_id}/rate")
def rate(complaint_id: int, data: dict = Body(...), db: Session = Depends(get_db), user: User = guard()):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    if c.raised_by != user.id:
        raise HTTPException(403, "Only the person who raised the complaint can rate it")
    if c.status not in ("resolved", "closed"):
        raise HTTPException(400, "You can rate only after it is resolved")
    rating = int(data.get("rating", 0))
    if not 1 <= rating <= 5:
        raise HTTPException(422, "Rating must be 1 to 5")
    c.rating = rating
    c.feedback = data.get("feedback")
    db.commit()
    return ser(c, *maps(db))


@router.delete("/{complaint_id}")
def delete_complaint(complaint_id: int, db: Session = Depends(get_db), user: User = guard("secretary")):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    db.delete(c)
    audit(db, user, "delete", "complaint", complaint_id)
    db.commit()
    return {"ok": True}
