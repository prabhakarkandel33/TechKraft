import asyncio
import json
from typing import Optional

from app.models import (
    new_id,
    now_iso,
    serialize_skills,
    deserialize_skills,
    row_to_candidate,
    row_to_score,
)


# ── Candidate queries ───────────────────────────────────────

async def list_candidates(
    db,
    status: Optional[str] = None,
    role_applied: Optional[str] = None,
    skill: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    is_admin: bool = False,
) -> dict:

    # this is the correct way to do filtered pagination —
    # everything happens in SQL, not in Python after fetching all rows
    # the assignment has a bug snippet that does it the wrong way,
    # loading all candidates into memory then slicing in Python
    # that breaks at scale and gives wrong counts

    conditions = ["deleted_at IS NULL"]
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if role_applied:
        conditions.append("role_applied = ?")
        params.append(role_applied)

    if keyword:
        # LIKE on name or email — kept simple intentionally
        conditions.append("(name LIKE ? OR email LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    if skill:
        # skills is stored as a JSON string like '["Python","React"]'
        # json_each lets SQLite iterate over the array natively
        # without this we'd have to do a hacky LIKE '%Python%' which
        # would match "PythonAnywhere" too
        conditions.append(
        "EXISTS (SELECT 1 FROM json_each(skills) WHERE LOWER(value) LIKE LOWER(?))"
        )#added fuzzy search
        params.append(skill)

    where_clause = " AND ".join(conditions)

    # get total count first using same filters — needed for pagination metadata
    count_sql = f"SELECT COUNT(*) FROM candidates WHERE {where_clause}"
    async with db.execute(count_sql, params) as cursor:
        row = await cursor.fetchone()
        total = row[0]

    # now fetch the actual page — LIMIT and OFFSET live in SQL
    offset = (page - 1) * page_size
    data_sql = f"""
        SELECT * FROM candidates
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    async with db.execute(data_sql, [*params, page_size, offset]) as cursor:
        rows = await cursor.fetchall()

    candidates = [row_to_candidate(row, is_admin=is_admin) for row in rows]

    return {
        "data": candidates,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (offset + len(candidates)) < total,
    }


async def get_candidate_by_id(
    db,
    candidate_id: str,
    is_admin: bool = False,
) -> Optional[dict]:

    async with db.execute(
        "SELECT * FROM candidates WHERE id = ? AND deleted_at IS NULL",
        (candidate_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    return row_to_candidate(row, is_admin=is_admin)


async def get_candidate_detail(
    db,
    candidate_id: str,
    current_user_id: str,
    is_admin: bool = False,
) -> Optional[dict]:

    candidate = await get_candidate_by_id(db, candidate_id, is_admin=is_admin)
    if not candidate:
        return None

    # PDF requirement: reviewer sees only their own scores
    # admin sees everyone's scores
    if is_admin:
        scores_sql = """
            SELECT * FROM scores
            WHERE candidate_id = ?
            ORDER BY created_at DESC
        """
        scores_params = (candidate_id,)
    else:
        scores_sql = """
            SELECT * FROM scores
            WHERE candidate_id = ? AND reviewer_id = ?
            ORDER BY created_at DESC
        """
        scores_params = (candidate_id, current_user_id)

    async with db.execute(scores_sql, scores_params) as cursor:
        score_rows = await cursor.fetchall()

    candidate["scores"] = [row_to_score(r) for r in score_rows]
    candidate["summary"] = None  # populated separately via POST /summary

    return candidate


# ── Score mutations ─────────────────────────────────────────

async def create_score(
    db,
    candidate_id: str,
    category: str,
    score: int,
    reviewer_id: str,
    note: Optional[str] = None,
) -> dict:

    # make sure candidate exists and isn't deleted
    candidate = await get_candidate_by_id(db, candidate_id)
    if not candidate:
        return None

    score_id = new_id()
    created_at = now_iso()

    await db.execute(
        """
        INSERT INTO scores (id, candidate_id, category, score, reviewer_id, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (score_id, candidate_id, category, score, reviewer_id, note, created_at),
    )
    await db.commit()

    # also flip candidate status to 'reviewed' if it's still 'new'
    # small quality of life thing — once someone scores them they're no longer new
    await db.execute(
        "UPDATE candidates SET status = 'reviewed' WHERE id = ? AND status = 'new'",
        (candidate_id,),
    )
    await db.commit()

    return {
        "id": score_id,
        "candidate_id": candidate_id,
        "category": category,
        "score": score,
        "reviewer_id": reviewer_id,
        "note": note,
        "created_at": created_at,
    }


# ── Mock AI summary ─────────────────────────────────────────

async def generate_summary(db, candidate_id: str) -> Optional[dict]:

    candidate = await get_candidate_by_id(db, candidate_id)
    if not candidate:
        return None

    # simulating an async LLM call — in production this would be
    # an await to Bedrock or OpenAI, same pattern just different await
    # the 2 second delay is explicitly required by the PDF
    await asyncio.sleep(2)

    skills_str = ", ".join(candidate["skills"]) if candidate["skills"] else "not specified"

    summary = (
        f"{candidate['name']} applied for {candidate['role_applied']}. "
        f"Their listed skills include {skills_str}. "
        f"Current status: {candidate['status']}. "
        f"This summary was auto-generated as part of the review workflow."
    )

    return {
        "candidate_id": candidate_id,
        "summary": summary,
        "generated_at": now_iso(),
    }


# ── Admin mutations ─────────────────────────────────────────

async def update_internal_notes(
    db,
    candidate_id: str,
    notes: str,
) -> Optional[dict]:

    candidate = await get_candidate_by_id(db, candidate_id, is_admin=True)
    if not candidate:
        return None

    await db.execute(
        "UPDATE candidates SET internal_notes = ? WHERE id = ?",
        (notes, candidate_id),
    )
    await db.commit()

    candidate["internal_notes"] = notes
    return candidate


async def soft_delete_candidate(db, candidate_id: str) -> bool:
    # never hard delete — PDF is explicit about this
    # sets deleted_at timestamp, all queries filter deleted_at IS NULL
    candidate = await get_candidate_by_id(db, candidate_id)
    if not candidate:
        return False

    await db.execute(
        "UPDATE candidates SET deleted_at = ? WHERE id = ?",
        (now_iso(), candidate_id),
    )
    await db.commit()
    return True


# ── Seed helpers ────────────────────────────────────────────
# used by the seed script to populate fake candidates on first run

async def seed_candidates(db):
    fake_candidates = [
        {
            "name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "role_applied": "Full Stack Engineer",
            "status": "new",
            "skills": ["Python", "React", "FastAPI"],
        },
        {
            "name": "Priya Thapa",
            "email": "priya.thapa@example.com",
            "role_applied": "Backend Engineer",
            "status": "reviewed",
            "skills": ["Python", "Django", "PostgreSQL"],
        },
        {
            "name": "Rohan Karki",
            "email": "rohan.karki@example.com",
            "role_applied": "Full Stack Engineer",
            "status": "hired",
            "skills": ["React", "Node.js", "AWS"],
        },
        {
            "name": "Sita Rai",
            "email": "sita.rai@example.com",
            "role_applied": "Data Engineer",
            "status": "new",
            "skills": ["Python", "Spark", "Airflow"],
        },
        {
            "name": "Bikash Adhikari",
            "email": "bikash.adhikari@example.com",
            "role_applied": "DevOps Engineer",
            "status": "rejected",
            "skills": ["Docker", "Terraform", "AWS"],
        },
        {
            "name": "Anita Gurung",
            "email": "anita.gurung@example.com",
            "role_applied": "Full Stack Engineer",
            "status": "new",
            "skills": ["Vue.js", "FastAPI", "DynamoDB"],
        },
        {
            "name": "Dipesh Maharjan",
            "email": "dipesh.maharjan@example.com",
            "role_applied": "Backend Engineer",
            "status": "reviewed",
            "skills": ["Go", "PostgreSQL", "Redis"],
        },
        {
            "name": "Kamala Shrestha",
            "email": "kamala.shrestha@example.com",
            "role_applied": "ML Engineer",
            "status": "new",
            "skills": ["Python", "PyTorch", "LangChain"],
        },
        {
            "name": "Nabin Bhandari",
            "email": "nabin.bhandari@example.com",
            "role_applied": "Full Stack Engineer",
            "status": "new",
            "skills": ["React", "FastAPI", "Pinecone"],
        },
        {
            "name": "Sunita Lama",
            "email": "sunita.lama@example.com",
            "role_applied": "Frontend Engineer",
            "status": "reviewed",
            "skills": ["React", "TypeScript", "Tailwind"],
        },
        {
            "name": "Kiran Pandey",
            "email": "kiran.pandey@example.com",
            "role_applied": "DevOps Engineer",
            "status": "new",
            "skills": ["Kubernetes", "Docker", "GitHub Actions"],
        },
        {
            "name": "Mina Tamang",
            "email": "mina.tamang@example.com",
            "role_applied": "Data Engineer",
            "status": "hired",
            "skills": ["Python", "dbt", "Snowflake"],
        },
    ]

    for c in fake_candidates:
        # skip if already seeded — email is unique so this won't duplicate
        async with db.execute(
            "SELECT id FROM candidates WHERE email = ?", (c["email"],)
        ) as cursor:
            exists = await cursor.fetchone()

        if not exists:
            await db.execute(
                """
                INSERT INTO candidates
                (id, name, email, role_applied, status, skills, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(),
                    c["name"],
                    c["email"],
                    c["role_applied"],
                    c["status"],
                    serialize_skills(c["skills"]),
                    now_iso(),
                ),
            )

    await db.commit()

async def seed_admin(db):
    from app.auth import hash_password

    async with db.execute(
        "SELECT id FROM users WHERE email = ?", ("admin@techkraft.com",)
    ) as cursor:
        exists = await cursor.fetchone()

    if not exists:
        await db.execute(
            """
            INSERT INTO users (id, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                new_id(),
                "admin@techkraft.com",
                hash_password("admin1234"),
                "admin",
                now_iso(),
            ),
        )
        await db.commit()