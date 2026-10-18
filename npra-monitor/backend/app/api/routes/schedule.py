from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import ScheduleConfig, utcnow
from app.db.session import get_db
from app.jobs.scheduler import build_trigger

router = APIRouter(prefix="/schedule", tags=["schedule"], dependencies=[Depends(require_admin)])


class ScheduleUpdate(BaseModel):
    enabled: bool
    cadence: str = Field(pattern="^(DAILY|WEEKLY|MONTHLY)$")
    local_time: str
    weekday: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int = Field(default=8, ge=1, le=28)
    timezone: str = "Asia/Kuala_Lumpur"

    @field_validator("local_time")
    @classmethod
    def valid_time(cls, value: str):
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("local_time must be HH:MM")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown timezone") from exc
        return value


def serialize(c: ScheduleConfig):
    next_time = build_trigger(c).get_next_fire_time(None, datetime.now(ZoneInfo(c.timezone))) if c.enabled else None
    return {
        "enabled": c.enabled,
        "cadence": c.cadence,
        "local_time": c.local_time,
        "weekday": c.weekday,
        "day_of_month": c.day_of_month,
        "timezone": c.timezone,
        "revision": c.revision,
        "updated_at": c.updated_at,
        "next_run_at": next_time.isoformat() if next_time else None,
    }


@router.get("")
def get_schedule(db: Session = Depends(get_db)):
    return serialize(db.get(ScheduleConfig, 1))


@router.put("")
def put_schedule(payload: ScheduleUpdate, db: Session = Depends(get_db)):
    config = db.get(ScheduleConfig, 1)
    if payload.cadence == "WEEKLY" and payload.weekday is None:
        raise HTTPException(400, "weekday is required for a weekly schedule")
    for field, value in payload.model_dump().items():
        setattr(config, field, value)
    config.revision += 1
    config.updated_at = utcnow()
    db.commit()
    db.refresh(config)
    return serialize(config)
