"""Integration tests for conversation and chat API endpoints.

These tests hit the HTTP endpoints and exercise the full stack:
routing -> service -> agent -> database.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient


async def _create_conversation(client: AsyncClient) -> dict:
    resp = await client.post("/api/conversations")
    assert resp.status_code == 201
    return resp.json()


async def _upload_sample_document(client: AsyncClient) -> dict:
    """Upload a sample markdown document to populate the vector store."""
    sample = Path(__file__).parent / "fixtures" / "sample.md"
    with open(sample, "rb") as f:
        resp = await client.post(
            "/api/documents",
            files={"file": ("sample.md", f, "text/markdown")},
        )
    assert resp.status_code == 201
    return resp.json()


async def test_create_conversation(client: AsyncClient) -> None:
    data = await _create_conversation(client)
    assert "id" in data
    assert data["title"] is None
    assert "created_at" in data
    assert "updated_at" in data


async def test_list_conversations_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json()["conversations"] == []


async def test_list_conversations_ordered_by_updated_at(
    client: AsyncClient,
) -> None:
    conv1 = await _create_conversation(client)
    conv2 = await _create_conversation(client)

    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    conversations = resp.json()["conversations"]
    assert len(conversations) >= 2
    assert conversations[0]["id"] == conv2["id"]
    assert conversations[1]["id"] == conv1["id"]


async def test_get_conversation_with_messages(client: AsyncClient) -> None:
    conv = await _create_conversation(client)

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == conv["id"]
    assert data["messages"] == []


async def test_get_conversation_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/conversations/nonexistent-id")
    assert resp.status_code == 404


async def test_delete_conversation(client: AsyncClient) -> None:
    conv = await _create_conversation(client)

    resp = await client.delete(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 404


async def test_delete_conversation_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/conversations/nonexistent-id")
    assert resp.status_code == 404


async def test_send_message_with_documents(client: AsyncClient) -> None:
    """When documents exist, the agent should return a response with sources."""
    await _upload_sample_document(client)
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "What is in the sample document?"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["content"]
    assert data["sources"] is not None
    assert len(data["sources"]) > 0
    assert "document_id" in data["sources"][0]
    assert "filename" in data["sources"][0]


async def test_send_message_empty_db_returns_no_docs(
    client: AsyncClient,
) -> None:
    """With no documents uploaded, agent should indicate no relevant docs."""
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "What is the meaning of life?"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["sources"] == []


async def test_send_message_empty_content_returns_422(
    client: AsyncClient,
) -> None:
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": ""},
    )
    assert resp.status_code == 422


async def test_send_message_nonexistent_conversation(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/conversations/nonexistent-id/messages",
        json={"content": "Hello"},
    )
    assert resp.status_code == 404


async def test_conversation_title_auto_generated(
    client: AsyncClient,
) -> None:
    conv = await _create_conversation(client)
    assert conv["title"] is None

    await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "What is the capital of France?"},
    )

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "What is the capital of France?"


async def test_messages_ordered_by_created_at(client: AsyncClient) -> None:
    conv = await _create_conversation(client)

    await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "First question"},
    )
    await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Second question"},
    )

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 200
    messages = resp.json()["messages"]

    # Should have 4 messages: user, assistant, user, assistant
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "First question"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "Second question"
    assert messages[3]["role"] == "assistant"


async def test_delete_conversation_cascades_messages(
    client: AsyncClient,
) -> None:
    conv = await _create_conversation(client)
    await client.post(
        f"/api/conversations/{conv['id']}/messages",
        json={"content": "Hello"},
    )

    resp = await client.delete(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 404
