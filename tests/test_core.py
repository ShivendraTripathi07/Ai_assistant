from pathlib import Path

import pytest

from copilot.application import Assistant
from copilot.domain import Message, Mode, SearchResult
from copilot.infrastructure import ConversationStore


class FakeLLM:
    async def generate(self, prompt: str, context: list[Message]) -> str:
        return "answer"


class FakeSearch:
    async def search(self, query: str) -> list[SearchResult]:
        return [SearchResult("Result", "https://example.com", "Snippet", "example.com")]


@pytest.mark.asyncio
async def test_search_only_does_not_call_llm(tmp_path: Path) -> None:
    assistant = Assistant(FakeLLM(), FakeSearch(), ConversationStore(tmp_path / "test.db"), 8)
    result = await assistant.ask("Search the web only: cats", Mode.SEARCH)
    assert result.answer == ""
    assert result.sources[0].domain == "example.com"


@pytest.mark.asyncio
async def test_ai_turn_persists_context(tmp_path: Path) -> None:
    store = ConversationStore(tmp_path / "test.db")
    assistant = Assistant(FakeLLM(), FakeSearch(), store, 8)
    result = await assistant.ask("Explain this", Mode.AI)
    assert result.answer == "answer"
    assert [m.role for m in store.history(8)] == ["user", "assistant"]
