# 10. Anthropic LLM Integration

**Date**: 2026-03-08  
**Status**: Accepted

## Context

The application shipped with a mock LLM and optional Ollama support. To deliver real, high-quality RAG answers, we need a hosted LLM provider that supports streaming and handles complex document reasoning well. The integration must be additive -- mock and Ollama must continue working unchanged.

## Options considered

1. **OpenAI (GPT-4o)** — Excellent quality, wide LangChain support. Requires OpenAI account and API key. Token costs are moderate.
2. **Anthropic (Claude Sonnet)** — Strong document reasoning, 200k context window, native streaming. LangChain has first-class support via `langchain-anthropic`. Competitive pricing.
3. **Google Gemini** — Large context window, but LangChain integration is less mature for streaming. API surface differs significantly from the existing provider pattern.

## Decision

Chose **Anthropic Claude** (`claude-sonnet-4-20250514` default, configurable via `ANTHROPIC_MODEL`).

- `langchain-anthropic` provides `ChatAnthropic` with the same `BaseChatModel` interface used by mock and Ollama, so the LLM factory stays clean.
- Claude excels at grounded document Q&A with explicit instructions not to speculate beyond provided context.
- Streaming is natively supported -- `ChatAnthropic(streaming=True)` yields token-level `AIMessageChunk` events via `astream_events`.
- The API key is provided via `ANTHROPIC_API_KEY` env var. When the provider is set to `anthropic` but the key is missing, startup fails fast with a clear error.
- Fallback: `LLM_PROVIDER` defaults to `mock`; no Anthropic dependency is imported unless `anthropic` is selected.

## Consequences

- **New dependency**: `langchain-anthropic>=0.3` added to `pyproject.toml`.
- **Config surface**: two new settings (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) -- both optional unless the provider is `anthropic`.
- **Cost**: real LLM calls incur API costs. The mock provider remains the zero-cost default for development and CI.
- **Query rewrite**: enabled for `anthropic` (same gating as Ollama -- `llm_provider != "mock"`), improving retrieval quality.
