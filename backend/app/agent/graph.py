from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.llm import _CONTEXT_MARKER
from app.services.retrieval import (
    RetrievedChunk,
    RetrievalService,
    deduplicate_chunks,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_NO_RELEVANT_DOCS_RESPONSE = (
    "I couldn't find any relevant information in the uploaded documents. "
    "Try uploading documents related to your question, or rephrase your query."
)

_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based on the user's "
    "uploaded documents. Use only the provided context to answer. If the "
    "context doesn't contain enough information, say so honestly."
)


class AgentState(TypedDict):
    query: str
    search_queries: list[str]
    conversation_history: list[dict[str, str]]
    retrieved_chunks: list[RetrievedChunk]
    relevant_chunks: list[RetrievedChunk]
    response: str
    sources: list[dict[str, Any]]


_REWRITE_PROMPT = (
    "You are a search query optimizer for a document retrieval system. "
    "Given the user's question, generate 2-3 alternative search queries "
    "that would help find relevant information. Each query should approach "
    "the topic from a different angle or use different keywords.\n\n"
    "Return ONLY the queries, one per line. No numbering, no explanations."
)


def _build_rewrite_node(llm: BaseChatModel, enabled: bool) -> Any:
    async def rewrite_query(state: AgentState) -> dict:
        original = state["query"]

        if not enabled:
            return {"search_queries": [original]}

        messages = [
            SystemMessage(content=_REWRITE_PROMPT),
            HumanMessage(content=original),
        ]
        result = await llm.ainvoke(messages)
        raw_text = str(result.content).strip()
        alternatives = [line.strip() for line in raw_text.splitlines() if line.strip()]

        queries = [original] + alternatives
        logger.info(
            "Rewrote query into %d search queries: %s",
            len(queries),
            queries,
        )
        return {"search_queries": queries}

    return rewrite_query


def _build_retrieve_node(
    retrieval_service: RetrievalService,
    top_k: int,
    candidate_k: int,
    session_factory: async_sessionmaker[AsyncSession],
) -> Any:
    async def retrieve_documents(state: AgentState) -> dict:
        queries = state.get("search_queries") or [state["query"]]

        all_chunks: list[RetrievedChunk] = []
        async with session_factory() as session:
            for q in queries:
                chunks = await retrieval_service.search(
                    query=q,
                    session=session,
                    top_k=top_k,
                    candidate_k=candidate_k,
                )
                all_chunks.extend(chunks)

        if len(queries) > 1:
            all_chunks = deduplicate_chunks(all_chunks, final_k=top_k)

        logger.info(
            "Retrieved %d chunks for %d search queries",
            len(all_chunks),
            len(queries),
        )
        return {"retrieved_chunks": all_chunks}

    return retrieve_documents


def _build_grade_node(similarity_threshold: float) -> Any:
    def grade_relevance(state: AgentState) -> dict:
        retrieved = state["retrieved_chunks"]
        for chunk in retrieved:
            logger.debug(
                "Chunk %d (%.80s): similarity=%.4f %s",
                chunk.chunk_index,
                chunk.chunk_content.replace("\n", " "),
                chunk.similarity_score,
                "PASS" if chunk.similarity_score >= similarity_threshold else "FAIL",
            )
        relevant = [
            chunk
            for chunk in retrieved
            if chunk.similarity_score >= similarity_threshold
        ]
        logger.info(
            "Graded %d/%d chunks as relevant (threshold=%.2f, top_score=%.4f)",
            len(relevant),
            len(retrieved),
            similarity_threshold,
            max((c.similarity_score for c in retrieved), default=0.0),
        )
        if not relevant:
            return {
                "relevant_chunks": [],
                "response": _NO_RELEVANT_DOCS_RESPONSE,
                "sources": [],
            }
        return {"relevant_chunks": relevant}

    return grade_relevance


def _build_generate_node(llm: BaseChatModel) -> Any:
    async def generate_response(state: AgentState) -> dict:
        chunks = state["relevant_chunks"]

        context_parts = []
        for chunk in chunks:
            if chunk.section_heading:
                source_label = f"{chunk.filename} > {chunk.section_heading}"
            else:
                source_label = chunk.filename
            context_parts.append(
                f"[Source: {source_label}]\n{chunk.chunk_content}"
            )
        context_text = "\n\n---\n\n".join(context_parts)

        messages = [SystemMessage(content=_SYSTEM_PROMPT)]

        for msg in state.get("conversation_history", []):
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        prompt = (
            f"Question: {state['query']}\n\n"
            f"{_CONTEXT_MARKER}\n{context_text}"
        )
        messages.append(HumanMessage(content=prompt))

        result = await llm.ainvoke(messages)
        response_text = str(result.content)

        sources = [
            {
                "document_id": str(chunk.document_id),
                "filename": chunk.filename,
                "chunk_content": chunk.chunk_content,
                "similarity_score": chunk.similarity_score,
                "section_heading": chunk.section_heading,
            }
            for chunk in chunks
        ]

        return {"response": response_text, "sources": sources}

    return generate_response


def _has_relevant_chunks(state: AgentState) -> str:
    if state.get("relevant_chunks"):
        return "generate"
    return "end"


def build_agent_graph(
    retrieval_service: RetrievalService,
    llm: BaseChatModel,
    session_factory: async_sessionmaker[AsyncSession],
    similarity_threshold: float = 0.3,
    top_k: int = 5,
    candidate_k: int = 10,
    query_rewrite: bool = False,
) -> CompiledStateGraph:
    """Build and compile the RAG agent graph.

    The graph has four nodes:
      1. rewrite_query -- reformulate the user query into search-optimized
         variations (passthrough when query_rewrite is disabled)
      2. retrieve_documents -- query the vector/keyword store for similar
         chunks, merging results across multiple search queries
      3. grade_relevance -- filter chunks below the similarity threshold
      4. generate_response -- pass relevant chunks to the LLM

    If no chunks pass the grade, the graph short-circuits with a
    "no relevant documents" response.
    """
    graph = StateGraph(AgentState)

    graph.add_node("rewrite_query", _build_rewrite_node(llm, enabled=query_rewrite))
    graph.add_node(
        "retrieve_documents",
        _build_retrieve_node(retrieval_service, top_k, candidate_k, session_factory),
    )
    graph.add_node("grade_relevance", _build_grade_node(similarity_threshold))
    graph.add_node("generate_response", _build_generate_node(llm))

    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "retrieve_documents")
    graph.add_edge("retrieve_documents", "grade_relevance")
    graph.add_conditional_edges(
        "grade_relevance",
        _has_relevant_chunks,
        {"generate": "generate_response", "end": END},
    )
    graph.add_edge("generate_response", END)

    return graph.compile()
