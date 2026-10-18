from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AdminUser, Session as DbSession, utcnow


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), digest_hex)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: AdminUser, hours: int) -> str:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(DbSession(token_hash=token_hash(token), admin_user_id=user.id, created_at=now, expires_at=now + timedelta(hours=hours)))
    db.commit()
    return token


def lookup_session(db: Session, token: str | None) -> AdminUser | None:
    if not token:
        return None
    now = utcnow()
    db.execute(delete(DbSession).where(DbSession.expires_at < now))
    row = db.execute(
        select(DbSession, AdminUser)
        .join(AdminUser, AdminUser.id == DbSession.admin_user_id)
        .where(DbSession.token_hash == token_hash(token), DbSession.expires_at >= now)
    ).first()
    db.commit()
    return row[1] if row else None


def revoke_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(DbSession).where(DbSession.token_hash == token_hash(token)))
        db.commit()
