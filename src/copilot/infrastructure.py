import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx

from copilot.config import Settings
from copilot.domain import Message, SearchResult


class GeminiProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(self, prompt: str, context: list[Message]) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("Gemini API key missing. Add COPILOT_GEMINI_API_KEY to .env.")
        contents = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.text}]}
            for m in context
        ]
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent"
        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": self.settings.gemini_api_key},
                json={"contents": contents},
            )
            response.raise_for_status()
            data = response.json()
        try:
            candidates = data["candidates"]
            first = candidates[0]
            content = first["content"]
            parts = content["parts"]
            text = parts[0]["text"]
            if not isinstance(text, str):
                raise TypeError("Gemini response text was not a string")
            return text
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Gemini returned no text. Check model availability and API quota."
            ) from exc


class TavilySearch:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(self, query: str) -> list[SearchResult]:
        if not self.settings.tavily_api_key:
            raise RuntimeError("Tavily API key missing. Add COPILOT_TAVILY_API_KEY to .env.")
        async with httpx.AsyncClient(timeout=self.settings.search_timeout_seconds) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": self.settings.tavily_api_key, "query": query, "max_results": 5},
            )
            response.raise_for_status()
            data = response.json()
        results = []
        for item in data.get("results", []):
            url = item.get("url", "")
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                continue
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=url,
                    snippet=item.get("content", ""),
                    domain=parsed.netloc,
                )
            )
        return results


class ConversationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _fetch_history(self, limit: int) -> list[tuple[str, str]]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT role, text FROM (SELECT id, role, text FROM messages ORDER BY id DESC LIMIT ?) ORDER BY id",
                (limit,),
            ).fetchall()
        return [(str(role), str(text)) for role, text in rows]

    def history(self, limit: int) -> list[Message]:
        return [Message(role, text) for role, text in self._fetch_history(limit)]

    def add(self, role: str, text: str) -> None:
        with self._connection() as db:
            db.execute("INSERT INTO messages (role, text) VALUES (?, ?)", (role, text))

    def clear(self) -> None:
        with self._connection() as db:
            db.execute("DELETE FROM messages")
