from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import CollectorGroup, CollectorProfile, Payment, User
from storage import get_signed_url, upload_file


router = APIRouter(prefix="/collector", tags=["collector"])
MAX_QR_FILE_SIZE = 5 * 1024 * 1024


class PaymentVerificationRequest(BaseModel):
    status: Literal["verified", "rejected"]
    notes: str | None = Field(default=None, max_length=10000)


async def get_current_collector(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "collector":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collector access required")
    return current_user


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_collector),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(
        select(CollectorProfile).where(CollectorProfile.user_id == current_user.id)
    )
    qr_image_url = None
    if profile and profile.qr_image_key:
        qr_image_url = await run_in_threadpool(get_signed_url, profile.qr_image_key, 300)

    return {
        "upi_id": profile.upi_id if profile else "",
        "phone": profile.phone if profile else "",
        "qr_image_key": profile.qr_image_key if profile else None,
        "qr_image_url": qr_image_url,
        "year": current_user.year,
        "branch": current_user.branch,
        "gender": current_user.gender,
    }


@router.post("/profile")
async def upsert_profile(
    upi_id: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    qr_image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_collector),
    db: AsyncSession = Depends(get_db),
):
    if current_user.year is None or current_user.gender is None:
        raise HTTPException(status_code=400, detail="Collector profile is missing year or gender")

    target_branch = None if current_user.gender == "F" else current_user.branch
    if current_user.gender == "M" and target_branch is None:
        raise HTTPException(status_code=400, detail="Male collector profile is missing branch")

    group_filters = [
        CollectorGroup.year == current_user.year,
        CollectorGroup.gender == current_user.gender,
    ]
    if current_user.gender == "F":
        group_filters.append(CollectorGroup.branch.is_(None))
    else:
        group_filters.append(CollectorGroup.branch == target_branch)

    collector_group = await db.scalar(select(CollectorGroup).where(*group_filters))
    if not collector_group:
        collector_group = CollectorGroup(
            year=current_user.year,
            branch=target_branch,
            gender=current_user.gender,
        )
        db.add(collector_group)
        await db.flush()

    existing_profile = await db.scalar(
        select(CollectorProfile).where(CollectorProfile.user_id == current_user.id)
    )

    key = existing_profile.qr_image_key if existing_profile else None

    if qr_image and qr_image.filename:
        if qr_image.content_type and not qr_image.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="qr_image must be an image file")

        file_bytes = await qr_image.read()
        if not file_bytes:
            raise HTTPException(status_code=422, detail="qr_image cannot be empty")
        if len(file_bytes) > MAX_QR_FILE_SIZE:
            raise HTTPException(status_code=413, detail="qr_image must be 5 MB or smaller")

        key = f"qr-codes/{current_user.id}.jpg"
        try:
            await run_in_threadpool(upload_file, file_bytes, key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Unable to upload QR image") from exc
    elif not key:
        raise HTTPException(status_code=422, detail="Choose a QR image before saving your profile for the first time")

    if existing_profile:
        existing_profile.collector_group_id = collector_group.id
        # keep previously saved values when a field is not provided
        existing_profile.upi_id = upi_id if upi_id is not None else existing_profile.upi_id
        existing_profile.qr_image_key = key
        existing_profile.phone = phone if phone is not None else existing_profile.phone
        existing_profile.updated_at = datetime.now(timezone.utc)
    else:
        db.add(
            CollectorProfile(
                user_id=current_user.id,
                collector_group_id=collector_group.id,
                upi_id=upi_id,
                qr_image_key=key,
                phone=phone,
            )
        )

    await db.commit()
    qr_url = await run_in_threadpool(get_signed_url, key, 300)
    return {"message": "Collector profile saved", "qr_image_key": key, "qr_image_url": qr_url}



@router.get("/my-payments")
async def my_payments(
    current_user: User = Depends(get_current_collector),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Payment, User.full_name, User.roll_no)
            .join(User, Payment.giver_id == User.id)
            .where(Payment.collector_id == current_user.id)
            .order_by(Payment.submitted_at.desc(), Payment.id.desc())
        )
    ).all()
    payments = []
    for payment, giver_name, giver_roll_no in rows:
        screenshot_url = await run_in_threadpool(get_signed_url, payment.screenshot_key, 300)
        payments.append(
            {
                "id": payment.id,
                "amount": payment.amount,
                "transaction_ref": payment.transaction_ref,
                "status": payment.status,
                "giver_full_name": giver_name,
                "giver_roll_no": giver_roll_no,
                "screenshot_url": screenshot_url,
                "submitted_at": payment.submitted_at,
                "verified_at": payment.verified_at,
                "verified_by": payment.verified_by,
                "notes": payment.notes,
            }
        )
    return payments


@router.patch("/payments/{payment_id}/verify")
async def verify_payment(
    payment_id: int,
    request: PaymentVerificationRequest,
    current_user: User = Depends(get_current_collector),
    db: AsyncSession = Depends(get_db),
):
    payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.collector_id != current_user.id:
        raise HTTPException(status_code=403, detail="You cannot verify this payment")

    payment.status = request.status
    payment.verified_by = current_user.id
    payment.verified_at = datetime.now(timezone.utc)
    payment.notes = request.notes
    await db.commit()
    return {"message": "Payment status updated", "status": payment.status}
