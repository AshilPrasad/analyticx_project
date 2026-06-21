"""
auth_routes.py — Signup / signin / current-user endpoints.

/api/auth/signup  — create an account, returns a JWT
/api/auth/signin  — authenticate, returns a JWT
/api/auth/me      — return the authenticated user's profile
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import User, get_db

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Schemas ───────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class SigninRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")

    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=email,
        name=(req.name or "").strip() or None,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@auth_router.post("/signin", response_model=AuthResponse)
async def signin(req: SigninRequest, db: AsyncSession = Depends(get_db)):
    email = req.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@auth_router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
