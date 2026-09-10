from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not set")

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)


engine = create_async_engine(
    database_url,
    connect_args={"statement_cache_size": 0},
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def check_database_connection() -> None:
    from sqlalchemy import text

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def seed_collector_groups() -> None:
    from sqlalchemy import select
    from models import CollectorGroup, Base

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        existing = (await db.scalars(select(CollectorGroup))).all()
        if existing:
            return

        groups = []
        for year in range(1, 5):
            # Boys: IT and ECE
            groups.append(CollectorGroup(year=year, branch="IT", gender="M"))
            groups.append(CollectorGroup(year=year, branch="ECE", gender="M"))
            # Girls: All branches combined per year
            groups.append(CollectorGroup(year=year, branch=None, gender="F"))

        db.add_all(groups)
        await db.commit()

