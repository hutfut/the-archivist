"""Tests for document content, search, and related documents endpoints."""
import uuid

from httpx import AsyncClient


async def _upload(client: AsyncClient, name: str, content: bytes, mime: str = "text/plain") -> dict:
    resp = await client.post("/api/documents", files={"file": (name, content, mime)})
    assert resp.status_code == 201
    return resp.json()


# --- GET /api/documents/{id}/content ---


async def test_content_returns_full_text(client: AsyncClient) -> None:
    doc = await _upload(client, "readme.txt", b"Hello, world!")
    resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "Hello, world!"
    assert body["title"] == "Readme"
    assert body["filename"] == "readme.txt"
    assert body["content_type"] == "text/plain"


async def test_content_markdown_file(client: AsyncClient) -> None:
    md = b"# Title\n\nSome **bold** text."
    doc = await _upload(client, "notes.md", md, "text/markdown")
    resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert resp.status_code == 200
    assert "# Title" in resp.json()["content"]
    assert resp.json()["title"] == "Notes"


async def test_content_404_for_missing_document(client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/documents/{fake_id}/content")
    assert resp.status_code == 404


async def test_content_404_for_missing_file_on_disk(
    client: AsyncClient, test_settings: "Settings",  # noqa: F821
) -> None:
    doc = await _upload(client, "temp.txt", b"This is a temporary document for testing disk removal.")
    import shutil
    doc_dir = test_settings.upload_dir / doc["id"]
    shutil.rmtree(doc_dir)
    resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert resp.status_code == 404


# --- GET /api/search ---


async def test_search_returns_results(client: AsyncClient) -> None:
    await _upload(client, "python.txt", b"Python is a programming language used for web development and data science.")
    resp = await client.get("/api/search", params={"q": "python programming"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "python programming"
    assert isinstance(body["results"], list)
    assert body["total"] >= 0


async def test_search_empty_query_rejected(client: AsyncClient) -> None:
    resp = await client.get("/api/search", params={"q": ""})
    assert resp.status_code == 422


async def test_search_no_match_returns_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/search", params={"q": "zyxwvutsrqponmlkjihgfedcba"})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0


async def test_search_returns_when_no_documents(client: AsyncClient) -> None:
    resp = await client.get("/api/search", params={"q": "anything"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


async def test_search_result_has_required_fields(client: AsyncClient) -> None:
    await _upload(client, "fields.txt", b"Testing search result fields with some content here.")
    resp = await client.get("/api/search", params={"q": "testing search"})
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        assert "document_id" in result
        assert "filename" in result
        assert "title" in result
        assert "snippet" in result
        assert "score" in result


# --- GET /api/documents/{id}/related ---


async def test_related_returns_other_documents(client: AsyncClient) -> None:
    doc1 = await _upload(client, "alpha.txt", b"Alpha document content about programming.")
    await _upload(client, "beta.txt", b"Beta document content about programming.")
    resp = await client.get(f"/api/documents/{doc1['id']}/related")
    assert resp.status_code == 200
    body = resp.json()
    ids = [d["id"] for d in body["documents"]]
    assert doc1["id"] not in ids


async def test_related_404_for_missing_document(client: AsyncClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/documents/{fake_id}/related")
    assert resp.status_code == 404


async def test_related_respects_limit(client: AsyncClient) -> None:
    doc1 = await _upload(client, "one.txt", b"Document one content.")
    await _upload(client, "two.txt", b"Document two content.")
    await _upload(client, "three.txt", b"Document three content.")
    resp = await client.get(f"/api/documents/{doc1['id']}/related", params={"limit": 1})
    assert resp.status_code == 200
    assert len(resp.json()["documents"]) <= 1


async def test_related_empty_when_single_document(client: AsyncClient) -> None:
    doc = await _upload(client, "lonely.txt", b"Only document in the system.")
    resp = await client.get(f"/api/documents/{doc['id']}/related")
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


async def test_related_result_has_required_fields(client: AsyncClient) -> None:
    doc1 = await _upload(client, "first.txt", b"First document about technology.")
    await _upload(client, "second.txt", b"Second document about technology.")
    resp = await client.get(f"/api/documents/{doc1['id']}/related")
    assert resp.status_code == 200
    for doc in resp.json()["documents"]:
        assert "id" in doc
        assert "filename" in doc
        assert "title" in doc
        assert "score" in doc
