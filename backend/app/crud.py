"""Generic REST router factory used by the simpler master-data modules."""
from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Session

from .database import get_db
from .deps import audit, guard
from .models import User

HIDDEN = {"password_hash"}


def to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in HIDDEN}


def coerce(model, data: dict, skip=("id",)) -> dict:
    """Keep only real columns and convert JSON values to the column's Python type."""
    cols = {c.name: c for c in model.__table__.columns}
    out = {}
    for key, value in data.items():
        if key not in cols or key in skip or key in HIDDEN:
            continue
        col = cols[key]
        t = col.type
        try:
            if value is None or (value == "" and not isinstance(t, String)):
                value = None
            elif isinstance(t, Boolean):
                value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
            elif isinstance(t, Date) and isinstance(value, str):
                value = date.fromisoformat(value[:10])
            elif isinstance(t, DateTime) and isinstance(value, str):
                value = datetime.fromisoformat(value)
            elif isinstance(t, Integer):
                value = int(value)
            elif isinstance(t, Float):
                value = float(value)
        except (ValueError, TypeError):
            raise HTTPException(422, f"Invalid value for '{key}'")
        out[key] = value
    return out


def make_router(prefix: str, model, *, read=None, write=None, tag=None, order_desc=True, hook=None,
                redact=None) -> APIRouter:
    """read / write: tuple of allowed roles, or None meaning any logged-in user. Admin is always allowed.
    redact: (fields, roles) - the listed fields are removed from responses unless the user has one of `roles`."""
    def out(obj, user):
        d = to_dict(obj)
        if redact and user.role != "admin" and user.role not in redact[1]:
            for field in redact[0]:
                d.pop(field, None)
        return d

    r = APIRouter(prefix=f"/api/{prefix}", tags=[tag or prefix])
    read_guard = guard(*(read or ()))
    write_guard = guard(*(write or ()))
    label = model.__name__

    @r.get("")
    def list_items(request: Request, db: Session = Depends(get_db), user: User = read_guard):
        q = db.query(model)
        for key, value in request.query_params.items():
            if key in model.__table__.columns:
                q = q.filter(getattr(model, key) == coerce(model, {key: value}).get(key))
        q = q.order_by(model.id.desc() if order_desc else model.id.asc())
        return [out(o, user) for o in q.all()]

    @r.get("/{item_id}")
    def get_item(item_id: int, db: Session = Depends(get_db), user: User = read_guard):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, f"{label} not found")
        return out(obj, user)

    @r.post("")
    def create_item(data: dict = Body(...), db: Session = Depends(get_db), user: User = write_guard):
        obj = model(**coerce(model, data))
        if hook:
            hook(obj, user)
        db.add(obj)
        db.flush()
        audit(db, user, "create", prefix, obj.id)
        db.commit()
        return out(obj, user)

    @r.put("/{item_id}")
    def update_item(item_id: int, data: dict = Body(...), db: Session = Depends(get_db), user: User = write_guard):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, f"{label} not found")
        for k, v in coerce(model, data).items():
            setattr(obj, k, v)
        audit(db, user, "update", prefix, obj.id)
        db.commit()
        return out(obj, user)

    @r.delete("/{item_id}")
    def delete_item(item_id: int, db: Session = Depends(get_db), user: User = write_guard):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, f"{label} not found")
        db.delete(obj)
        audit(db, user, "delete", prefix, item_id)
        db.commit()
        return {"ok": True}

    return r
