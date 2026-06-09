import aiosqlite
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "candidates.db")


#helpers
def new_id() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def serialize_skills(skills: list[str]) -> str:
    return json.dumps(skills)

def deserialize_skills(skills_str: str) -> list[str]:
    try:
        return json.loads(skills_str)
    except Exception:
        return []


#row serializers
def row_to_candidate(row, is_admin: bool = False) -> dict:
    data = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role_applied": row["role_applied"],
        "status": row["status"],
        "skills": deserialize_skills(row["skills"]),
        "created_at": row["created_at"],
    }
    if is_admin:
        data["internal_notes"] = row["internal_notes"]
    return data

def row_to_score(row) -> dict:
    return {
        "id": row["id"],
        "candidate_id": row["candidate_id"],
        "category": row["category"],
        "score": row["score"],
        "reviewer_id": row["reviewer_id"],
        "note": row["note"],
        "created_at": row["created_at"],
    }

def row_to_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id             TEXT PRIMARY KEY,
                name           TEXT NOT NULL,
                email          TEXT UNIQUE NOT NULL,
                role_applied   TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'new',
                skills         TEXT NOT NULL DEFAULT '[]',
                internal_notes TEXT,
                created_at     TEXT NOT NULL,
                deleted_at     TEXT
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id           TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                category     TEXT NOT NULL,
                score        INTEGER NOT NULL CHECK(score >= 1 AND score <= 5),
                reviewer_id  TEXT NOT NULL,
                note         TEXT,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id)
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         TEXT PRIMARY KEY,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                role       TEXT NOT NULL DEFAULT 'reviewer',
                created_at TEXT NOT NULL
            );
        """)
        # Indexes so filters hit index not full table scan
        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);",
            "CREATE INDEX IF NOT EXISTS idx_candidates_role ON candidates(role_applied);",
            "CREATE INDEX IF NOT EXISTS idx_candidates_deleted ON candidates(deleted_at);",
            "CREATE INDEX IF NOT EXISTS idx_scores_candidate ON scores(candidate_id);",
            "CREATE INDEX IF NOT EXISTS idx_scores_reviewer ON scores(reviewer_id);",
        ]:
            await db.execute(sql)
        await db.commit()