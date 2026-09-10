from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import Broadcast, CollectorGroup, CollectorProfile, Payment, User
from routers.auth import send_brevo_email
from storage import get_signed_url


router = APIRouter(prefix="/admin", tags=["admin"])


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


class BroadcastRequest(BaseModel):
    filter_year: int | None = Field(default=None, ge=1, le=4)
    filter_branch: Literal["IT", "ECE"] | None = None
    filter_gender: Literal["M", "F"] | None = None
    filter_role: Literal["all", "collector", "giver"] = "all"
    message: str = Field(min_length=1)


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    all_payments = (await db.scalars(select(Payment))).all()
    all_collectors = (await db.scalars(select(User).where(User.role == "collector"))).all()
    all_givers = (await db.scalars(select(User).where(User.role == "giver"))).all()
    active_profiles = (await db.scalars(select(CollectorProfile).where(CollectorProfile.qr_image_key.isnot(None)))).all()

    total_collected = sum(p.amount for p in all_payments if p.status == "verified")
    total_pending = sum(p.amount for p in all_payments if p.status == "pending")

    return {
        "total_collected": float(total_collected),
        "total_pending": float(total_pending),
        "verified_count": len([p for p in all_payments if p.status == "verified"]),
        "pending_count": len([p for p in all_payments if p.status == "pending"]),
        "rejected_count": len([p for p in all_payments if p.status == "rejected"]),
        "total_collectors": len(all_collectors),
        "active_collectors": len(active_profiles),
        "total_givers": len(all_givers),
    }


@router.get("/payments")
async def list_payments(
    year: int | None = Query(default=None, ge=1, le=4),
    branch: Literal["IT", "ECE"] | None = None,
    gender: Literal["M", "F"] | None = None,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    giver = User.__table__.alias("giver")
    collector = User.__table__.alias("collector")
    query = (
        select(
            Payment,
            giver.c.full_name,
            giver.c.roll_no,
            collector.c.full_name,
            collector.c.roll_no,
            CollectorGroup.year,
            CollectorGroup.branch,
            CollectorGroup.gender,
        )
        .join(giver, Payment.giver_id == giver.c.id)
        .join(collector, Payment.collector_id == collector.c.id)
        .outerjoin(CollectorProfile, CollectorProfile.user_id == Payment.collector_id)
        .outerjoin(CollectorGroup, CollectorGroup.id == CollectorProfile.collector_group_id)
        .order_by(Payment.submitted_at.desc(), Payment.id.desc())
    )
    if year is not None:
        query = query.where(CollectorGroup.year == year)
    if branch is not None:
        query = query.where(CollectorGroup.branch == branch)
    if gender is not None:
        query = query.where(CollectorGroup.gender == gender)

    rows = (await db.execute(query)).all()
    payments = []
    for payment, giver_name, giver_roll_no, collector_name, collector_roll_no, group_year, group_branch, group_gender in rows:
        screenshot_url = await run_in_threadpool(get_signed_url, payment.screenshot_key, 300)
        payments.append(
            {
                "id": payment.id,
                "amount": payment.amount,
                "transaction_ref": payment.transaction_ref,
                "status": payment.status,
                "giver_full_name": giver_name,
                "giver_roll_no": giver_roll_no,
                "collector_full_name": collector_name,
                "collector_roll_no": collector_roll_no,
                "year": group_year,
                "branch": group_branch,
                "gender": group_gender,
                "screenshot_url": screenshot_url,
                "submitted_at": payment.submitted_at,
                "verified_at": payment.verified_at,
                "notes": payment.notes,
            }
        )
    return payments


@router.post("/broadcast")
async def create_broadcast(
    request: BroadcastRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    broadcast = Broadcast(
        sent_by=current_user.id,
        filter_year=request.filter_year,
        filter_branch=request.filter_branch,
        filter_gender=request.filter_gender,
        filter_role=request.filter_role,
        message=request.message,
    )
    db.add(broadcast)
    await db.commit()

    filters = []
    if request.filter_year is not None:
        filters.append(User.year == request.filter_year)
    if request.filter_branch is not None:
        filters.append(User.branch == request.filter_branch)
    if request.filter_gender is not None:
        filters.append(User.gender == request.filter_gender)
    if request.filter_role != "all":
        filters.append(User.role == request.filter_role)

    recipients = (await db.scalars(select(User).where(*filters).order_by(User.id))).all()
    sent_count = 0
    for recipient in recipients:
        try:
            await send_brevo_email(
                recipient.email,
                "Chanda Tracker broadcast",
                request.message,
            )
            sent_count += 1
        except Exception as exc:
            print(f"[BROADCAST LOG] Email to {recipient.email} not sent: {exc}")

    return {"message": "Broadcast created and sent", "recipient_count": len(recipients), "emails_sent": sent_count}

