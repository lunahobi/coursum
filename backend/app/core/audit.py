from sqlalchemy.orm import Session

from app.models.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    action: str,
    actor_user_id: int | None,
    tenant_id: int | None,
    entity_type: str,
    entity_id: int | None,
    details: str = "",
) -> None:
    db.add(
        AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
