from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import NotificationDelivery


settings = get_settings()


def send_mock_notification(db: Session, *, tenant_id: int | None, user_id: int | None, payload: dict) -> NotificationDelivery:
    record = NotificationDelivery(
        tenant_id=tenant_id,
        user_id=user_id,
        channel="mock",
        target=settings.demo_notification_target,
        payload=payload,
        status="sent",
    )
    db.add(record)
    return record
