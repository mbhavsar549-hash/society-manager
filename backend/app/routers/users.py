from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud import coerce, to_dict
from ..database import get_db
from ..deps import audit, guard
from ..models import ROLES, User
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])
MANAGERS = ("secretary",)


@router.get("")
def list_users(db: Session = Depends(get_db), user: User = guard("secretary", "treasurer", "committee")):
    return [to_dict(u) for u in db.query(User).order_by(User.id)]


@router.post("")
def create_user(data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*MANAGERS)):
    password = data.get("password") or ""
    if len(password) < 6:
        raise HTTPException(422, "Password must be at least 6 characters")
    fields = coerce(User, data)
    fields["email"] = (fields.get("email") or "").lower().strip()
    if fields.get("role") not in ROLES:
        raise HTTPException(422, f"Role must be one of {ROLES}")
    if fields.get("role") == "admin" and user.role != "admin":
        raise HTTPException(403, "Only an admin can create admins")
    if db.query(User).filter(User.email == fields["email"]).first():
        raise HTTPException(409, "Email already exists")
    obj = User(**fields, password_hash=hash_password(password))
    db.add(obj)
    db.flush()
    audit(db, user, "create", "users", obj.id, obj.email)
    db.commit()
    return to_dict(obj)


@router.put("/{user_id}")
def update_user(user_id: int, data: dict = Body(...), db: Session = Depends(get_db), user: User = guard(*MANAGERS)):
    obj = db.get(User, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    fields = coerce(User, data)
    if "email" in fields and fields["email"]:
        fields["email"] = fields["email"].lower().strip()
    if fields.get("role") == "admin" and user.role != "admin":
        raise HTTPException(403, "Only an admin can grant the admin role")
    for k, v in fields.items():
        setattr(obj, k, v)
    if data.get("password"):
        obj.password_hash = hash_password(data["password"])
    audit(db, user, "update", "users", obj.id)
    db.commit()
    return to_dict(obj)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user: User = guard()):
    if user.role != "admin":
        raise HTTPException(403, "Only an admin can delete users")
    obj = db.get(User, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    if obj.id == user.id:
        raise HTTPException(400, "You cannot delete yourself")
    obj.is_active = False  # soft delete keeps history intact
    audit(db, user, "deactivate", "users", obj.id)
    db.commit()
    return {"ok": True}
