from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import lookup_session
from app.db.session import get_db


def require_admin(
    npra_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = lookup_session(db, npra_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
