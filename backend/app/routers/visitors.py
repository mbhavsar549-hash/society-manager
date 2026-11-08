"""Visitor management: pre-approval, gate approval, pass-code check-in, check-out."""
import secrets
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import Flat, User, Visitor, now

router = APIRouter(prefix="/api/visitors", tags=["visitors"])
GATE = ("security", "secretary")
APPROVERS = ("resident", "secretary", "committee")


def ser(v: Visitor, flats: dict) -> dict:
    d = to_dict(v)
    d["flat_number"] = flats.get(v.flat_id)
    return d


def flat_map(db):
    return {f.id: f.number for f in db.query(Flat)}


def own_flat_or_403(v: Visitor, user: User):
    if user.role == "resident" and v.flat_id != user.flat_id:
        raise HTTPException(403, "This visitor is not for your flat")


@router.get("")
def list_visitors(status: str | None = None, db: Session = Depends(get_db),
                  user: User = guard("resident", "security", "secretary", "committee")):
    q = db.query(Visitor)
    if user.role == "resident":
        q = q.filter(Visitor.flat_id == (user.flat_id or -1))
    if status:
        q = q.filter(Visitor.status == status)
    flats = flat_map(db)
    return [ser(v, flats) for v in q.order_by(Visitor.id.desc()).limit(300)]


@router.post("")
def create_visitor(data: dict = Body(...), db: Session = Depends(get_db),
                   user: User = guard("resident", "security", "secretary")):
    """Resident -> pre-approved with a pass code. Guard -> 'pending' until the resident approves."""
    fields = coerce(Visitor, data, skip=("id", "status", "pass_code", "in_time", "out_time", "created_by", "created_at"))
    if not fields.get("name"):
        raise HTTPException(422, "Visitor name is required")
    if user.role == "resident":
        fields["flat_id"] = user.flat_id
        status, code = "approved", f"{secrets.randbelow(900000) + 100000}"
    else:
        if not fields.get("flat_id"):
            raise HTTPException(422, "flat_id is required")
        status, code = "pending", None
    v = Visitor(**fields, status=status, pass_code=code, created_by=user.id)
    db.add(v)
    db.flush()
    audit(db, user, "create", "visitor", v.id, v.name)
    db.commit()
    return ser(v, flat_map(db))


@router.post("/verify")
def verify_code(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*GATE)):
    code = str(data.get("pass_code", "")).strip()
    v = db.query(Visitor).filter(Visitor.pass_code == code, Visitor.status == "approved").first() if code else None
    if not v:
        raise HTTPException(404, "Invalid or already used pass code")
    return ser(v, flat_map(db))


def _get(db, visitor_id) -> Visitor:
    v = db.get(Visitor, visitor_id)
    if not v:
        raise HTTPException(404, "Visitor not found")
    return v


@router.post("/{visitor_id}/approve")
def approve(visitor_id: int, db: Session = Depends(get_db), user: User = guard(*APPROVERS)):
    v = _get(db, visitor_id)
    own_flat_or_403(v, user)
    if v.status != "pending":
        raise HTTPException(400, f"Visitor is already {v.status}")
    v.status = "approved"
    v.pass_code = v.pass_code or f"{secrets.randbelow(900000) + 100000}"
    audit(db, user, "approve", "visitor", v.id)
    db.commit()
    return ser(v, flat_map(db))


@router.post("/{visitor_id}/reject")
def reject(visitor_id: int, db: Session = Depends(get_db), user: User = guard(*APPROVERS)):
    v = _get(db, visitor_id)
    own_flat_or_403(v, user)
    if v.status not in ("pending", "approved"):
        raise HTTPException(400, f"Visitor is already {v.status}")
    v.status = "rejected"
    audit(db, user, "reject", "visitor", v.id)
    db.commit()
    return ser(v, flat_map(db))


@router.post("/{visitor_id}/checkin")
def checkin(visitor_id: int, db: Session = Depends(get_db), user: User = guard(*GATE)):
    v = _get(db, visitor_id)
    if v.status != "approved":
        raise HTTPException(400, f"Cannot check in: visitor is '{v.status}', resident approval is required")
    v.status, v.in_time = "in", now()
    audit(db, user, "checkin", "visitor", v.id)
    db.commit()
    return ser(v, flat_map(db))


@router.post("/{visitor_id}/checkout")
def checkout(visitor_id: int, db: Session = Depends(get_db), user: User = guard(*GATE)):
    v = _get(db, visitor_id)
    if v.status != "in":
        raise HTTPException(400, "Visitor is not inside")
    v.status, v.out_time = "out", now()
    audit(db, user, "checkout", "visitor", v.id)
    db.commit()
    return ser(v, flat_map(db))
