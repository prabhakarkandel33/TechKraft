from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.models import init_db
from app.services.candidate_service import seed_candidates, seed_admin
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "candidates.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await init_db()
        await seed_candidates(db)
        await seed_admin(db)
    yield


app = FastAPI(
    title="TechKraft Candidate Scoring API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import candidates, auth as auth_router
app.include_router(auth_router.router)
app.include_router(candidates.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

@asynccontextmanager
async def lifespan(app:FastAPI):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await init_db()
        await seed_candidates(db)
        await seed_admin(db)
    yield