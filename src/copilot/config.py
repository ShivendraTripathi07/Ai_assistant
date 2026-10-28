from pathlib import Path

from platformdirs import user_data_path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COPILOT_", env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash"
    tavily_api_key: str = ""
    database_path: Path = user_data_path("PersonalAICopilot") / "copilot.sqlite3"
    llm_timeout_seconds: float = Field(default=45, gt=0, le=180)
    search_timeout_seconds: float = Field(default=12, gt=0, le=60)
    max_context_messages: int = Field(default=16, ge=2, le=100)
    shortcut: str = "Ctrl+Shift+Space"
