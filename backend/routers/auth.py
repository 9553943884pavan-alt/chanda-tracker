import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import OTPCode, User


load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

router = APIRouter(prefix="/auth", tags=["auth"])
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(days=7)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


@dataclass
class PendingSignup:
    full_name: str
    email: str
    roll_no: str
    role: str
    year: int | None
    branch: str | None
    gender: str | None
    expires_at: datetime


pending_signups: dict[str, PendingSignup] = {}


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str
    roll_no: str = Field(min_length=1, max_length=20)
    role: Literal["admin", "collector", "giver"]
    year: int | None = Field(default=None, ge=1, le=4)
    branch: Literal["IT", "ECE"] | None = None
    gender: Literal["M", "F"] | None = None


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_pending_signup(email: str) -> PendingSignup | None:
    pending = pending_signups.get(email)
    if pending and pending.expires_at > datetime.now(timezone.utc):
        return pending
    pending_signups.pop(email, None)
    return None


async def send_brevo_email(email: str, subject: str, text_content: str) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("FROM_EMAIL")
    if not api_key or not from_email:
        raise HTTPException(status_code=503, detail="Email service is not configured")

    payload = {
        "sender": {"email": from_email},
        "to": [{"email": email}],
        "subject": subject,
        "textContent": text_content,
    }
    headers = {"accept": "application/json", "api-key": api_key, "content-type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(BREVO_URL, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Unable to send email") from exc


def require_jwt_secret() -> str:
    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET is not set")
    return jwt_secret


async def send_signup_otp(email: str, otp: str) -> None:
    print(f"\n==========================================")
    print(f"[CHANDA TRACKER OTP] Email: {email} | Code: {otp}")
    print(f"==========================================\n")
    try:
        await send_brevo_email(
            email,
            "Your Chanda Tracker verification code",
            f"Your Chanda Tracker verification code is {otp}. It expires in 10 minutes.",
        )
    except HTTPException as exc:
        print(f"[CHANDA TRACKER OTP] Email sending failed: {exc.detail}. Use console OTP code: {otp}")


async def send_reset_otp(email: str, otp: str) -> None:
    print(f"\n==========================================")
    print(f"[CHANDA TRACKER RESET OTP] Email: {email} | Code: {otp}")
    print(f"==========================================\n")
    try:
        await send_brevo_email(
            email,
            "Your Chanda Tracker password reset code",
            f"Your Chanda Tracker password reset code is {otp}. It expires in 10 minutes.",
        )
    except HTTPException as exc:
        print(f"[CHANDA TRACKER RESET OTP] Email sending failed: {exc.detail}. Use console OTP code: {otp}")


def validate_password_rules(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters long")
    has_letter = any(c.isalpha() for c in password)
    has_digit_or_special = any(not c.isalpha() for c in password)
    if not (has_letter and has_digit_or_special):
        raise HTTPException(
            status_code=422,
            detail="Password must contain a mix of letters and numbers/symbols",
        )


@router.post("/signup")
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(request.email)
    if not email.endswith("@iiita.ac.in"):
        raise HTTPException(status_code=422, detail="Email must end with @iiita.ac.in")
    if request.role == "admin" and request.year is not None:
        raise HTTPException(status_code=422, detail="Admin accounts must not include a year")
    if request.role != "admin":
        if request.year is None:
            raise HTTPException(status_code=422, detail="Year is required for student accounts")
        if request.gender is None:
            raise HTTPException(status_code=422, detail="Gender is required for student accounts")
        if request.gender == "M" and request.branch is None:
            raise HTTPException(status_code=422, detail="Branch is required for male student accounts")

    existing_user = await db.scalar(select(User).where((User.email == email) | (User.roll_no == request.roll_no)))
    if existing_user:
        raise HTTPException(status_code=409, detail="Email or roll number is already registered")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    pending_signups[email] = PendingSignup(
        full_name=request.full_name,
        email=email,
        roll_no=request.roll_no,
        role=request.role,
        year=request.year,
        branch=request.branch,
        gender=request.gender,
        expires_at=now + timedelta(minutes=10),
    )
    db.add(
        OTPCode(
            email=email,
            code_hash=password_context.hash(otp),
            purpose="signup",
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        )
    )

    try:
        await db.commit()
        await send_signup_otp(email, otp)
    except Exception as exc:
        await db.rollback()
        pending_signups.pop(email, None)
        raise HTTPException(status_code=500, detail="Failed to initialize signup process") from exc

    return {"message": "Verification code sent. Check your email (or server log in dev) to continue signup."}



@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    validate_password_rules(request.password)
    email = normalize_email(request.email)
    pending = get_pending_signup(email)
    if not pending:
        raise HTTPException(status_code=400, detail="Signup request expired or not found")


    otp_record = await db.scalar(
        select(OTPCode)
        .where(
            OTPCode.email == email,
            OTPCode.purpose == "signup",
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
        .order_by(desc(OTPCode.id))
        .limit(1)
    )
    if not otp_record:
        raise HTTPException(status_code=400, detail="Verification code expired or not found")

    attempts = otp_record.attempts or 0
    if attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many invalid verification attempts")

    if not password_context.verify(request.otp, otp_record.code_hash):
        otp_record.attempts = attempts + 1
        await db.commit()
        if attempts + 1 >= 5:
            raise HTTPException(status_code=429, detail="Too many invalid verification attempts")
        raise HTTPException(status_code=400, detail="Invalid verification code")

    user = User(
        full_name=pending.full_name,
        email=pending.email,
        roll_no=pending.roll_no,
        password_hash=password_context.hash(request.password),
        role=pending.role,
        year=pending.year,
        branch=pending.branch,
        gender=pending.gender,
        email_verified=True,
    )
    db.add(user)
    await db.delete(otp_record)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email or roll number is already registered") from exc

    pending_signups.pop(email, None)
    return {"message": "Email verified and account created"}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(request.email)
    if not email.endswith("@iiita.ac.in"):
        raise HTTPException(status_code=422, detail="Email must end with @iiita.ac.in")

    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    db.add(
        OTPCode(
            email=email,
            code_hash=password_context.hash(otp),
            purpose="reset",
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        )
    )

    try:
        await db.commit()
        await send_reset_otp(email, otp)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to initialize password reset") from exc

    return {"message": "Reset code sent. Check your email (or server log in dev) to continue."}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    validate_password_rules(request.new_password)
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match")

    email = normalize_email(request.email)
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")

    otp_record = await db.scalar(
        select(OTPCode)
        .where(
            OTPCode.email == email,
            OTPCode.purpose == "reset",
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
        .order_by(desc(OTPCode.id))
        .limit(1)
    )
    if not otp_record:
        raise HTTPException(status_code=400, detail="Reset code expired or not found")

    attempts = otp_record.attempts or 0
    if attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many invalid reset attempts")

    if not password_context.verify(request.otp, otp_record.code_hash):
        otp_record.attempts = attempts + 1
        await db.commit()
        if attempts + 1 >= 5:
            raise HTTPException(status_code=429, detail="Too many invalid reset attempts")
        raise HTTPException(status_code=400, detail="Invalid reset code")

    user.password_hash = password_context.hash(request.new_password)
    await db.delete(otp_record)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reset password") from exc

    return {"message": "Password reset successfully. You can now sign in with your new password."}


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = normalize_email(request.email)
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not password_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email is not verified")

    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "exp": datetime.now(timezone.utc) + JWT_EXPIRY,
        },
        require_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )
    return {"access_token": token, "token_type": "bearer"}
