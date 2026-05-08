import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.core.tenant import get_current_tenant
from app.models.models import Membership, RoleName, Tenant, User

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable")
    return user


def tenant_context(request: Request, db: Session = Depends(get_db)) -> Tenant:
    return get_current_tenant(request, db)


def active_membership(
    user: User = Depends(current_user),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.tenant_id == tenant.id, Membership.is_active.is_(True))
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required")
    return membership


def require_roles(*allowed: RoleName):
    def _checker(membership: Membership = Depends(active_membership)) -> Membership:
        if membership.role.name not in {role.value for role in allowed}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return membership

    return _checker
