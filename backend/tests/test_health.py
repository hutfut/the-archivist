import logging
import uuid

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_response_includes_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    uuid.UUID(request_id)


async def test_request_id_in_log_records(
    client: AsyncClient,
    caplog: "pytest.LogCaptureFixture",  # noqa: F821
) -> None:
    """Endpoints that log should have the request_id attribute on their records."""
    with caplog.at_level(logging.INFO):
        await client.post("/api/conversations")

    matching = [r for r in caplog.records if getattr(r, "request_id", "")]
    assert len(matching) > 0
    for record in matching:
        uuid.UUID(record.request_id)  # type: ignore[attr-defined]
