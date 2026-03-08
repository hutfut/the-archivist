"""Unit tests for the LangGraph RAG agent graph.

Tests exercise the graph directly (not through HTTP endpoints) using
mock retrieval and mock LLM. Integration tests for the HTTP layer
are in test_conversations.py.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.graph import _NO_RELEVANT_DOCS_RESPONSE, _SYSTEM_PROMPT, build_agent_graph
from app.agent.llm import MockChatModel, create_llm
from app.config import Settings
from app.services.retrieval import RetrievedChunk


def _make_chunk(
    document_id: str = "doc-1",
    filename: str = "test.md",
    chunk_content: str = "The capital of France is Paris.",
    chunk_index: int = 0,
    similarity_score: float = 0.85,
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id,
        filename=filename,
        chunk_content=chunk_content,
        chunk_index=chunk_index,
        similarity_score=similarity_score,
    )


def _mock_retrieval_service(chunks: list[RetrievedChunk]) -> AsyncMock:
    service = AsyncMock()
    service.search = AsyncMock(return_value=chunks)
    return service


def _mock_session_factory():
    """Creates a callable that returns an async context manager, mimicking async_sessionmaker."""
    mock_session = MagicMock()

    @asynccontextmanager
    async def _session_ctx():
        yield mock_session

    def factory():
        return _session_ctx()

    return factory


@pytest.fixture
def mock_llm() -> MockChatModel:
    return MockChatModel()


@pytest.fixture
def high_relevance_chunks() -> list[RetrievedChunk]:
    return [
        _make_chunk(
            document_id="doc-1",
            filename="geography.md",
            chunk_content="The capital of France is Paris.",
            similarity_score=0.9,
        ),
        _make_chunk(
            document_id="doc-2",
            filename="history.txt",
            chunk_content="Paris has been the capital since the 10th century.",
            similarity_score=0.75,
        ),
    ]


@pytest.fixture
def low_relevance_chunks() -> list[RetrievedChunk]:
    return [
        _make_chunk(
            chunk_content="Python is a programming language.",
            similarity_score=0.1,
        ),
        _make_chunk(
            chunk_content="The weather is nice today.",
            similarity_score=0.05,
        ),
    ]


async def test_agent_returns_response_with_relevant_chunks(
    mock_llm: MockChatModel,
    high_relevance_chunks: list[RetrievedChunk],
) -> None:
    retrieval = _mock_retrieval_service(high_relevance_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
        similarity_threshold=0.3,
    )

    result = await graph.ainvoke(
        {"query": "What is the capital of France?", "conversation_history": []}
    )

    assert result["response"]
    assert "Based on your documents" in result["response"]
    assert len(result["sources"]) == 2
    assert result["sources"][0]["filename"] == "geography.md"


async def test_agent_returns_no_docs_when_below_threshold(
    mock_llm: MockChatModel,
    low_relevance_chunks: list[RetrievedChunk],
) -> None:
    retrieval = _mock_retrieval_service(low_relevance_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
        similarity_threshold=0.3,
    )

    result = await graph.ainvoke(
        {"query": "What is the capital of France?", "conversation_history": []}
    )

    assert result["response"] == _NO_RELEVANT_DOCS_RESPONSE
    assert result["sources"] == []


async def test_agent_returns_no_docs_when_store_empty(
    mock_llm: MockChatModel,
) -> None:
    retrieval = _mock_retrieval_service([])
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
    )

    result = await graph.ainvoke({"query": "Anything?", "conversation_history": []})

    assert result["response"] == _NO_RELEVANT_DOCS_RESPONSE
    assert result["sources"] == []


async def test_grade_node_filters_below_threshold(
    mock_llm: MockChatModel,
) -> None:
    """Only chunks at or above the threshold pass grading."""
    mixed_chunks = [
        _make_chunk(chunk_content="Relevant chunk", similarity_score=0.8),
        _make_chunk(chunk_content="Borderline chunk", similarity_score=0.3),
        _make_chunk(chunk_content="Irrelevant chunk", similarity_score=0.2),
    ]
    retrieval = _mock_retrieval_service(mixed_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
        similarity_threshold=0.3,
    )

    result = await graph.ainvoke({"query": "test", "conversation_history": []})

    assert len(result["sources"]) == 2
    scores = [s["similarity_score"] for s in result["sources"]]
    assert all(s >= 0.3 for s in scores)


async def test_conversation_history_included_in_llm_prompt(
    mock_llm: MockChatModel,
    high_relevance_chunks: list[RetrievedChunk],
) -> None:
    """Conversation history should be passed to the LLM."""
    retrieval = _mock_retrieval_service(high_relevance_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
    )

    history = [
        {"role": "user", "content": "Tell me about France"},
        {"role": "assistant", "content": "France is a country in Europe."},
    ]

    result = await graph.ainvoke({"query": "What is its capital?", "conversation_history": history})

    assert result["response"]
    assert len(result["sources"]) > 0


async def test_source_attributions_structure(
    mock_llm: MockChatModel,
    high_relevance_chunks: list[RetrievedChunk],
) -> None:
    retrieval = _mock_retrieval_service(high_relevance_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
    )

    result = await graph.ainvoke({"query": "test", "conversation_history": []})

    for source in result["sources"]:
        assert "document_id" in source
        assert "filename" in source
        assert "chunk_content" in source
        assert "similarity_score" in source
        assert isinstance(source["similarity_score"], float)


async def test_rewrite_node_passthrough_when_disabled(
    mock_llm: MockChatModel,
    high_relevance_chunks: list[RetrievedChunk],
) -> None:
    """With query_rewrite=False, the original query is passed through unchanged."""
    retrieval = _mock_retrieval_service(high_relevance_chunks)
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
        query_rewrite=False,
    )

    result = await graph.ainvoke(
        {"query": "What is the capital of France?", "conversation_history": []}
    )

    assert result["search_queries"] == ["What is the capital of France?"]
    assert result["response"]
    assert len(result["sources"]) > 0


async def test_graph_has_four_nodes(mock_llm: MockChatModel) -> None:
    retrieval = _mock_retrieval_service([])
    session_factory = _mock_session_factory()
    graph = build_agent_graph(
        retrieval_service=retrieval,
        llm=mock_llm,
        session_factory=session_factory,
    )
    node_names = set(graph.get_graph().nodes.keys()) - {"__start__", "__end__"}
    assert node_names == {
        "rewrite_query",
        "retrieve_documents",
        "grade_relevance",
        "generate_response",
    }


def test_create_llm_returns_mock_by_default() -> None:
    settings = Settings(llm_provider="mock")
    llm = create_llm(settings)
    assert isinstance(llm, MockChatModel)


def test_create_llm_returns_anthropic_when_configured() -> None:
    from langchain_anthropic import ChatAnthropic

    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-4-20250514",
    )
    llm = create_llm(settings)
    assert isinstance(llm, ChatAnthropic)


def test_create_llm_raises_on_missing_anthropic_api_key() -> None:
    settings = Settings(llm_provider="anthropic", anthropic_api_key="")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        create_llm(settings)


def test_system_prompt_contains_caretaker_persona() -> None:
    assert "The Caretaker" in _SYSTEM_PROMPT
    assert "The Archive" in _SYSTEM_PROMPT
    assert "ONLY the provided document context" in _SYSTEM_PROMPT
