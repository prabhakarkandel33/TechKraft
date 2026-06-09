import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import init_db, DB_PATH
from app.services.candidate_service import seed_candidates

# use a separate test DB so we don't trash the dev one
TEST_DB = "test_candidates.db"


@pytest_asyncio.fixture(autouse=True)
async def setup_db(monkeypatch):
    # point everything at the test DB for this run
    monkeypatch.setenv("DB_PATH", TEST_DB)

    import app.models as m
    m.DB_PATH = TEST_DB

    import app.main as main_module
    main_module.DB_PATH = TEST_DB

    async with aiosqlite.connect(TEST_DB) as db:
        db.row_factory = aiosqlite.Row
        await init_db()
        await seed_candidates(db)

    yield

    # clean up after each test
    import os
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c


async def get_token(client, email="test@example.com", password="test1234"):
    await client.post("/auth/register", json={
        "email": email,
        "password": password,
    })
    res = await client.post("/auth/login", json={
        "email": email,
        "password": password,
    })
    return res.json()["access_token"]


#create a candidate score and verify response

@pytest.mark.asyncio
async def test_submit_score(client):
    token = await get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # grab first candidate from list
    res = await client.get("/candidates", headers=headers)
    assert res.status_code == 200
    candidates = res.json()["data"]
    assert len(candidates) > 0

    candidate_id = candidates[0]["id"]

    # submit a score
    score_res = await client.post(
        f"/candidates/{candidate_id}/scores",
        headers=headers,
        json={"category": "technical", "score": 4, "note": "solid python skills"},
    )
    assert score_res.status_code == 201
    data = score_res.json()
    assert data["score"] == 4
    assert data["category"] == "technical"
    assert data["candidate_id"] == candidate_id


# reviewer cannot see another reviewer's scores

@pytest.mark.asyncio
async def test_reviewer_isolation(client):
    # reviewer A submits a score
    token_a = await get_token(client, "reviewer_a@test.com", "pass1234")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = await client.get("/candidates", headers=headers_a)
    candidate_id = res.json()["data"][0]["id"]

    await client.post(
        f"/candidates/{candidate_id}/scores",
        headers=headers_a,
        json={"category": "communication", "score": 3},
    )

    # reviewer B logs in — should NOT see reviewer A's score
    token_b = await get_token(client, "reviewer_b@test.com", "pass1234")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    detail_res = await client.get(
        f"/candidates/{candidate_id}",
        headers=headers_b,
    )
    assert detail_res.status_code == 200
    scores = detail_res.json()["scores"]

    # reviewer B has no scores so list must be empty
    assert scores == []


#unauthenticated request is rejected 

@pytest.mark.asyncio
async def test_unauth_request_rejected(client):
    res = await client.get("/candidates")
    assert res.status_code == 403


#soft delete test

@pytest.mark.asyncio
async def test_soft_delete_preserves_row(client):
    from app.auth import hash_password
    from app.models import new_id, now_iso

    # seed an admin
    async with aiosqlite.connect(TEST_DB) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO users (id, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id(), "admin2@test.com", hash_password("admin1234"), "admin", now_iso()),
        )
        await db.commit()

    admin_res = await client.post("/auth/login", json={
        "email": "admin2@test.com",
        "password": "admin1234",
    })
    admin_token = admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # get a candidate
    res = await client.get("/candidates", headers=admin_headers)
    candidate_id = res.json()["data"][0]["id"]

    # delete the candidate
    delete_res = await client.delete(f"/candidates/{candidate_id}", headers=admin_headers)
    assert delete_res.status_code == 204

    # candidate must not appear in list anymore
    list_res = await client.get("/candidates", headers=admin_headers)
    ids_in_list = [c["id"] for c in list_res.json()["data"]]
    assert candidate_id not in ids_in_list, "deleted candidate still appears in list"

    # but row must still exist in DB with deleted_at set
    async with aiosqlite.connect(TEST_DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT deleted_at FROM candidates WHERE id = ?", (candidate_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None, "candidate row was hard deleted"
            assert row["deleted_at"] is not None, "deleted_at was not set — soft delete failed"
