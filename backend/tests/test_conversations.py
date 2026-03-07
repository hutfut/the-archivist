"""Integration tests for conversation and chat API endpoints.

These tests hit the HTTP endpoints and exercise the full stack:
routing -> service -> agent -> database.
"""

import json
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

NONEXISTENT_UUID = str(uuid.uuid4())


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
    resp = await client.get(f"/api/conversations/{NONEXISTENT_UUID}")
    assert resp.status_code == 404


async def test_delete_conversation(client: AsyncClient) -> None:
    conv = await _create_conversation(client)

    resp = await client.delete(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/conversations/{conv['id']}")
    assert resp.status_code == 404


async def test_delete_conversation_not_found(client: AsyncClient) -> None:
    resp = await client.delete(f"/api/conversations/{NONEXISTENT_UUID}")
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
        f"/api/conversations/{NONEXISTENT_UUID}/messages",
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


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    """Parse an SSE response body into a list of (event_type, data) tuples."""
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    for line in body.splitlines():
        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: ") and current_event is not None:
            data = json.loads(line[len("data: "):])
            events.append((current_event, data))
            current_event = None
    return events


async def test_stream_message_event_sequence(client: AsyncClient) -> None:
    """SSE stream should emit message_start, content_delta(s), sources, message_end."""
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages/stream",
        json={"content": "Tell me something"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse_events(resp.text)
    event_types = [e[0] for e in events]

    assert event_types[0] == "message_start"
    assert event_types[-1] == "message_end"
    assert event_types[-2] == "sources"
    assert all(t == "content_delta" for t in event_types[1:-2])
    assert len(event_types) >= 4

    message_id = events[0][1]["message_id"]
    assert events[-1][1]["message_id"] == message_id

    full_content = "".join(e[1]["delta"] for e in events if e[0] == "content_delta")
    assert len(full_content) > 0


async def test_stream_message_with_documents(client: AsyncClient) -> None:
    """SSE stream should include source attributions when documents exist."""
    await _upload_sample_document(client)
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages/stream",
        json={"content": "What is in the sample?"},
    )
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    sources_events = [e for e in events if e[0] == "sources"]
    assert len(sources_events) == 1
    sources = sources_events[0][1]["sources"]
    assert len(sources) > 0
    assert "filename" in sources[0]


async def test_stream_message_persists(client: AsyncClient) -> None:
    """Messages sent via streaming should be persisted to the conversation."""
    conv = await _create_conversation(client)

    resp = await client.post(
        f"/api/conversations/{conv['id']}/messages/stream",
        json={"content": "Streaming question"},
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/conversations/{conv['id']}")
    messages = resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Streaming question"
    assert messages[1]["role"] == "assistant"


async def test_stream_message_nonexistent_conversation(
    client: AsyncClient,
) -> None:
    """Streaming to a nonexistent conversation should emit an error event."""
    resp = await client.post(
        f"/api/conversations/{NONEXISTENT_UUID}/messages/stream",
        json={"content": "Hello"},
    )
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    assert len(events) == 1
    assert events[0][0] == "error"
    assert "not found" in events[0][1]["detail"].lower()


async def test_conversation_history_truncated(client: AsyncClient) -> None:
    """get_conversation_history with max_messages should only return recent messages."""
    from app.db.session import get_session_factory
    from app.services.conversation_service import (
        add_message,
        get_conversation_history,
    )

    conv = await _create_conversation(client)
    session_factory = get_session_factory()

    async with session_factory() as session:
        for i in range(6):
            await add_message(conv["id"], "user", f"msg-{i}", session)

        history = await get_conversation_history(conv["id"], session, max_messages=4)

    assert len(history) == 4
    assert history[0]["content"] == "msg-2"
    assert history[-1]["content"] == "msg-5"


async def test_list_conversations_pagination(client: AsyncClient) -> None:
    for _ in range(3):
        await _create_conversation(client)

    resp = await client.get("/api/conversations", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["conversations"]) == 2

    resp = await client.get("/api/conversations", params={"limit": 2, "offset": 2})
    assert resp.status_code == 200
    assert len(resp.json()["conversations"]) == 1


async def test_send_message_invalid_uuid_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/conversations/not-a-uuid/messages",
        json={"content": "Hello"},
    )
    assert resp.status_code == 422


async def test_delete_document_invalid_uuid_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.delete("/api/documents/not-a-uuid")
    assert resp.status_code == 422
