import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from google.auth.exceptions import GoogleAuthError
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
# OTP codes are printed to the server console only when DEBUG=true is set (dev environments)
DEBUG_MODE = os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


class GoogleSignupRequest(BaseModel):
    credential: str  # Google ID token (JWT)
    full_name: str = Field(min_length=1, max_length=100)
    roll_no: str = Field(min_length=1, max_length=20)
    role: Literal["collector", "giver"]
    year: int = Field(ge=1, le=4)
    branch: Literal["IT", "ECE"] | None = None
    gender: Literal["M", "F"] | None = None


class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token (JWT)


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


def verify_google_id_token(credential: str) -> dict:
    """Verify a Google ID token and return its claims. Raises HTTPException on failure."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google authentication is not configured on the server")
    try:
        idinfo = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=5,  # Tolerate up to 5 seconds of clock skew
        )
        return idinfo
    except (ValueError, GoogleAuthError) as exc:
        error_msg = str(exc)
        print(f"[GOOGLE AUTH ERROR] {error_msg}")
        raise HTTPException(status_code=401, detail=f"Invalid Google credential: {error_msg}") from exc


async def send_signup_otp(email: str, otp: str) -> None:
    if DEBUG_MODE:
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
        if DEBUG_MODE:
            print(f"[CHANDA TRACKER OTP] Email sending failed: {exc.detail}. Use console OTP code: {otp}")


async def send_reset_otp(email: str, otp: str) -> None:
    if DEBUG_MODE:
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
        if DEBUG_MODE:
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
    db.add(
        OTPCode(
            email=email,
            code_hash=password_context.hash(otp),
            purpose="signup",
            # pending signup data travels with the code so a restart mid-signup loses nothing
            payload={
                "full_name": request.full_name,
                "email": email,
                "roll_no": request.roll_no,
                "role": request.role,
                "year": request.year,
                "branch": request.branch,
                "gender": request.gender,
            },
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        )
    )

    try:
        await db.commit()
        await send_signup_otp(email, otp)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to initialize signup process") from exc

    return {"message": "Verification code sent. Check your email to continue signup."}



@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    validate_password_rules(request.password)
    email = normalize_email(request.email)

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
    if not otp_record or not otp_record.payload:
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

    pending = otp_record.payload
    user = User(
        full_name=pending["full_name"],
        email=email,
        roll_no=pending["roll_no"],
        password_hash=password_context.hash(request.password),
        role=pending["role"],
        year=pending.get("year"),
        branch=pending.get("branch"),
        gender=pending.get("gender"),
        email_verified=True,
    )
    db.add(user)
    await db.delete(otp_record)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email or roll number is already registered") from exc

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


def _issue_jwt(user: User) -> dict:
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


@router.post("/google/signup")
async def google_signup(request: GoogleSignupRequest, db: AsyncSession = Depends(get_db)):
    # Defense in depth: the frontend hides "admin", but never trust client input alone.
    if request.role == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot be created through signup")

    # Apply the same student validation rules as the email signup flow.
    if request.year is None:
        raise HTTPException(status_code=422, detail="Year is required")
    if request.gender is None:
        raise HTTPException(status_code=422, detail="Gender is required")
    if request.gender == "M" and request.branch is None:
        raise HTTPException(status_code=422, detail="Branch is required for male student accounts")

    # Verify the Google ID token.
    idinfo = verify_google_id_token(request.credential)

    # Enforce IIITA-only accounts (hd claim + email domain, both must pass).
    hd = idinfo.get("hd")
    email = (idinfo.get("email") or "").strip().lower()
    if hd != "iiita.ac.in" or not email.endswith("@iiita.ac.in"):
        raise HTTPException(status_code=403, detail="Only IIITA college Google accounts are allowed")

    google_sub = idinfo.get("sub")

    # Reject if email, roll_no, or google_sub already exists — direct them to login instead.
    existing_user = await db.scalar(
        select(User).where(
            (User.email == email) | (User.roll_no == request.roll_no) | (User.google_sub == google_sub)
        )
    )
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email, roll number, or Google account already exists. Please sign in instead.",
        )

    user = User(
        full_name=request.full_name,
        email=email,
        roll_no=request.roll_no,
        google_sub=google_sub,
        password_hash=None,
        role=request.role,
        year=request.year,
        branch=request.branch,
        gender=request.gender,
        email_verified=True,  # Google already verified the email
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="An account with this email, roll number, or Google account already exists. Please sign in instead.",
        ) from exc

    return _issue_jwt(user)


@router.post("/google/login")
async def google_login(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    idinfo = verify_google_id_token(request.credential)

    hd = idinfo.get("hd")
    email = (idinfo.get("email") or "").strip().lower()
    if hd != "iiita.ac.in" or not email.endswith("@iiita.ac.in"):
        raise HTTPException(status_code=403, detail="Only IIITA college Google accounts are allowed")

    google_sub = idinfo.get("sub")

    # Look up by google_sub first, then by email (covers accounts created via either method).
    user = await db.scalar(
        select(User).where((User.google_sub == google_sub) | (User.email == email))
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found for this Google account — please sign up first",
        )

    return _issue_jwt(user)
