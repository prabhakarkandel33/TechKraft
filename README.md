# TechKraft Candidate Scoring Dashboard

Internal tool for TechKraft's recruitment team. Reviewers score candidates
across categories and trigger AI-generated summaries. Admins get full
visibility including internal notes and all reviewer scores.

Built with FastAPI + SQLite on the backend, React + Vite on the frontend,
containerized with Docker Compose.

---

## Quick Start

### Prerequisites
- Docker Desktop
- Node.js 20+ (for local frontend dev only)
- Python 3.11+ (for running tests locally)

### Run with Docker Compose

After cloning the repo

cp .env.example .env
# open .env and set a real SECRET_KEY before running

docker-compose up --build
```



### Default credentials (seeded automatically on first run)

I have already seeded the following admin upon the first run i.e when containerr is built:

| Email | Password |
|-------|----------|
| admin@techkraft.com | admin1234 |




---

## Running Tests

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
pytest tests/test_api.py -v
```

Tests use a separate `test_candidates.db` that gets created and destroyed
per run — your dev database is never touched.

---

## Example API Calls

### Register a reviewer
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"reviewer@test.com\", \"password\": \"test1234\"}"
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"admin@techkraft.com\", \"password\": \"admin1234\"}"
```

### List candidates with filters
```bash
curl "http://localhost:8000/candidates?skill=Python&status=new&page=1&page_size=5" \
  -H "Authorization: Bearer TOKEN"
```

### Submit a score
```bash
curl -X POST http://localhost:8000/candidates/CANDIDATE_ID/scores \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"category\": \"technical\", \"score\": 4, \"note\": \"strong async patterns\"}"
```



---

## Architecture Decision Records

### ADR 1 — SQLite over DynamoDB

**Context:** For the assingment I was asked to use DynamoDB-Style modelling but required
a fully runnable local setup. Setting it up would demonstrate nothing beyond
configuration ability

**Decision:** SQLite with aiosqlite was used for async access, it tried to mirror schema
with DynamoDB lookalike, candidates and scores as separate entity, indexes
on status for fast retrieval.

**Trade-off:** SQLite is only practical for this usecase as it doesn't scale well, it is
very hard to handle thousands of concurrent requests.

---

### ADR 2 — Service layer separation

**Context:** At first iteration i had SQL queries on route handlers, that made the code
hard to read and testing difficult, as you had to make http request to test
any data logic.

**Decision:** Now all database queries live in candidate_service.py, routers 
only handle
HTTP.

**Trade-off:** Not much totally worth it.Complete separation of concerns is good design.

---

### ADR 3 — JWT in Authorization header, role embedded in token

**Context:** The frontend is a React SPA talking to a separate FastAPI
backend. Needed a stateless auth mechanism that works across origins
and doesn't require server-side session storage.

**Decision:** JWT Bearer tokens stored in localStorage. Role is embedded
in the token payload so any route can check permissions without a DB
lookup. Registration hardcodes role to reviewer — the field isn't
even present in the registration schema so there's no code path where
a client could inject a different role.

**Trade-off:** Although technically vulnerable to XSS the risk is acceptable
in case of an internal tool.


---

## Debugging — The Pagination Bug

The provided snippet:

```python
def search_candidates(status, keyword, page, page_size):
    all_candidates = db.execute("SELECT * FROM candidates").fetchall()
    filtered = [c for c in all_candidates if c["status"] == status]
    offset = (page - 1) * page_size
    return filtered[offset : offset + page_size]
```

**Issue 1 — Full table scan on every request.**
`SELECT * FROM candidates` Loading of every row into Python memory regardless of how they match filters,it is highly inefficient as at scale a lot of db entries will get converted
to python dictionary which is total waste(on every request). Python is especially
not made for things like this.

**Issue 2 — Pagination counts are wrong.**
The offset is calculated against the already-filtered Python list, not
the total dataset. If there are 10,000 candidates but only 50 match
`status=new`, page 2 with page_size=20 would try to slice
`filtered[20:40]` — which works — but the caller has no way to know
there are only 50 total matches, so the frontend can't render correct
pagination controls. The `total` count returned would reflect the
filtered list length, not the true count.

**The fix — push everything into SQL:**

```python
async def search_candidates(db, status, keyword, page, page_size):
    conditions = ["deleted_at IS NULL"]
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if keyword:
        conditions.append("(name LIKE ? OR email LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    where = " AND ".join(conditions)

    # accurate total with same filters
    async with db.execute(
        f"SELECT COUNT(*) FROM candidates WHERE {where}", params
    ) as cursor:
        total = (await cursor.fetchone())[0]

    # actual page — LIMIT and OFFSET in SQL
    offset = (page - 1) * page_size
    async with db.execute(
        f"SELECT * FROM candidates WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        [*params, page_size, offset]
    ) as cursor:
        rows = await cursor.fetchall()

    return rows, total
```

Two queries, both use indexes, nothing loaded into Python memory
unnecessarily.

---


## Learning Reflection

Began with writing the authorization checks within each route function directly until realizing that `Depends()` allows one to build off another, so `get_current_admin` simply depends on `get_current_user`. This refactoring helped clean up the RBAC design compared to the initial version. If I had more time, I would work on an SSE streaming endpoint to update scores in real-time. Took a brief look at the `StreamingResponse` API but decided against implementing it to prevent a half-baked submission.
---

## What's Not Implemented

- `GET /candidates/{id}/stream` — SSE stretch goal. Acknowledged
  rather than attempted poorly. The mock summary endpoint demonstrates
  understanding of async external calls which is the same underlying
  pattern.

---

## Test Coverage

4 tests covering core requirements and RBAC enforcement:

| Test | What it verifies |
|------|-----------------|
| `test_submit_score` | Score submission and response shape validation |
| `test_reviewer_isolation` | Reviewer B cannot see reviewer A's scores |
| `test_unauth_request_rejected` | No token = 403 |
| `test_soft_delete_preserves_row` | Row exists in DB after delete with deleted_at set |

Due to timing constraints I didnot implement more ones the hard cap rules are verified however and others i manually checked reviewers are invited to do the same.