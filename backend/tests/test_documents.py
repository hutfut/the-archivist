import uuid

from httpx import AsyncClient


async def test_upload_document_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/documents",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "test.txt"
    assert body["content_type"] == "text/plain"
    assert body["file_size"] == 11
    assert body["chunk_count"] == 0
    assert "id" in body
    assert "created_at" in body


async def test_upload_returns_correct_metadata(client: AsyncClient) -> None:
    content = b"a" * 256
    response = await client.post(
        "/api/documents",
        files={"file": ("notes.md", content, "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.md"
    assert body["content_type"] == "text/markdown"
    assert body["file_size"] == 256
    assert body["chunk_count"] == 0


async def test_upload_stores_file_on_disk(
    client: AsyncClient, test_settings: "Settings"  # noqa: F821
) -> None:
    response = await client.post(
        "/api/documents",
        files={"file": ("disk.txt", b"persisted", "text/plain")},
    )
    doc_id = response.json()["id"]
    file_path = test_settings.upload_dir / doc_id / "disk.txt"
    assert file_path.exists()
    assert file_path.read_bytes() == b"persisted"


async def test_list_documents_empty(client: AsyncClient) -> None:
    response = await client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"documents": []}


async def test_list_documents_after_uploads(client: AsyncClient) -> None:
    await client.post(
        "/api/documents",
        files={"file": ("a.txt", b"aaa", "text/plain")},
    )
    await client.post(
        "/api/documents",
        files={"file": ("b.txt", b"bbb", "text/plain")},
    )

    response = await client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()["documents"]
    assert len(docs) == 2
    filenames = {d["filename"] for d in docs}
    assert filenames == {"a.txt", "b.txt"}


async def test_upload_empty_file_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_upload_unsupported_format_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/documents",
        files={"file": ("malware.exe", b"bad", "application/octet-stream")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert ".exe" in detail
    assert ".pdf" in detail


async def test_upload_pdf_accepted(client: AsyncClient) -> None:
    response = await client.post(
        "/api/documents",
        files={"file": ("doc.pdf", b"%PDF-fake", "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "doc.pdf"
