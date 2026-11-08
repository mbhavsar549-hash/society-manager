"""Notifications, polls & voting, SOS, audit log."""
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import (COMMITTEE, AuditLog, Incident, Notification, NotificationRead,
                      Poll, PollVote, User)

router = APIRouter(prefix="/api", tags=["community"])


# ---------------------------------------------------------------- notifications
def visible_notifications(db: Session, user: User):
    conds = [Notification.target_role == None, Notification.target_role == user.role,  # noqa: E711
             Notification.user_id == user.id]
    if user.role in COMMITTEE:
        conds.append(Notification.target_role == "committee")
    return db.query(Notification).filter(or_(*conds))


@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = guard()):
    read = {r.notification_id for r in db.query(NotificationRead).filter(NotificationRead.user_id == user.id)}
    rows = visible_notifications(db, user).order_by(Notification.id.desc()).limit(100).all()
    return {
        "unread": sum(1 for n in rows if n.id not in read),
        "items": [{**to_dict(n), "read": n.id in read} for n in rows],
    }


@router.post("/notifications/read-all")
def read_all(db: Session = Depends(get_db), user: User = guard()):
    read = {r.notification_id for r in db.query(NotificationRead).filter(NotificationRead.user_id == user.id)}
    for n in visible_notifications(db, user).all():
        if n.id not in read:
            db.add(NotificationRead(user_id=user.id, notification_id=n.id))
    db.commit()
    return {"ok": True}


@router.post("/notifications/broadcast")
def broadcast(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard("secretary", "committee")):
    """Emergency / announcement alert to everyone. Hook SMS/WhatsApp/email providers in here."""
    message = (data.get("message") or "").strip()
    if not message:
        raise HTTPException(422, "Message is required")
    db.add(Notification(message=message, level=data.get("level", "warning"), target_role=None))
    audit(db, user, "broadcast", "notification", None, message)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- SOS
@router.post("/sos")
def sos(data: dict = Body(default={}), db: Session = Depends(get_db), user: User = guard()):
    flat = f" (Flat {user.flat_id})" if user.flat_id else ""
    inc = Incident(title=f"SOS from {user.name}{flat}", type="SOS", location=data.get("location"),
                   description=data.get("message"), reported_by=user.id)
    db.add(inc)
    db.flush()
    db.add(Notification(key=f"sos-{inc.id}", message=f"🚨 SOS raised by {user.name}{flat}. {data.get('message') or ''}".strip(),
                        level="danger", target_role=None))
    audit(db, user, "sos", "incident", inc.id)
    db.commit()
    return {"ok": True, "incident_id": inc.id}


# ---------------------------------------------------------------- polls
def ser_poll(p: Poll, votes: list[PollVote], me: int) -> dict:
    options = [o.strip() for o in p.options.splitlines() if o.strip()]
    counts = {o: 0 for o in options}
    mine = None
    for v in votes:
        counts[v.option] = counts.get(v.option, 0) + 1
        if v.user_id == me:
            mine = v.option
    d = to_dict(p)
    d.update(options_list=options, counts=counts, total_votes=len(votes), my_vote=mine,
             closed=bool(p.closes_on and p.closes_on < date.today()))
    return d


@router.get("/polls")
def list_polls(db: Session = Depends(get_db), user: User = guard()):
    votes = db.query(PollVote).all()
    return [ser_poll(p, [v for v in votes if v.poll_id == p.id], user.id)
            for p in db.query(Poll).order_by(Poll.id.desc())]


@router.post("/polls")
def create_poll(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard("secretary", "committee")):
    f = coerce(Poll, data, skip=("id", "created_by", "created_at"))
    if not f.get("question") or len([o for o in (f.get("options") or "").splitlines() if o.strip()]) < 2:
        raise HTTPException(422, "A question and at least two options (one per line) are required")
    p = Poll(**f, created_by=user.id)
    db.add(p)
    db.flush()
    audit(db, user, "create", "poll", p.id, p.question)
    db.commit()
    return ser_poll(p, [], user.id)


@router.post("/polls/{poll_id}/vote")
def vote(poll_id: int, data: dict = Body(...), db: Session = Depends(get_db), user: User = guard()):
    p = db.get(Poll, poll_id)
    if not p:
        raise HTTPException(404, "Poll not found")
    if p.closes_on and p.closes_on < date.today():
        raise HTTPException(400, "Poll is closed")
    option = data.get("option")
    if option not in [o.strip() for o in p.options.splitlines()]:
        raise HTTPException(422, "Invalid option")
    existing = db.query(PollVote).filter(PollVote.poll_id == p.id, PollVote.user_id == user.id).first()
    if existing:
        existing.option = option
    else:
        db.add(PollVote(poll_id=p.id, user_id=user.id, option=option))
    db.commit()
    return ser_poll(p, db.query(PollVote).filter(PollVote.poll_id == p.id).all(), user.id)


@router.delete("/polls/{poll_id}")
def delete_poll(poll_id: int, db: Session = Depends(get_db), user: User = guard("secretary")):
    p = db.get(Poll, poll_id)
    if not p:
        raise HTTPException(404, "Poll not found")
    db.query(PollVote).filter(PollVote.poll_id == poll_id).delete()
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- audit log
@router.get("/audit")
def audit_log(limit: int = 300, db: Session = Depends(get_db), user: User = guard("secretary", "committee", "treasurer")):
    return [to_dict(a) for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))]
