from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuditLog, User
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def current_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(token)
    user = db.get(User, int(payload["sub"])) if payload else None
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid or expired token")
    return user


def guard(*roles: str):
    """Dependency: any logged-in user if no roles given, else one of `roles` (admin always allowed)."""

    def dep(user: User = Depends(current_user)) -> User:
        if roles and user.role != "admin" and user.role not in roles:
            raise HTTPException(403, "You do not have permission for this action")
        return user

    return Depends(dep)


def audit(db: Session, user: User | None, action: str, entity: str, entity_id: int | None = None, detail: str = ""):
    db.add(AuditLog(
        user_id=user.id if user else None,
        user_name=user.name if user else "system",
        action=action, entity=entity, entity_id=entity_id, detail=(detail or "")[:500],
    ))
