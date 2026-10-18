from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.security import create_session, revoke_session, verify_password
from app.db.models import AdminUser
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(AdminUser).where(AdminUser.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_session(db, user, get_settings().session_hours)
    response.set_cookie(
        "npra_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=get_settings().session_hours * 3600,
        path="/",
    )
    return {"email": user.email}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_session(db, request.cookies.get("npra_session"))
    response.delete_cookie("npra_session", path="/")
    return {"ok": True}


@router.get("/me")
def me(user: AdminUser = Depends(require_admin)):
    return {"id": user.id, "email": user.email}
