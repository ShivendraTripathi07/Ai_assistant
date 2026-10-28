# Personal AI Copilot

A Windows desktop chat launcher with configurable AI and web search providers. It keeps conversation history in a local SQLite database and works without credentials for the desktop shell. Cloud requests require your own API keys.

## Current scope

Implemented: PySide6 floating draggable launcher, tray menu, chat window, Auto/AI/Web Search modes, background HTTP calls, Gemini and Tavily HTTP adapters, raw search results surfaced as soon as search completes, bounded recent conversation history, SQLite persistence, settings dialog for model/timeouts, and explicit clipboard text attachment. Attached text is sent only after you click **Attach copied text…**, is shown in the UI, is not written into conversation history, and can be removed before sending. Recent conversation history is restored at launch.

Not implemented yet: global keyboard hook, automatic selected-text capture (copy text yourself, then use the explicit attach button), screenshot region/vision flow, OAuth and Google Sheets/job tracker, streaming, cancellation, migrations, PyInstaller build, multi-conversation management, and Windows multi-monitor validation. These remain next milestones, not completed features.

## Install and run (Windows PowerShell)

Install Python 3.12+, then from this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
copilot
```

With no API key, the window still launches and explains which key is missing when a provider is used. Add keys to `.env` (never share or commit it):

```dotenv
COPILOT_GEMINI_API_KEY=your_key
COPILOT_TAVILY_API_KEY=your_key
```

Gemini: create a key in [Google AI Studio](https://aistudio.google.com/app/apikey). The model identifier is configurable with `COPILOT_GEMINI_MODEL` (default `gemini-2.5-flash`). Gemini API availability, quotas, pricing, and free access depend on current Google terms and account/region. Tavily: create an API key at [Tavily](https://tavily.com/); its free allowance and terms can change. Search credentials are separate from model credentials. No paid-provider fallback is enabled.

## Configuration

Pydantic Settings reads built-in defaults, then `.env` and process environment variables (environment values win). Supported values include `COPILOT_GEMINI_API_KEY`, `COPILOT_GEMINI_MODEL`, `COPILOT_TAVILY_API_KEY`, `COPILOT_DATABASE_PATH`, `COPILOT_LLM_TIMEOUT_SECONDS`, `COPILOT_SEARCH_TIMEOUT_SECONDS`, `COPILOT_MAX_CONTEXT_MESSAGES`, and `COPILOT_SHORTCUT`. API keys are not stored in SQLite or logged. `config/config.example.yaml` is a reference for planned file-based settings; the current app does not parse YAML yet.

## Architecture

See [docs/architecture.md](docs/architecture.md). Domain contracts are in `domain.py`, orchestration in `application.py`, HTTP/SQLite adapters in `infrastructure.py`, and PySide6 presentation in `desktop.py`. `main.py` composes them. The UI does not call HTTP providers directly. Search-only mode does not make an LLM request; in Auto mode, obvious current-information phrasing searches and then asks Gemini to synthesize. Search results are emitted to the UI before synthesis. Web results are treated as untrusted reference material.

## Google Sheets setup (planned integration)

The app does not yet connect to Google Sheets. When implemented, setup will require a Google Cloud project, enablement of Google Sheets API, OAuth consent configuration, and a Desktop app OAuth client. Configure the exact spreadsheet ID to avoid Drive-wide discovery scope; authorize only the Sheets scope needed for that spreadsheet. Credentials should be stored in the Windows user credential store or a user-only application data directory, never in the repository. The initial write workflow will display extracted fields and ask before writes; retries must not duplicate rows. Do not create OAuth credentials expecting the current release to use them.

## Privacy and troubleshooting

Only text you type and clipboard text you explicitly attach are sent to a provider. The app never reads clipboard contents in the background; browser content is not captured. Search/AI requests require internet access and may fail on missing credentials, quota, timeout, or provider outage; the UI displays the error. SQLite is stored at `COPILOT_DATABASE_PATH` (default: `%LOCALAPPDATA%/PersonalAICopilot/copilot.sqlite3`). Use **New conversation** to clear its messages. API responses are subject to provider policies; review them before sending sensitive information.

## Development

```powershell
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

Tests use fakes and do not call live APIs. No GUI launch or Windows global-shortcut behavior has been verified in this environment. `pip install -e ".[google-sheets,package]"` installs future integration/packaging dependencies but does not implement those features.
