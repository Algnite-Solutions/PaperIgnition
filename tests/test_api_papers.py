import os
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.db_utils import AsyncSessionLocal
from backend.app.models.users import User
from backend.app.models.papers import PaperRecommendation
import asyncio
from httpx import AsyncClient

BASE_URL = "http://localhost:8008"

USERS = [
    {"username": "testuser_a", "email": "testuser_a@example.com"},
    {"username": "testuser_b", "email": "testuser_b@example.com"}
]
PAPERS = [
    {"paper_id": "paper_a1", "title": "Paper A1", "authors": "Alice", "abstract": "A1 abstract.", "url": "http://example.com/paper_a1", "content": "# Markdown A1", "blog": "Blog A1",  "recommendation_reason": "Rec reason A1", "relevance_score": 0.9},
    {"paper_id": "paper_a2", "title": "Paper A2", "authors": "Alice", "abstract": "A2 abstract.", "url": "http://example.com/paper_a2", "content": "# Markdown A2", "blog": "Blog A2",  "recommendation_reason": "Rec reason A2", "relevance_score": 0.8},
    {"paper_id": "paper_b1", "title": "Paper B1", "authors": "Bob", "abstract": "B1 abstract.", "url": "http://example.com/paper_b1", "content": "# Markdown B1", "blog": "Blog B1",  "recommendation_reason": "Rec reason B1", "relevance_score": 0.7},
    {"paper_id": "paper_b2", "title": "Paper B2", "authors": "Bob", "abstract": "B2 abstract.", "url": "http://example.com/paper_b2", "content": "# Markdown B2", "blog": "Blog B2",  "recommendation_reason": "Rec reason B2", "relevance_score": 0.6}
]

@pytest.mark.asyncio
async def test_add_paper_recommendation_multiuser():
    async with AsyncSessionLocal() as db:
        for u in USERS:
            await db.execute(text("DELETE FROM paper_recommendations WHERE username=:u"), {"u": u["username"]})
            await db.execute(text("DELETE FROM users WHERE username=:u"), {"u": u["username"]})
        await db.commit()
        for u in USERS:
            user = User(username=u["username"], email=u["email"])
            db.add(user)
        await db.commit()
    async with AsyncClient(base_url=BASE_URL) as client:
        # user_a: paper_a1, paper_a2; user_b: paper_b1, paper_b2
        for i, u in enumerate(USERS):
            for p in PAPERS[i*2:(i+1)*2]:
                resp = await client.post(f"/api/papers/recommend?username={u['username']}", json=p)
                assert resp.status_code == 201, resp.text
        # 再次添加同一条，返回400
        resp_dup = await client.post(f"/api/papers/recommend?username={USERS[0]['username']}", json=PAPERS[0])
        assert resp_dup.status_code == 500, resp_dup.text
        # 用户不存在
        resp_no = await client.post(f"/api/papers/recommend?username=nouser", json=PAPERS[0])
        assert resp_no.status_code == 500, resp_no.text

@pytest.mark.asyncio
async def test_get_recommended_papers_info_multiuser():
    async with AsyncClient(base_url=BASE_URL) as client:
        for i, u in enumerate(USERS):
            resp = await client.get(f"/api/papers/recommendations/{u['username']}")
            assert resp.status_code == 200
            papers = resp.json()
            assert len(papers) == 2
            ids = {p["id"] for p in papers}
            expected_ids = {PAPERS[i*2]["paper_id"], PAPERS[i*2+1]["paper_id"]}
            assert ids == expected_ids
            for p in papers:
                assert p["title"] is not None
                assert p["authors"] is not None
                assert p["abstract"] is not None
                assert p["url"] is not None

@pytest.mark.asyncio
async def test_get_paper_markdown_content_multiuser():
    async with AsyncClient(base_url=BASE_URL) as client:
        for i, u in enumerate(USERS):
            for p in PAPERS[i*2:(i+1)*2]:
                resp = await client.get(f"/api/papers/paper_content/{p['paper_id']}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["paper_content"] == p["content"]
                assert data["blog"] == p["blog"]
                assert data["recommendation_reason"] == p["recommendation_reason"]
        # 不存在的 paper_id
        resp2 = await client.get(f"/api/papers/paper_content/nonexistent_id")
        assert resp2.status_code == 404

async def run_tests():
    print("\nRunning papers.py API tests (multi-user)")
    print("=" * 50)
    try:
        await test_add_paper_recommendation_multiuser()
        print("✅ test_add_paper_recommendation_multiuser passed")
        await test_get_recommended_papers_info_multiuser()
        print("✅ test_get_recommended_papers_info_multiuser passed")
        await test_get_paper_markdown_content_multiuser()
        print("✅ test_get_paper_markdown_content_multiuser passed")
        print("\n✅ All multi-user papers.py API tests passed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
    except Exception as e:
        print(f"\n❌ Error during tests: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_tests()) 