import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import CollectorGroup, CollectorProfile, Payment, User
from storage import get_signed_url, upload_file


router = APIRouter(prefix="/giver", tags=["giver"])
MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024
# UPI UTR: exactly 12 digits (e.g. 139709650010)
UTR_PATTERN = re.compile(r"^\d{12}$")
# PhonePe Transaction ID: T followed by 20-23 digits (total length 21-24)
PHONEPE_TXN_PATTERN = re.compile(r"^T\d{20,23}$")


def is_valid_transaction_ref(ref: str) -> bool:
    ref = ref.strip()
    return bool(UTR_PATTERN.match(ref)) or bool(PHONEPE_TXN_PATTERN.match(ref))


async def get_current_giver(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "giver":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Giver access required")
    return current_user


async def find_assigned_collector(
    giver: User,
    db: AsyncSession,
) -> tuple[CollectorProfile | None, User]:
    if giver.year is None or giver.gender is None:
        raise HTTPException(status_code=400, detail="Giver profile is missing year or gender")

    target_branch = None if giver.gender == "F" else giver.branch
    if giver.gender == "M" and target_branch is None:
        raise HTTPException(status_code=400, detail="Male giver profile is missing branch")

    group_filters = [
        CollectorGroup.year == giver.year,
        CollectorGroup.gender == giver.gender,
    ]
    if giver.gender == "F":
        group_filters.append(CollectorGroup.branch.is_(None))
    else:
        group_filters.append(CollectorGroup.branch == target_branch)

    collector_group = await db.scalar(select(CollectorGroup).where(*group_filters))

    # First attempt: lookup via collector_group_id
    if collector_group:
        assignment = await db.execute(
            select(CollectorProfile, User)
            .join(User, User.id == CollectorProfile.user_id)
            .where(
                CollectorProfile.collector_group_id == collector_group.id,
                User.role == "collector",
            )
            .limit(1)
        )
        result = assignment.first()
        if result:
            return result[0], result[1]

    # Second attempt: find collector User directly by group criteria
    user_filters = [
        User.role == "collector",
        User.year == giver.year,
        User.gender == giver.gender,
    ]
    if giver.gender == "M":
        user_filters.append(User.branch == target_branch)

    collector_user = await db.scalar(select(User).where(*user_filters).limit(1))
    if not collector_user:
        raise HTTPException(status_code=404, detail="No collector has been assigned for your year and branch yet.")

    profile = await db.scalar(
        select(CollectorProfile).where(CollectorProfile.user_id == collector_user.id)
    )
    return profile, collector_user


@router.get("/my-collector")
async def get_my_collector(
    current_user: User = Depends(get_current_giver),
    db: AsyncSession = Depends(get_db),
):
    profile, collector = await find_assigned_collector(current_user, db)
    if not profile or not profile.qr_image_key:
        return {
            "full_name": collector.full_name,
            "upi_id": profile.upi_id if profile else None,
            "phone": profile.phone if profile else None,
            "qr_image_url": None,
            "has_qr": False,
            "message": f"{collector.full_name} is your assigned collector, but has not uploaded a payment QR code yet.",
        }

    qr_image_url = await run_in_threadpool(get_signed_url, profile.qr_image_key, 300)
    return {
        "full_name": collector.full_name,
        "upi_id": profile.upi_id,
        "phone": profile.phone,
        "qr_image_url": qr_image_url,
        "has_qr": True,
    }



@router.get("/my-payments")
async def my_payments(
    current_user: User = Depends(get_current_giver),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Payment, User.full_name)
            .join(User, Payment.collector_id == User.id)
            .where(Payment.giver_id == current_user.id)
            .order_by(Payment.submitted_at.desc(), Payment.id.desc())
        )
    ).all()
    payments = []
    for payment, collector_name in rows:
        payments.append(
            {
                "id": payment.id,
                "amount": payment.amount,
                "transaction_ref": payment.transaction_ref,
                "status": payment.status,
                "collector_full_name": collector_name,
                "submitted_at": payment.submitted_at,
                "verified_at": payment.verified_at,
                "notes": payment.notes,
            }
        )
    return payments


@router.post("/submit-payment")
async def submit_payment(
    amount: Decimal = Form(...),
    transaction_ref: str = Form(..., min_length=1, max_length=100),
    screenshot: UploadFile = File(...),
    current_user: User = Depends(get_current_giver),
    db: AsyncSession = Depends(get_db),
):
    try:
        amount = amount.quantize(Decimal("0.01"))
    except (AttributeError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail="Amount must be a valid number") from exc
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than zero")

    # strip copy-paste whitespace so " 139709650010 " and "139709650010" are the same value
    transaction_ref = transaction_ref.strip()
    if not is_valid_transaction_ref(transaction_ref):
        raise HTTPException(
            status_code=400,
            detail="Enter a valid 12-digit UTR number or a PhonePe Transaction ID starting with T (e.g. 139709650010 or T2609110049222606913740)",
        )
    if not screenshot.content_type or not screenshot.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="screenshot must be an image file")

    existing_payment = await db.scalar(
        select(Payment).where(Payment.transaction_ref == transaction_ref)
    )
    if existing_payment:
        raise HTTPException(status_code=409, detail="Transaction reference has already been submitted")

    _, collector = await find_assigned_collector(current_user, db)
    screenshot_bytes = await screenshot.read()
    if not screenshot_bytes:
        raise HTTPException(status_code=422, detail="screenshot cannot be empty")
    if len(screenshot_bytes) > MAX_SCREENSHOT_SIZE:
        raise HTTPException(status_code=413, detail="screenshot must be 10 MB or smaller")

    key = f"screenshots/{current_user.id}-{transaction_ref}.jpg"
    try:
        await run_in_threadpool(upload_file, screenshot_bytes, key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to upload payment screenshot") from exc

    db.add(
        Payment(
            giver_id=current_user.id,
            collector_id=collector.id,
            amount=amount,
            transaction_ref=transaction_ref,
            screenshot_key=key,
            status="pending",
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Transaction reference has already been submitted") from exc

    return {
        "message": "Payment submitted for verification",
        "transaction_ref": transaction_ref,
        "status": "pending",
    }
