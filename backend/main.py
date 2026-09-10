from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import check_database_connection, seed_collector_groups
from storage import UPLOADS_DIR
from routers.auth import router as auth_router
from routers.collector import router as collector_router
from routers.giver import router as giver_router
from routers.admin import router as admin_router
from routers.broadcasts import router as broadcasts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_database_connection()
    await seed_collector_groups()
    yield


app = FastAPI(title="Chanda Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # API uses Bearer tokens (no cookies), so credentials are not required
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(collector_router)
app.include_router(giver_router)
app.include_router(admin_router)
app.include_router(broadcasts_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

