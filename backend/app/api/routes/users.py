from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.core.security import hash_password
from app.models.models import Membership, Role, RoleName, Tenant, User
from app.schemas.user import UserCreate, UserRead, UserRoleUpdate, UserTenantBind, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    users = db.scalars(select(User).join(Membership).where(Membership.tenant_id == tenant.id)).all()
    return [UserRead.model_validate(item) for item in users]


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> UserRead:
    if membership.role.name != RoleName.system_admin.value and payload.role_name == RoleName.system_admin.value:
        raise HTTPException(status_code=403, detail="Only system admins can grant system admin role")
    role = db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")
    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role_id=role.id, is_active=True))
    write_audit_log(db, action="users.create", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="user", entity_id=user.id)
    db.commit()
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> UserRead:
    target = db.scalar(select(User).join(Membership).where(User.id == user_id, Membership.tenant_id == tenant.id))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.is_active is not None:
        target.is_active = payload.is_active
    write_audit_log(db, action="users.update", actor_user_id=membership.user_id, tenant_id=tenant.id, entity_type="user", entity_id=target.id)
    db.commit()
    return UserRead.model_validate(target)


@router.patch("/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> UserRead:
    if membership.role.name != RoleName.system_admin.value and payload.role_name == RoleName.system_admin.value:
        raise HTTPException(status_code=403, detail="Only system admins can grant system admin role")
    target_membership = db.scalar(select(Membership).where(Membership.tenant_id == tenant.id, Membership.user_id == user_id))
    if target_membership is None:
        raise HTTPException(status_code=404, detail="User membership not found")
    role = db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")
    target_membership.role_id = role.id
    db.add(target_membership)
    db.commit()
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    write_audit_log(
        db,
        action="users.role.update",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="user",
        entity_id=user_id,
        details=payload.role_name,
    )
    db.commit()
    return UserRead.model_validate(target)


@router.post("/{user_id}/tenants")
def bind_user_to_tenant(
    user_id: int,
    payload: UserTenantBind,
    membership: Membership = Depends(require_roles(RoleName.system_admin)),
    db: Session = Depends(get_db),
) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.code == payload.tenant_code))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    role = db.scalar(select(Role).where(Role.name == payload.role_name))
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    membership_row = db.scalar(select(Membership).where(Membership.user_id == user_id, Membership.tenant_id == tenant.id))
    if membership_row is None:
        membership_row = Membership(user_id=user_id, tenant_id=tenant.id, role_id=role.id, is_active=payload.is_active)
    else:
        membership_row.role_id = role.id
        membership_row.is_active = payload.is_active
    db.add(membership_row)
    db.commit()
    write_audit_log(
        db,
        action="users.tenant.bind",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="user",
        entity_id=user_id,
        details=payload.role_name,
    )
    db.commit()
    return {"user_id": user_id, "tenant_code": tenant.code, "role_name": payload.role_name, "is_active": payload.is_active}
