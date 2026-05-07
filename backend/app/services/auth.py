from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.security import create_token, hash_password, verify_password
from app.models.models import RefreshToken, User


settings = get_settings()


def register_user(db: Session, *, email: str, full_name: str, password: str) -> User:
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(email=email, full_name=full_name, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    write_audit_log(db, action="auth.register", actor_user_id=user.id, tenant_id=None, entity_type="user", entity_id=user.id)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is deactivated")
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_token(str(user.id), "access", settings.access_token_minutes)
    refresh = create_token(str(user.id), "refresh", settings.refresh_token_minutes)
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.refresh_token_minutes),
            revoked=False,
        )
    )
    return access, refresh


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    record = db.scalar(select(RefreshToken).where(RefreshToken.token == refresh_token, RefreshToken.revoked.is_(False)))
    if record is None or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")
    record.revoked = True
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return issue_tokens(db, user)
