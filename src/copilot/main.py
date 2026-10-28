import logging
import sys

from copilot.application import Assistant
from copilot.config import Settings
from copilot.desktop import run_desktop
from copilot.infrastructure import ConversationStore, GeminiProvider, TavilySearch


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = Settings()
    assistant = Assistant(
        GeminiProvider(settings),
        TavilySearch(settings),
        ConversationStore(settings.database_path),
        settings.max_context_messages,
    )
    sys.exit(run_desktop(assistant, settings))


if __name__ == "__main__":
    main()
