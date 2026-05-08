from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.core.security import hash_password
from app.models.models import Group, GroupMember, Membership, Role, RoleName, Tenant, User
from app.schemas.user import (
    GroupCreate,
    GroupMemberCreate,
    GroupMemberRead,
    GroupRead,
    UserCreate,
    UserRead,
    UserRoleUpdate,
    UserTenantBind,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])
groups_router = APIRouter(prefix="/groups", tags=["groups"])


@groups_router.get("", response_model=list[GroupRead])
def list_groups(
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[GroupRead]:
    rows = db.execute(
        select(Group, func.count(GroupMember.id))
        .outerjoin(
            GroupMember,
            (GroupMember.group_id == Group.id) & (GroupMember.tenant_id == tenant.id),
        )
        .where(Group.tenant_id == tenant.id)
        .group_by(Group.id)
        .order_by(Group.name.asc(), Group.id.asc())
    ).all()
    return [
        GroupRead(id=group.id, name=group.name, member_count=member_count)
        for group, member_count in rows
    ]


@groups_router.post("", response_model=GroupRead)
def create_group(
    payload: GroupCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> GroupRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Group name is required")
    existing = db.scalar(
        select(Group.id).where(
            Group.tenant_id == tenant.id,
            func.lower(Group.name) == name.lower(),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Group already exists")
    group = Group(tenant_id=tenant.id, name=name)
    db.add(group)
    db.flush()
    write_audit_log(
        db,
        action="groups.create",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="group",
        entity_id=group.id,
        details=group.name,
    )
    db.commit()
    return GroupRead(id=group.id, name=group.name, member_count=0)


@groups_router.get("/{group_id}/members", response_model=list[GroupMemberRead])
def list_group_members(
    group_id: int,
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[GroupMemberRead]:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.tenant_id == tenant.id))
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    rows = db.execute(
        select(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .where(
            GroupMember.tenant_id == tenant.id,
            GroupMember.group_id == group_id,
        )
        .order_by(User.full_name.asc(), User.id.asc())
    ).all()
    return [
        GroupMemberRead(
            id=member.id,
            group_id=member.group_id,
            user_id=member.user_id,
            full_name=user.full_name,
            email=user.email,
        )
        for member, user in rows
    ]


@groups_router.post("/{group_id}/members", response_model=GroupMemberRead)
def add_group_member(
    group_id: int,
    payload: GroupMemberCreate,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> GroupMemberRead:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.tenant_id == tenant.id))
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    target_membership = db.scalar(
        select(Membership).where(
            Membership.tenant_id == tenant.id,
            Membership.user_id == payload.user_id,
            Membership.is_active.is_(True),
        )
    )
    if target_membership is None:
        raise HTTPException(status_code=422, detail="User must belong to the current tenant")
    existing_member = db.scalar(
        select(GroupMember).where(
            GroupMember.tenant_id == tenant.id,
            GroupMember.group_id == group_id,
            GroupMember.user_id == payload.user_id,
        )
    )
    if existing_member is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return GroupMemberRead(
            id=existing_member.id,
            group_id=existing_member.group_id,
            user_id=existing_member.user_id,
            full_name=user.full_name,
            email=user.email,
        )
    member = GroupMember(tenant_id=tenant.id, group_id=group_id, user_id=payload.user_id)
    db.add(member)
    db.flush()
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    write_audit_log(
        db,
        action="groups.member.add",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="group",
        entity_id=group_id,
        details=f"user_id={payload.user_id}",
    )
    db.commit()
    return GroupMemberRead(
        id=member.id,
        group_id=member.group_id,
        user_id=member.user_id,
        full_name=user.full_name,
        email=user.email,
    )


@groups_router.delete("/{group_id}/members/{user_id}")
def remove_group_member(
    group_id: int,
    user_id: int,
    membership: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> dict:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.tenant_id == tenant.id))
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    target = db.scalar(
        select(GroupMember).where(
            GroupMember.tenant_id == tenant.id,
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Group member not found")
    db.delete(target)
    write_audit_log(
        db,
        action="groups.member.remove",
        actor_user_id=membership.user_id,
        tenant_id=tenant.id,
        entity_type="group",
        entity_id=group_id,
        details=f"user_id={user_id}",
    )
    db.commit()
    return {"deleted": True, "group_id": group_id, "user_id": user_id}


@router.get("", response_model=list[UserRead])
def list_users(
    _: Membership = Depends(require_roles(RoleName.org_admin, RoleName.teacher, RoleName.system_admin)),
    tenant: Tenant = Depends(tenant_context),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    rows = db.execute(
        select(User, Role.name)
        .join(Membership, Membership.user_id == User.id)
        .join(Role, Membership.role_id == Role.id)
        .where(
            Membership.tenant_id == tenant.id,
            Role.name != RoleName.system_admin.value,
        )
    ).all()
    return [
        UserRead.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "role_name": role_name,
            }
        )
        for user, role_name in rows
    ]


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
