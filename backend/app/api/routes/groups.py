from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles, tenant_context
from app.core.audit import write_audit_log
from app.core.db import get_db
from app.models.models import Group, GroupMember, Membership, RoleName, Tenant, User
from app.schemas.user import GroupCreate, GroupMemberCreate, GroupMemberRead, GroupRead

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupRead])
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
    return [GroupRead(id=group.id, name=group.name, member_count=member_count) for group, member_count in rows]


@router.post("", response_model=GroupRead)
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


@router.get("/{group_id}/members", response_model=list[GroupMemberRead])
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


@router.post("/{group_id}/members", response_model=GroupMemberRead)
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


@router.delete("/{group_id}/members/{user_id}")
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
