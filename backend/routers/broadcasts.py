from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import Broadcast, User


router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.get("")
async def my_broadcasts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if current_user.role != "admin":
        # admins see every broadcast; students only see ones matching their role (or "all")
        filters.append(
            or_(
                Broadcast.filter_role.is_(None),
                Broadcast.filter_role == "all",
                Broadcast.filter_role == current_user.role,
            )
        )
    if current_user.year is not None:
        # filter_year None = all years
        filters.append(or_(Broadcast.filter_year.is_(None), Broadcast.filter_year == current_user.year))
    if current_user.branch is not None:
        filters.append(or_(Broadcast.filter_branch.is_(None), Broadcast.filter_branch == current_user.branch))
    else:
        # users without a branch (e.g. girls groups) must not receive branch-targeted broadcasts
        filters.append(Broadcast.filter_branch.is_(None))
    if current_user.gender is not None:
        filters.append(or_(Broadcast.filter_gender.is_(None), Broadcast.filter_gender == current_user.gender))

    query = select(Broadcast, User.full_name).join(User, Broadcast.sent_by == User.id)
    if filters:
        query = query.where(*filters)
    query = query.order_by(Broadcast.sent_at.desc(), Broadcast.id.desc()).limit(50)

    rows = (await db.execute(query)).all()
    return [
        {
            "id": broadcast.id,
            "message": broadcast.message,
            "sent_by": sender_name,
            "sent_at": broadcast.sent_at,
            "filter_role": broadcast.filter_role or "all",
            "filter_year": broadcast.filter_year,
            "filter_branch": broadcast.filter_branch,
            "filter_gender": broadcast.filter_gender,
        }
        for broadcast, sender_name in rows
    ]
