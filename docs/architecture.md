# Architecture and milestones

## Boundaries

`domain` contains framework-independent message and provider contracts. `application` routes an explicit mode or a lightweight heuristic and coordinates search and model calls. `infrastructure` owns HTTP adapters and SQLite storage. `desktop` is the PySide6 presentation layer; `bootstrap.py` loads settings and wires dependencies. Dependencies point inward: UI depends on application interfaces, while adapters implement those interfaces.

`LLMProvider` and `SearchProvider` are replaceable ports. The initial adapters use documented HTTP APIs directly to keep the dependency footprint small. Search-only results are displayed before any optional model synthesis. The UI runs network work in a Qt worker thread and signals the GUI thread.

## Lifecycle

User message → request router → optional search adapter → immediate raw result display → optional LLM adapter with bounded recent context → SQLite conversation history → GUI update. The application never treats webpage text as instructions, executes model output, or writes to external accounts implicitly.

## Milestones

1. Foundation: validated config, ports, adapters, persistence, tests, documentation.
2. Desktop: tray, floating launcher, chat popup, worker-thread calls.
3. Context: explicit clipboard selection and screenshot region capture.
4. Integrations: Google OAuth and user-confirmed job tracking workflows.
5. Packaging and Windows verification.

This initial implementation completes the first milestone and a usable slice of milestone 2. OAuth, screenshot capture, job extraction, and packaging remain follow-up work and are described in README.
