from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.core.rate_limit import auth_rate_limiter
from app.core.tenant import resolve_tenant_code
from app.models.models import Membership, Tenant
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserProfile
from app.services.auth import authenticate_user, issue_tokens, register_user, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


def enforce_auth_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{request.url.path}:{client_host}"
    if auth_rate_limiter.hit(rate_limit_key):
        return
    raise HTTPException(status_code=429, detail="Too many auth requests. Try again later.")


@router.post("/register", response_model=UserProfile)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserProfile:
    enforce_auth_rate_limit(request)
    user = register_user(db, email=payload.email, full_name=payload.full_name, password=payload.password)
    db.commit()
    return UserProfile.model_validate(user)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    enforce_auth_rate_limit(request)
    user = authenticate_user(db, email=payload.email, password=payload.password)
    access, refresh = issue_tokens(db, user)
    write_audit_log(db, action="auth.login", actor_user_id=user.id, tenant_id=None, entity_type="user", entity_id=user.id)
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    enforce_auth_rate_limit(request)
    access, refresh_token = rotate_refresh_token(db, payload.refresh_token)
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.get("/me", response_model=UserProfile)
def me(request: Request, user=Depends(current_user), db: Session = Depends(get_db)) -> UserProfile:
    tenant_role = None
    try:
        tenant_code = resolve_tenant_code(request).source
    except HTTPException:
        tenant_code = None
    if tenant_code:
        membership = db.scalar(
            select(Membership)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(Membership.user_id == user.id, Membership.is_active.is_(True), Tenant.code == tenant_code)
        )
        if membership is not None:
            tenant_role = membership.role.name
    return UserProfile(id=user.id, email=user.email, full_name=user.full_name, tenant_role=tenant_role)
