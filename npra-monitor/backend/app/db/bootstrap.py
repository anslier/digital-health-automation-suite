from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import AdminUser, ScheduleConfig
from app.db.session import SessionLocal, create_schema


def bootstrap() -> None:
    settings = get_settings()
    create_schema()
    with SessionLocal() as db:
        if not db.scalar(select(AdminUser).where(AdminUser.email == settings.admin_email.lower())):
            db.add(AdminUser(email=settings.admin_email.lower(), password_hash=hash_password(settings.admin_password)))
        if not db.get(ScheduleConfig, 1):
            db.add(ScheduleConfig(id=1, enabled=False, cadence="MONTHLY", local_time="09:00", day_of_month=8))
        db.commit()
