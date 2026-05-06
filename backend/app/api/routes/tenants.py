from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import active_membership, current_user, require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.models.models import Membership, RoleName, Tenant, User
from app.schemas.tenant import TenantCreate, TenantRead, TenantSelectRequest, TenantUpdate
from app.schemas.user import UserRead


router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantRead])
def list_tenants(user=Depends(current_user), db: Session = Depends(get_db)) -> list[TenantRead]:
    tenants = db.scalars(
        select(Tenant)
        .join(Membership)
        .where(Membership.user_id == user.id, Membership.is_active.is_(True))
        .order_by(Tenant.name.asc(), Tenant.id.asc())
    ).all()
    return [TenantRead.model_validate(item) for item in tenants]


@router.get("/current", response_model=TenantRead)
def current(tenant: Tenant = Depends(tenant_context)) -> TenantRead:
    return TenantRead.model_validate(tenant)


@router.post("/select", response_model=TenantRead)
def select_tenant(payload: TenantSelectRequest, membership=Depends(active_membership), db: Session = Depends(get_db)) -> TenantRead:
    tenant = db.scalar(select(Tenant).where(Tenant.code == payload.code))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    allowed = db.scalar(
        select(Membership.id).where(
            Membership.user_id == membership.user_id,
            Membership.tenant_id == tenant.id,
            Membership.is_active.is_(True),
        )
    )
    if allowed is None:
        raise HTTPException(status_code=403, detail="Tenant membership required")
    write_audit_log(db, action="tenant.select", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="tenant", entity_id=tenant.id)
    db.commit()
    return TenantRead.model_validate(tenant)


@router.post("", response_model=TenantRead)
def create_tenant(
    payload: TenantCreate,
    membership: Membership = Depends(require_roles(RoleName.system_admin)),
    db: Session = Depends(get_db),
) -> TenantRead:
    if db.scalar(select(Tenant.id).where(Tenant.code == payload.code)):
        raise HTTPException(status_code=400, detail="Tenant code already exists")
    if db.scalar(select(Tenant.id).where(Tenant.name == payload.name)):
        raise HTTPException(status_code=400, detail="Tenant name already exists")
    tenant = Tenant(name=payload.name, code=payload.code, locale=payload.locale, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    write_audit_log(
        db,
        action="tenants.create",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="tenant",
        entity_id=tenant.id,
        details=tenant.name,
    )
    db.commit()
    return TenantRead.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    membership: Membership = Depends(require_roles(RoleName.system_admin)),
    db: Session = Depends(get_db),
) -> TenantRead:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if payload.name is not None:
        tenant.name = payload.name
    if payload.locale is not None:
        tenant.locale = payload.locale
    if payload.is_active is not None:
        tenant.is_active = payload.is_active
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    write_audit_log(
        db,
        action="tenants.update",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="tenant",
        entity_id=tenant.id,
        details=tenant.name,
    )
    db.commit()
    return TenantRead.model_validate(tenant)


@router.post("/{tenant_id}/deactivate", response_model=TenantRead)
def deactivate_tenant(
    tenant_id: int,
    membership: Membership = Depends(require_roles(RoleName.system_admin)),
    db: Session = Depends(get_db),
) -> TenantRead:
    return update_tenant(tenant_id, TenantUpdate(is_active=False), membership, db)


@router.get("/{tenant_id}/users", response_model=list[UserRead])
def list_tenant_users(
    tenant_id: int,
    _: Membership = Depends(require_roles(RoleName.system_admin)),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    users = db.scalars(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == tenant_id)
        .order_by(User.full_name.asc(), User.id.asc())
    ).all()
    return [UserRead.model_validate(user) for user in users]
