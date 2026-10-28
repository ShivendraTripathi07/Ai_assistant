from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class Mode(StrEnum):
    AUTO = "Auto"
    AI = "AI"
    SEARCH = "Web Search"


@dataclass(frozen=True)
class Message:
    role: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    domain: str


@dataclass
class TurnResult:
    answer: str = ""
    sources: list[SearchResult] = field(default_factory=list)
    provider: str = ""


class LLMProvider(Protocol):
    async def generate(self, prompt: str, context: list[Message]) -> str: ...


class SearchProvider(Protocol):
    async def search(self, query: str) -> list[SearchResult]: ...
