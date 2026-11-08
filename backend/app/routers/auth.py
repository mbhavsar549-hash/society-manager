from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..crud import to_dict
from ..database import get_db
from ..deps import audit, current_user
from ..models import User
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    phone: str | None = None
    flat_id: int | None = None
    resident_type: str | None = "owner"


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user.id, user.role), "user": to_dict(user)}


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Public self-registration. Always creates a *resident*; admin can change the role later."""
    email = body.email.lower().strip()
    if len(body.password) < 6:
        raise HTTPException(422, "Password must be at least 6 characters")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(name=body.name, email=email, phone=body.phone, flat_id=body.flat_id,
                resident_type=body.resident_type, role="resident", password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    audit(db, user, "register", "users", user.id)
    db.commit()
    return {"access_token": create_token(user.id, user.role), "user": to_dict(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return to_dict(user)


@router.put("/me")
def update_me(data: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    for key in ("name", "phone", "family_members", "vehicles", "emergency_contact"):
        if key in data:
            setattr(user, key, data[key])
    db.commit()
    return to_dict(user)


@router.post("/change-password")
def change_password(body: PasswordIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Old password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(422, "Password must be at least 6 characters")
    user.password_hash = hash_password(body.new_password)
    audit(db, user, "change_password", "users", user.id)
    db.commit()
    return {"ok": True}
