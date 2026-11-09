# backend/ — Python brain

> **Status: implemented.** FastAPI app, WebSocket session, agent loop, tool registry, audio pipeline and SQLite memory live here. Windows-only integrations import lazily and report a clear error off Windows.

Layout:

```
backend/
├── main.py              # entry point: FastAPI on 127.0.0.1:<random port>
├── config.py            # settings, %APPDATA%\Veyra paths, keyring access
├── api/                 # HTTP + WebSocket surface, session-token auth
├── brain/               # Ollama client, online client, router, agent loop, prompts
├── audio/               # wake word, VAD, STT, TTS
├── tools/               # registry, pre-classifier, tool implementations
├── memory/              # SQLite schema, notes, timers, tool log
└── tests/               # pytest, no real side effects
```

Non-negotiable rules:

- Docstrings and comments in English; user-facing text through i18n on the UI side.
- Type hints on public functions; structured logging, never `print`.
- No secrets in code or config files: keys and tokens go through `keyring`.
- The server binds to `127.0.0.1` only and validates the per-run session token on every request.
- Model output is untrusted input: validate JSON, tool names and parameters before use.
- A failing tool returns an error to the model and the UI; it never crashes the process.
