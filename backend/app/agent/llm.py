from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import Settings

logger = logging.getLogger(__name__)

_CONTEXT_MARKER = "Retrieved context:"
_NO_CONTEXT_RESPONSE = (
    "I couldn't find any relevant information in the uploaded documents. "
    "Try uploading documents related to your question, or rephrase your query."
)


class MockChatModel(BaseChatModel):
    """Mock LLM that templates retrieved chunks into a formatted response.

    Expects the last human message to contain retrieved context injected
    by the agent's generate node. Extracts that context and formats it
    into a structured response that demonstrates the full RAG pipeline.
    """

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    def _format_response(self, messages: list[BaseMessage]) -> str:
        last_message = messages[-1].content if messages else ""
        content = str(last_message)

        if _CONTEXT_MARKER in content:
            context_section = content.split(_CONTEXT_MARKER, 1)[1].strip()
            return (
                f"Based on your documents, here is what I found:\n\n"
                f"{context_section}"
            )
        return _NO_CONTEXT_RESPONSE

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_text = self._format_response(messages)
        generation = ChatGeneration(message=AIMessage(content=response_text))
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_text = self._format_response(messages)
        generation = ChatGeneration(message=AIMessage(content=response_text))
        return ChatResult(generations=[generation])


def create_llm(settings: Settings) -> BaseChatModel:
    """Factory that returns the configured LLM.

    Uses MockChatModel by default. Set LLM_PROVIDER=ollama to use a local
    Ollama model (requires Ollama running with the model pulled).
    """
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info(
            "Using Ollama LLM: model=%s, base_url=%s",
            settings.ollama_model,
            settings.ollama_base_url,
        )
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    logger.info("Using mock LLM (set LLM_PROVIDER=ollama for real responses)")
    return MockChatModel()
